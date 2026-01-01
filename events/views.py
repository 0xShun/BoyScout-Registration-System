from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Event, EventPhoto, Attendance, EventRegistration, EventPayment
from .forms import EventForm, EventPhotoForm, EventRegistrationForm, EventPaymentForm
from accounts.views import admin_required # Reusing the admin_required decorator
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import models
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
import os
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from accounts.models import User
from django.utils import timezone
from notifications.services import send_realtime_notification, NotificationService
from decimal import Decimal

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

def send_event_notifications(event, action='created'):
    """Send notifications to all active users about new/updated events"""
    from accounts.models import User
    
    active_users = User.objects.filter(is_active=True)
    
    if action == 'created':
        subject = f"New Event: {event.title}"
        message = f"""
        A new event has been scheduled!
        
        Event: {event.title}
        Date: {event.date}
        Time: {event.time}
        Location: {event.location}
        
        {event.description}
        
        Please log in to your dashboard to register.
        """
        sms_message = f"New event: {event.title} on {event.date}"
    else:  # updated
        subject = f"Event Updated: {event.title}"
        message = f"""
        An event has been updated!
        
        Event: {event.title}
        Date: {event.date}
        Time: {event.time}
        Location: {event.location}
        
        {event.description}
        
        Please check your dashboard for updated details.
        """
        sms_message = f"Event updated: {event.title} on {event.date}"
    
    # Send email to all active users
    for user in active_users:
        if user.email:
            NotificationService.send_email(subject, message, [user.email])
        
        # Send SMS if phone number exists
        if user.phone_number:
            NotificationService.send_sms(user.phone_number, sms_message)

@login_required
def event_list(request):
    # Gate events for scouts until registration is verified
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_registration_complete:
        messages.warning(request, 'Events are locked until your registration payment is verified.')
        return redirect('accounts:registration_payment', user_id=request.user.id)
    # Show all events for calendar view (including past events)
    events = Event.objects.all().order_by('-date', '-time')
    return render(request, 'events/event_list.html', {'events': events})

@admin_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            # Send notifications to all active users
            send_event_notifications(event, 'created')
            
            messages.success(request, 'Event created successfully.')
            return redirect('events:event_detail', pk=event.pk)
    else:
        # Pre-fill date if provided in query parameter (from calendar)
        initial_data = {}
        if 'date' in request.GET:
            initial_data['date'] = request.GET.get('date')
        form = EventForm(initial=initial_data)
    return render(request, 'events/event_form.html', {'form': form})

@login_required
def event_detail(request, pk):
    # Gate events for scouts until registration is verified
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_registration_complete:
        messages.warning(request, 'Events are locked until your registration payment is verified.')
        return redirect('accounts:registration_payment', user_id=request.user.id)
    event = get_object_or_404(Event, pk=pk)
    
    photos = event.photos.all().order_by('-is_featured', '-uploaded_at')
    # Attendance summary
    attendance_qs = event.attendances.select_related('user')
    present_list = [a.user for a in attendance_qs if a.status == 'present']
    absent_list = [a.user for a in attendance_qs if a.status == 'absent']
    present_count = len(present_list)
    absent_count = len(absent_list)
    total_scouts = present_count + absent_count

    # Get QR code for payment (event-specific or fallback to general)
    from payments.models import PaymentQRCode
    # Use the actual event.qr_code object if it exists, otherwise get the general QR code
    qr_code = None
    if event.qr_code:
        qr_code = event.qr_code
    else:
        qr_code = PaymentQRCode.get_active_qr_code()
    
    # Registration logic
    registration = None
    registration_form = None
    if request.user.is_authenticated:
        # Handle QR code upload (Admin only)
        if request.method == 'POST' and 'upload_qr_code' in request.POST and request.user.is_admin():
            qr_code_file = request.FILES.get('qr_code')
            if qr_code_file:
                # Validate file size (max 10MB)
                if qr_code_file.size > 10 * 1024 * 1024:
                    messages.error(request, 'File too large. Maximum size is 10MB.')
                    return redirect('events:event_detail', pk=event.pk)
                
                # Validate file type
                allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
                if qr_code_file.content_type not in allowed_types:
                    messages.error(request, 'Invalid file type. Please upload JPG or PNG image.')
                    return redirect('events:event_detail', pk=event.pk)
                
                # Save the QR code to the event
                event.qr_code = qr_code_file
                event.save()
                
                messages.success(request, f'Payment QR code {"updated" if event.qr_code else "uploaded"} successfully!')
                return redirect('events:event_detail', pk=event.pk)
            else:
                messages.error(request, 'Please select a QR code image to upload.')
                return redirect('events:event_detail', pk=event.pk)
        
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
        if request.method == 'POST' and 'register_event' in request.POST:
            if registration:
                registration_form = EventRegistrationForm(request.POST, instance=registration, event=event)
            else:
                registration_form = EventRegistrationForm(request.POST, event=event)
            if registration_form.is_valid():
                reg = registration_form.save(commit=False)
                reg.event = event
                reg.user = request.user
                
                # Handle payment for paid events
                if event.has_payment_required:
                    # Cancel old pending payments for this user/event
                    old_payments = EventPayment.objects.filter(
                        registration__event=event,
                        registration__user=request.user,
                        status='pending'
                    )
                    old_payments.update(status='cancelled')
                    
                    # Save registration first
                    if not registration:
                        # New registration
                        reg.payment_status = 'pending'
                        reg.save()
                    else:
                        reg.save()
                    
                    # Calculate amount to pay (total - already paid)
                    total_paid = EventPayment.objects.filter(
                        registration=reg,
                        status='verified'
                    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
                    
                    amount_to_pay = event.payment_amount - total_paid
                    
                    if amount_to_pay > 0:
                        # Create PayMongo source for QR payment
                        from .paymongo_service import PayMongoService
                        paymongo_service = PayMongoService()
                        
                        # Get selected payment method from form
                        payment_method = request.POST.get('payment_method', 'gcash')
                        
                        source_response = paymongo_service.create_source(
                            amount=amount_to_pay,
                            type=payment_method,  # gcash, grab_pay, or paymaya
                            redirect_success=f"{settings.SITE_URL}/events/payment-status/{reg.id}/success/",
                            redirect_failed=f"{settings.SITE_URL}/events/payment-status/{reg.id}/failed/",
                            metadata={
                                'registration_id': str(reg.id),
                                'event_id': str(event.id),
                                'user_id': str(request.user.id)
                            }
                        )
                        
                        if source_response and source_response.get('data'):
                            source_id = source_response['data']['id']
                            checkout_url = source_response['data']['attributes']['redirect']['checkout_url']
                            expires_at = source_response['data']['attributes']['redirect'].get('return_url_expires_at')
                            
                            # Create EventPayment record
                            payment = EventPayment.objects.create(
                                registration=reg,
                                amount=amount_to_pay,
                                paymongo_source_id=source_id,
                                payment_method=f'paymongo_{payment_method}',
                                status='pending',
                                expires_at=timezone.datetime.fromisoformat(expires_at.replace('Z', '+00:00')) if expires_at else None
                            )
                            
                            # Update registration payment status
                            reg.payment_status = 'pending'
                            reg.save()
                            
                            messages.success(request, 'Registration created! Redirecting to PayMongo for payment...')
                            # Store checkout URL in session to open in new tab
                            request.session['paymongo_checkout_url'] = checkout_url
                            return redirect('events:event_detail', pk=event.pk)
                        else:
                            messages.error(request, 'Failed to create payment link. Please try again.')
                            return redirect('events:event_detail', pk=event.pk)
                    else:
                        # Already fully paid
                        reg.payment_status = 'paid'
                        reg.save()
                        messages.success(request, 'Registration updated! Payment already complete.')
                        return redirect('events:event_detail', pk=event.pk)
                else:
                    # Free event - auto approve
                    reg.payment_status = 'not_required'
                    reg.save()
                    messages.success(request, 'You have successfully registered for this event!')
                
                return redirect('events:event_detail', pk=event.pk)
            else:
                # Form validation failed - show specific errors
                for field, errors in registration_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                if not registration_form.errors:
                    messages.error(request, 'There was an error with your registration. Please check the form.')
        else:
            registration_form = EventRegistrationForm(instance=registration, event=event)

    # Admin: see all registrations
    registrations = None
    if request.user.is_authenticated and request.user.is_admin():
        registrations = EventRegistration.objects.filter(event=event).select_related('user').prefetch_related('payments')
    
    # Get user's payment receipts if registered
    user_payments = []
    if registration:
        user_payments = EventPayment.objects.filter(registration=registration).order_by('-created_at')

    return render(request, 'events/event_detail.html', {
        'event': event,
        'photos': photos,
        'present_list': present_list,
        'absent_list': absent_list,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_scouts': total_scouts,
        'registration': registration,
        'registration_form': registration_form,
        'registrations': registrations,
        'qr_code': qr_code,
        'user_payments': user_payments,
    })

@admin_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            
            # Send notifications to all active users about the update
            send_event_notifications(event, 'updated')
            
            messages.success(request, 'Event updated successfully.')
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form})

@admin_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('events:event_list')
    return render(request, 'events/event_confirm_delete.html', {'event': event})

@admin_required
def photo_upload(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)
    
    if request.method == 'POST':
        form = EventPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Validate image file
                image = request.FILES['image']
                if image.size > settings.MAX_UPLOAD_SIZE:  # e.g., 5MB
                    messages.error(request, 'Image size must be less than 5MB.')
                    return redirect('events:event_detail', pk=event.pk)
                
                # Validate image format
                try:
                    img = Image.open(image)
                    if img.format.lower() not in ['jpeg', 'jpg', 'png', 'gif']:
                        messages.error(request, 'Invalid image format. Please upload JPG, PNG, or GIF.')
                        return redirect('events:event_detail', pk=event.pk)
                except Exception as e:
                    messages.error(request, 'Invalid image file.')
                    return redirect('events:event_detail', pk=event.pk)

                # Create photo instance
                photo = form.save(commit=False)
                photo.event = event
                photo.uploaded_by = request.user
                
                # Generate unique filename
                ext = os.path.splitext(image.name)[1]
                filename = f"event_{event.pk}_photo_{photo.uploaded_at.strftime('%Y%m%d_%H%M%S')}{ext}"
                photo.image.save(filename, image, save=False)
                
                photo.save()
                messages.success(request, 'Photo uploaded successfully.')
                return redirect('events:event_detail', pk=event.pk)
                
            except Exception as e:
                messages.error(request, f'Error uploading photo: {str(e)}')
                return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventPhotoForm()
    return render(request, 'events/photo_upload.html', {
        'form': form,
        'event': event
    })

@login_required
def photo_delete(request, photo_pk):
    photo = get_object_or_404(EventPhoto, pk=photo_pk)
    
    # Check if user has permission to delete the photo
    if not (request.user.is_staff or request.user == photo.uploaded_by):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise PermissionDenied
    
    if request.method == 'POST':
        try:
            # Delete the image file
            if photo.image:
                if default_storage.exists(photo.image.name):
                    default_storage.delete(photo.image.name)
            
            # Delete the database record
            photo.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Photo deleted successfully.')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=500)
            messages.error(request, f'Error deleting photo: {str(e)}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    return redirect('events:event_detail', pk=photo.event.pk)

@admin_required
def photo_toggle_featured(request, photo_pk):
    photo = get_object_or_404(EventPhoto, pk=photo_pk)
    
    if request.method == 'POST':
        try:
            # If setting as featured, unfeature other photos
            if not photo.is_featured:
                EventPhoto.objects.filter(event=photo.event, is_featured=True).update(is_featured=False)
            
            photo.is_featured = not photo.is_featured
            photo.save()
            messages.success(request, f'Photo {"featured" if photo.is_featured else "unfeatured"} successfully.')
        except Exception as e:
            messages.error(request, f'Error updating photo: {str(e)}')
    
    return redirect('events:event_detail', pk=photo.event.pk)

@admin_required
def event_attendance(request, pk):
    event = get_object_or_404(Event, pk=pk)
    scouts = User.objects.filter(rank='scout').order_by('last_name', 'first_name')
    existing_attendance = {a.user_id: a for a in Attendance.objects.filter(event=event)}

    if request.method == 'POST':
        for scout in scouts:
            status = request.POST.get(f'attendance_{scout.id}', 'absent')
            att, created = Attendance.objects.get_or_create(event=event, user=scout, defaults={
                'status': status,
                'marked_by': request.user
            })
            if not created:
                att.status = status
                att.marked_by = request.user
                att.save()
        messages.success(request, 'Attendance has been updated.')
        return redirect('events:event_attendance', pk=event.pk)

    # Prepare attendance status for display
    attendance_status = {scout.id: existing_attendance.get(scout.id).status if scout.id in existing_attendance else '' for scout in scouts}
    return render(request, 'events/event_attendance.html', {
        'event': event,
        'scouts': scouts,
        'attendance_status': attendance_status,
    })

@admin_required
def verify_event_registration(request, event_pk, reg_pk):
    registration = get_object_or_404(EventRegistration, pk=reg_pk, event_id=event_pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        payment_id = request.POST.get('payment_id')
        payment_amount = request.POST.get('payment_amount')
        
        if payment_id:
            # Verify a specific payment
            payment = get_object_or_404(EventPayment, pk=payment_id, registration=registration)
            
            if action == 'verify':
                # Validate payment amount
                try:
                    if payment_amount:
                        amount = Decimal(payment_amount)
                        if amount <= 0:
                            messages.error(request, 'Payment amount must be greater than 0.')
                            return redirect('events:verify_event_registration', event_pk=event_pk, reg_pk=reg_pk)
                        payment.amount = amount
                    else:
                        messages.error(request, 'Please enter the payment amount.')
                        return redirect('events:verify_event_registration', event_pk=event_pk, reg_pk=reg_pk)
                except (ValueError, TypeError):
                    messages.error(request, 'Please enter a valid payment amount.')
                    return redirect('events:verify_event_registration', event_pk=event_pk, reg_pk=reg_pk)
                
                payment.status = 'verified'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.notes = notes
                payment.save()
                
                # Update registration total paid
                registration.total_paid += payment.amount
                registration.update_payment_status()
                registration.save()
                
                # Email and notification
                subject = f"Event Payment Verified: {registration.event.title}"
                message = f"Your payment of ₱{payment.amount} for event '{registration.event.title}' has been verified."
                if notes:
                    message += f"\n\nAdmin notes: {notes}"
                NotificationService.send_email(subject, message, [registration.user.email])
                send_realtime_notification(registration.user.id, f"Your payment of ₱{payment.amount} for '{registration.event.title}' has been verified.", type='event')
                messages.success(request, f'Payment of ₱{payment.amount} verified.')
                
            elif action == 'reject':
                rejection_reason = request.POST.get('rejection_reason', '').strip()
                
                payment.status = 'rejected'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.rejection_reason = rejection_reason if rejection_reason else 'No reason provided'
                payment.notes = notes
                payment.save()
                
                # Update registration payment status to rejected
                registration.payment_status = 'rejected'
                registration.save()
                
                # Check if this was a teacher-submitted payment
                teacher_submitted = 'teacher' in payment.notes.lower() if payment.notes else False
                teacher = registration.user.managed_by if hasattr(registration.user, 'managed_by') and registration.user.managed_by else None
                
                # Email and notification to student
                subject = f"Event Payment Rejected: {registration.event.title}"
                message = f"Your payment of ₱{payment.amount} for event '{registration.event.title}' has been rejected.\n\nReason: {payment.rejection_reason}\n\nPlease submit a new payment receipt."
                NotificationService.send_email(subject, message, [registration.user.email])
                send_realtime_notification(
                    registration.user.id, 
                    f"Your payment of ₱{payment.amount} for '{registration.event.title}' has been rejected. Reason: {payment.rejection_reason}", 
                    type='event'
                )
                
                # Notify teacher if they submitted the payment
                if teacher_submitted and teacher:
                    send_realtime_notification(
                        teacher.id,
                        f"Bulk payment for {registration.user.get_full_name()} for event '{registration.event.title}' has been rejected. Reason: {payment.rejection_reason}",
                        type='event'
                    )
                    NotificationService.send_email(
                        f"Bulk Event Payment Rejected: {registration.event.title}",
                        f"Your bulk payment submission for student {registration.user.get_full_name()} for event '{registration.event.title}' has been rejected.\n\nReason: {payment.rejection_reason}\n\nPlease submit a new payment receipt.",
                        [teacher.email]
                    )
                
                messages.warning(request, f'Payment of ₱{payment.amount} rejected.')
        else:
            # Legacy verification for old registrations without EventPayment records
            if action == 'verify':
                registration.verified = True
                registration.payment_status = 'paid'
                registration.verified_by = request.user
                registration.verification_date = timezone.now()
                registration.payment_notes = notes
                registration.save()
                
                # Email and notification
                subject = f"Event Registration Payment Verified: {registration.event.title}"
                message = f"Your payment for event '{registration.event.title}' has been verified."
                if notes:
                    message += f"\n\nAdmin notes: {notes}"
                NotificationService.send_email(subject, message, [registration.user.email])
                send_realtime_notification(registration.user.id, f"Your payment for '{registration.event.title}' has been verified.", type='event')
                messages.success(request, 'Registration payment verified.')
                
            elif action == 'reject':
                registration.verified = False
                registration.payment_status = 'rejected'
                registration.verified_by = request.user
                registration.verification_date = timezone.now()
                registration.payment_notes = notes
                registration.save()
                
                # Email and notification
                subject = f"Event Registration Payment Rejected: {registration.event.title}"
                message = f"Your payment for event '{registration.event.title}' has been rejected."
                if notes:
                    message += f"\n\nAdmin notes: {notes}"
                NotificationService.send_email(subject, message, [registration.user.email])
                send_realtime_notification(registration.user.id, f"Your payment for '{registration.event.title}' has been rejected.", type='event')
                messages.warning(request, 'Registration payment rejected.')
            
        return redirect('events:event_detail', pk=event_pk)
    
    return render(request, 'events/verify_event_registration.html', {'registration': registration, 'event_pk': event_pk})

@login_required
def event_payment(request, pk):
    """Dedicated payment page for a specific event"""
    event = get_object_or_404(Event, pk=pk)
    
    # Check if user is registered for this event
    try:
        registration = EventRegistration.objects.get(event=event, user=request.user)
    except EventRegistration.DoesNotExist:
        messages.error(request, 'You must register for this event first before making a payment.')
        return redirect('events:event_detail', pk=event.pk)
    
    # Check if event requires payment
    if not event.has_payment_required:
        messages.info(request, 'This event does not require payment.')
        return redirect('events:event_detail', pk=event.pk)
    
    # Handle new payment submission
    if request.method == 'POST':
        form = EventPaymentForm(request.POST, request.FILES, registration=registration)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.registration = registration
            payment.save()
            
            # Notify admins about payment submission
            admins = User.objects.filter(rank='admin')
            for admin in admins:
                send_realtime_notification(
                    admin.id, 
                    f"Event payment submitted: {registration.user.get_full_name()} - ₱{payment.amount} for {event.title}",
                    type='event'
                )
            
            messages.success(request, f'Payment of ₱{payment.amount} submitted successfully! Your payment is pending verification.')
            return redirect('events:event_payment', pk=event.pk)
    else:
        form = EventPaymentForm(registration=registration)
    
    # Get QR code (event-specific or general)
    from payments.models import PaymentQRCode
    qr_code = event.qr_code if event.qr_code else PaymentQRCode.get_active_qr_code()
    
    # Get payment history for this registration
    payments = registration.payments.all().order_by('-created_at')
    
    return render(request, 'events/event_payment.html', {
        'event': event,
        'registration': registration,
        'form': form,
        'qr_code': qr_code,
        'payments': payments,
    })

@admin_required
def pending_payments(request):
    """View for admins to see all pending payment registrations"""
    pending_registrations = EventRegistration.objects.filter(
        payment_status__in=['pending', 'partial']
    ).select_related('user', 'event').prefetch_related('payments').order_by('-registered_at')
    
    return render(request, 'events/pending_payments.html', {
        'pending_registrations': pending_registrations,
    })

# ==================== TEACHER VIEWS ====================

@login_required
def teacher_register_students_event(request):
    """Teacher registers multiple students for an event"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')
    
    from .forms import TeacherBulkEventRegistrationForm
    
    if request.method == 'POST':
        form = TeacherBulkEventRegistrationForm(request.POST, request.FILES, teacher=request.user)
        if form.is_valid():
            event = form.cleaned_data['event']
            students = form.cleaned_data['students']
            rsvp = form.cleaned_data['rsvp']
            receipt_image = form.cleaned_data.get('receipt_image')
            reference_number = form.cleaned_data.get('reference_number', '').strip()
            
            # Validate reference number for paid events
            if event.has_payment_required and receipt_image:
                if not reference_number:
                    messages.error(request, 'Reference number is required when uploading a payment receipt.')
                    return redirect('events:teacher_register_students_event')
                
                # Check for duplicate reference number
                if EventPayment.objects.filter(reference_number=reference_number).exists():
                    messages.error(request, 'This reference number has already been used. Please check your receipt.')
                    return redirect('events:teacher_register_students_event')
            
            registered_count = 0
            already_registered = []
            
            # Calculate total amount
            total_amount = 0
            if event.has_payment_required:
                total_amount = event.payment_amount * students.count()
            
            for student in students:
                # Check if already registered
                existing_reg = EventRegistration.objects.filter(event=event, user=student).first()
                if existing_reg:
                    already_registered.append(student.get_full_name())
                    continue
                
                # Create registration
                registration = EventRegistration.objects.create(
                    event=event,
                    user=student,
                    rsvp=rsvp,
                    receipt_image=None,  # Don't store in registration, use EventPayment
                    amount_required=event.payment_amount if event.has_payment_required else Decimal('0.00')
                )
                
                # Handle payment
                if event.has_payment_required and receipt_image:
                    # Create individual EventPayment record for this student using the same receipt
                    # Generate unique reference number for each student payment
                    student_ref_number = f"{reference_number}-S{student.id}"
                    
                    EventPayment.objects.create(
                        registration=registration,
                        amount=event.payment_amount,
                        receipt_image=receipt_image,
                        reference_number=student_ref_number,
                        status='pending',  # Pending admin verification
                        notes=f"Submitted by teacher {request.user.get_full_name()} for bulk registration"
                    )
                    
                    registration.payment_status = 'pending'
                    registration.verified = False
                elif not event.has_payment_required:
                    registration.payment_status = 'not_required'
                    registration.verified = True
                else:
                    registration.payment_status = 'pending'
                    registration.verified = False
                
                registration.save()
                registered_count += 1
                
                # Send notification to student
                send_realtime_notification(
                    student.id,
                    f"Your teacher, {request.user.get_full_name()}, has registered you for {event.title}",
                    type='event'
                )
                
                # Send email to student
                try:
                    from django.core.mail import send_mail
                    subject = f'Event Registration: {event.title}'
                    message = f"""
Hello {student.get_full_name()},

Your teacher, {request.user.get_full_name()}, has registered you for the following event:

Event: {event.title}
Date: {event.date.strftime('%B %d, %Y')}
Time: {event.time.strftime('%I:%M %p')}
Location: {event.location}

{event.description}

Please log in to view more details.

Best regards,
Boy Scout System
"""
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [student.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    pass  # Silently fail email
            
            # Notify admins if payment was submitted
            if event.has_payment_required and receipt_image:
                admins = User.objects.filter(rank='admin')
                for admin in admins:
                    send_realtime_notification(
                        admin.id,
                        f"Teacher {request.user.get_full_name()} submitted bulk event payment for {registered_count} students for {event.title} - Total: ₱{total_amount} (Ref: {reference_number})",
                        type='event'
                    )
            
            # Success message
            if registered_count > 0:
                if event.has_payment_required and receipt_image:
                    messages.success(
                        request, 
                        f'Successfully registered {registered_count} student(s) for {event.title}. '
                        f'Total amount: ₱{total_amount}. Payment auto-approved.'
                    )
                else:
                    messages.success(request, f'Successfully registered {registered_count} student(s) for {event.title}.')
            
            if already_registered:
                messages.warning(
                    request, 
                    f'The following students were already registered: {", ".join(already_registered)}'
                )
            
            return redirect('accounts:teacher_dashboard')
    else:
        form = TeacherBulkEventRegistrationForm(teacher=request.user)
    
    # Get upcoming events with payment info
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time')[:5]
    
    return render(request, 'events/teacher_bulk_register.html', {
        'form': form,
        'upcoming_events': upcoming_events,
    })

@login_required
def teacher_mark_attendance(request):
    """Teacher marks attendance for their students"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')
    
    # Get events where teacher's students are registered
    from django.db.models import Q
    managed_students = User.objects.filter(managed_by=request.user)
    
    # Get events with registrations from teacher's students
    events_with_students = Event.objects.filter(
        registrations__user__in=managed_students
    ).distinct().order_by('-date', '-time')[:10]
    
    selected_event = None
    students_attendance = []
    
    if request.method == 'POST':
        if 'select_event' in request.POST:
            event_id = request.POST.get('event')
            if event_id:
                selected_event = get_object_or_404(Event, pk=event_id)
                # Get teacher's students registered for this event
                registered_students = User.objects.filter(
                    managed_by=request.user,
                    event_registrations__event=selected_event
                ).distinct()
                
                # Get existing attendance
                for student in registered_students:
                    attendance = Attendance.objects.filter(event=selected_event, user=student).first()
                    students_attendance.append({
                        'student': student,
                        'attendance': attendance,
                    })
        
        elif 'mark_attendance' in request.POST:
            event_id = request.POST.get('event_id')
            selected_event = get_object_or_404(Event, pk=event_id)
            
            marked_count = 0
            for key, value in request.POST.items():
                if key.startswith('attendance_'):
                    student_id = key.split('_')[1]
                    student = get_object_or_404(User, pk=student_id, managed_by=request.user)
                    
                    # Create or update attendance
                    attendance, created = Attendance.objects.update_or_create(
                        event=selected_event,
                        user=student,
                        defaults={
                            'status': value,
                            'marked_by': request.user,
                        }
                    )
                    marked_count += 1
            
            messages.success(request, f'Attendance marked for {marked_count} student(s).')
            return redirect('accounts:teacher_dashboard')
    
    return render(request, 'events/teacher_mark_attendance.html', {
        'events_with_students': events_with_students,
        'selected_event': selected_event,
        'students_attendance': students_attendance,
    })


# PayMongo Webhook Endpoint
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
from .paymongo_service import PayMongoService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def paymongo_webhook(request):
    """
    Handle PayMongo webhook events:
    - source.chargeable: Create payment when source becomes chargeable
    - payment.paid: Mark payment as verified
    - payment.failed: Mark payment as failed
    """
    try:
        # Get webhook data
        payload = request.body.decode('utf-8')
        signature = request.META.get('HTTP_PAYMONGO_SIGNATURE', '')
        
        # Verify webhook signature
        paymongo_service = PayMongoService()
        if not paymongo_service.verify_webhook_signature(payload, signature):
            logger.warning("Invalid PayMongo webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parse webhook data
        data = json.loads(payload)
        event_type = data.get('data', {}).get('attributes', {}).get('type')
        event_data = data.get('data', {}).get('attributes', {}).get('data', {})
        
        logger.info(f"PayMongo webhook received: {event_type}")
        
        if event_type == 'source.chargeable':
            # Source is ready to be charged - create payment
            source_id = event_data.get('id')
            
            # Find the payment record
            payment = EventPayment.objects.filter(paymongo_source_id=source_id).first()
            if not payment:
                logger.error(f"Payment not found for source: {source_id}")
                return JsonResponse({'error': 'Payment not found'}, status=404)
            
            # Create payment via PayMongo
            payment_response = paymongo_service.create_payment(
                source_id=source_id,
                amount=payment.amount,
                description=f"Event Payment - {payment.registration.event.title}"
            )
            
            if payment_response and payment_response.get('data'):
                payment_id = payment_response['data']['id']
                payment.paymongo_payment_id = payment_id
                payment.status = 'processing'
                payment.save()
                
                # Update registration payment status
                payment.registration.payment_status = 'pending'
                payment.registration.save()
                
                logger.info(f"Payment created: {payment_id}")
            else:
                payment.status = 'failed'
                payment.save()
                
                # Update registration payment status
                payment.registration.payment_status = 'rejected'
                payment.registration.save()
                
                logger.error(f"Failed to create payment for source: {source_id}")
        
        elif event_type == 'payment.paid':
            # Payment successful - mark as verified
            payment_id = event_data.get('id')
            
            # Find the payment record
            payment = EventPayment.objects.filter(paymongo_payment_id=payment_id).first()
            if not payment:
                logger.error(f"Payment not found for payment_id: {payment_id}")
                return JsonResponse({'error': 'Payment not found'}, status=404)
            
            # Mark payment as verified
            payment.status = 'verified'
            payment.verification_date = timezone.now()
            payment.save()
            
            # Update registration payment status
            registration = payment.registration
            registration.payment_status = 'paid'
            registration.verified = True
            registration.verification_date = timezone.now()
            registration.save()
            
            # Send notification to user
            NotificationService.send_notification(
                user=registration.user,
                title="Payment Verified",
                message=f"Your payment for {registration.event.title} has been verified. Your registration is confirmed!",
                notification_type='payment',
                related_object=payment
            )
            
            logger.info(f"Payment verified: {payment_id}")
        
        elif event_type == 'payment.failed':
            # Payment failed - mark as failed
            payment_id = event_data.get('id')
            
            # Find the payment record
            payment = EventPayment.objects.filter(paymongo_payment_id=payment_id).first()
            if not payment:
                logger.error(f"Payment not found for payment_id: {payment_id}")
                return JsonResponse({'error': 'Payment not found'}, status=404)
            
            # Mark payment as failed
            payment.status = 'failed'
            payment.save()
            
            # Update registration payment status
            payment.registration.payment_status = 'rejected'
            payment.registration.save()
            
            # Send notification to user
            NotificationService.send_notification(
                user=payment.registration.user,
                title="Payment Failed",
                message=f"Payment for {payment.registration.event.title} failed. Please try again.",
                notification_type='payment',
                related_object=payment
            )
            
            logger.info(f"Payment failed: {payment_id}")
        
        return JsonResponse({'status': 'success'}, status=200)
    
    except Exception as e:
        logger.error(f"PayMongo webhook error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def payment_status(request, registration_id, status):
    """
    Payment status page - shows payment result after PayMongo redirect
    Auto-refreshes to check payment status from webhooks
    """
    registration = get_object_or_404(EventRegistration, id=registration_id, user=request.user)
    
    # Get latest payment for this registration
    latest_payment = EventPayment.objects.filter(
        event_registration=registration
    ).order_by('-created_at').first()
    
    context = {
        'registration': registration,
        'payment': latest_payment,
        'status': status,
        'event': registration.event,
    }
    
    return render(request, 'events/payment_status.html', context)


@login_required
def clear_paymongo_session(request):
    """Clear PayMongo checkout URL from session after opening in new tab"""
    if 'paymongo_checkout_url' in request.session:
        del request.session['paymongo_checkout_url']
    return JsonResponse({'status': 'ok'})
