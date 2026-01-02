from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Event, EventPhoto, Attendance, EventRegistration, EventPayment, AttendanceSession, CertificateTemplate, EventCertificate
from .forms import EventForm, EventPhotoForm, EventRegistrationForm, EventPaymentForm
from accounts.views import admin_required # Reusing the admin_required decorator
from .services.certificate_service import CertificateService
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
import logging
import sys

logger = logging.getLogger(__name__)

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
    
    # Registration logic
    registration = None
    registration_form = None
    if request.user.is_authenticated:
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
                    # Save registration first
                    if not registration:
                        # New registration
                        reg.save()
                        is_update = False
                    else:
                        reg.save()
                        is_update = True
                    
                    # Calculate amount to pay (total - already paid)
                    total_paid = EventPayment.objects.filter(
                        registration=reg,
                        status='verified'
                    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
                    
                    amount_to_pay = event.payment_amount - total_paid
                    
                    # Check if user already has a pending payment
                    existing_pending = EventPayment.objects.filter(
                        registration=reg,
                        status='pending'
                    ).first()
                    
                    # Update payment status
                    if amount_to_pay > 0:
                        reg.payment_status = 'pending'
                    else:
                        reg.payment_status = 'paid'
                    reg.save()
                    
                    # Only create new payment if no pending payment exists and amount is due
                    if amount_to_pay > 0 and not existing_pending:
                        # Create PayMongo source for QR payment
                        from .paymongo_service import PayMongoService
                        paymongo_service = PayMongoService()
                        
                        # Get selected payment method from form
                        payment_method = request.POST.get('payment_method', 'gcash')
                        
                        # Build absolute URLs for redirects
                        success_url = request.build_absolute_uri(f'/events/payment-status/{reg.id}/success/')
                        failed_url = request.build_absolute_uri(f'/events/payment-status/{reg.id}/failed/')
                        
                        source_response = paymongo_service.create_source(
                            amount=amount_to_pay,
                            type=payment_method,  # gcash, grab_pay, or paymaya
                            redirect_success=success_url,
                            redirect_failed=failed_url,
                            metadata={
                                'registration_id': str(reg.id),
                                'event_id': str(event.id),
                                'user_id': str(request.user.id)
                            }
                        )
                        
                        if source_response and 'id' in source_response and 'attributes' in source_response:
                            source_id = source_response['id']
                            checkout_url = source_response['attributes']['redirect']['checkout_url']
                            return_url_data = source_response['attributes'].get('redirect', {})
                            expires_at_str = return_url_data.get('return_url_expires_at')
                            
                            # Create EventPayment record
                            payment = EventPayment.objects.create(
                                registration=reg,
                                amount=amount_to_pay,
                                paymongo_source_id=source_id,
                                paymongo_checkout_url=checkout_url,
                                payment_method=f'paymongo_{payment_method}',
                                status='pending',
                                expires_at=timezone.datetime.fromisoformat(expires_at_str.replace('Z', '+00:00')) if expires_at_str else None
                            )
                            
                            messages.success(request, 'Registration created! Click the "Pay Now" button below to complete your payment.')
                            # Store checkout URL in session to open in new tab
                            request.session['paymongo_checkout_url'] = checkout_url
                            return redirect('events:event_detail', pk=event.pk)
                        else:
                            # Log the error for debugging
                            print(f"PayMongo source creation failed. Response: {source_response}")
                            messages.error(request, 'Failed to create payment link. Please try again.')
                            return redirect('events:event_detail', pk=event.pk)
                    elif amount_to_pay > 0 and existing_pending:
                        # User already has pending payment
                        if is_update:
                            messages.success(request, 'Registration updated! Use the "Pay Now" button below to complete payment.')
                        else:
                            messages.success(request, 'Registration created! Use the "Pay Now" button below to complete payment.')
                        return redirect('events:event_detail', pk=event.pk)
                    else:
                        # Already fully paid - status already set above
                        if is_update:
                            messages.success(request, 'Registration updated! Payment already complete.')
                        else:
                            messages.success(request, 'Registration created! Payment already complete.')
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
    # Teacher: see their own students' registrations
    registrations = None
    if request.user.is_authenticated:
        if request.user.is_admin():
            registrations = EventRegistration.objects.filter(event=event).select_related('user').prefetch_related('payments')
        elif request.user.is_teacher():
            # Get registrations for students that belong to this teacher
            registrations = EventRegistration.objects.filter(
                event=event,
                user__managed_by=request.user
            ).select_related('user').prefetch_related('payments')
    
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

# ==================== TEACHER VIEWS ====================

@login_required
def teacher_register_students_event(request):
    """Teacher registers multiple students for an event with PayMongo payment"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')
    
    from .forms import TeacherBulkEventRegistrationForm
    from .paymongo_service import PayMongoService
    
    if request.method == 'POST':
        logger.error("=" * 80)
        logger.error("DEBUG: Teacher Bulk Event Registration - POST request received")
        logger.error(f"POST data: {request.POST}")
        logger.error(f"User: {request.user.email}")
        
        form = TeacherBulkEventRegistrationForm(request.POST, teacher=request.user)
        logger.error(f"Form created. Is valid: {form.is_valid()}")
        
        if not form.is_valid():
            logger.error(f"FORM ERRORS: {form.errors}")
            logger.error(f"Form non-field errors: {form.non_field_errors()}")
            logger.error("=" * 80)
            # Show errors on page too
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        if form.is_valid():
            event = form.cleaned_data['event']
            students = form.cleaned_data['students']
            logger.error(f"Event: {event.title}")
            logger.error(f"Students count: {len(students)}")
            logger.error(f"Students: {[s.get_full_name() for s in students]}")
            
            # Check for already registered students
            already_registered = []
            students_to_register = []
            
            for student in students:
                if EventRegistration.objects.filter(event=event, user=student).exists():
                    already_registered.append(student.get_full_name())
                else:
                    students_to_register.append(student)
            
            logger.error(f"Already registered: {already_registered}")
            logger.error(f"Students to register: {[s.get_full_name() for s in students_to_register]}")
            
            if not students_to_register:
                logger.error("No students to register - all already registered")
                logger.error("=" * 80)
                messages.warning(request, 'All selected students are already registered for this event.')
                return redirect('events:teacher_register_students_event')
            
            # Calculate total amount
            total_amount = Decimal('0.00')
            if event.has_payment_required:
                total_amount = event.payment_amount * len(students_to_register)
            
            logger.error(f"Event has payment required: {event.has_payment_required}")
            logger.error(f"Event payment amount: {event.payment_amount}")
            logger.error(f"Total amount: {total_amount}")
            
            # If free event, register immediately
            if not event.has_payment_required or total_amount == 0:
                logger.error("FREE EVENT - Registering immediately")
                registered_count = 0
                for student in students_to_register:
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=student,
                        rsvp='yes',
                        amount_required=Decimal('0.00'),
                        payment_status='not_required',
                        verified=True,
                        verification_date=timezone.now()
                    )
                    registered_count += 1
                    
                    # Send notification to student
                    send_realtime_notification(
                        student.id,
                        f"Your teacher has registered you for {event.title}",
                        type='event'
                    )
                
                if already_registered:
                    messages.warning(request, f'Already registered: {", ".join(already_registered)}')
                
                logger.error(f"Successfully registered {registered_count} students for free event")
                logger.error("=" * 80)
                messages.success(request, f'Successfully registered {registered_count} student(s) for {event.title}.')
                return redirect('events:event_detail', pk=event.id)
            
            # Create event registrations (pending payment)
            logger.error("PAID EVENT - Creating PayMongo payment")
            registrations_created = []
            for student in students_to_register:
                registration = EventRegistration.objects.create(
                    event=event,
                    user=student,
                    rsvp='yes',
                    amount_required=event.payment_amount,
                    payment_status='pending',
                    verified=False,
                    total_paid=Decimal('0.00')
                )
                registrations_created.append(registration)
            
            logger.error(f"Created {len(registrations_created)} pending registrations")
            
            # Create PayMongo source for bulk payment
            paymongo = PayMongoService()
            
            try:
                # Build redirect URL
                redirect_url = request.build_absolute_uri(
                    f'/events/teacher-bulk-event-payment-status/{event.id}/'
                )
                
                logger.error(f"Redirect URL: {redirect_url}")
                
                # Get student names for description
                student_names = ', '.join([s.get_full_name() for s in students_to_register[:3]])
                if len(students_to_register) > 3:
                    student_names += f' and {len(students_to_register) - 3} more'
                
                logger.error(f"Creating PayMongo source for ₱{total_amount}")
                logger.error(f"Description: Event Registration for {len(students_to_register)} students: {student_names}")
                
                source_data = paymongo.create_source(
                    amount=total_amount,
                    type='gcash',
                    redirect_success=redirect_url,
                    redirect_failed=redirect_url,
                    metadata={
                        'teacher_email': str(request.user.email),
                        'teacher_name': str(request.user.get_full_name()),
                        'event_id': str(event.id),
                        'event_title': str(event.title),
                        'student_count': str(len(students_to_register)),
                        'student_names': student_names,
                        'payment_type': 'bulk_event_registration',
                    }
                )
                
                logger.error(f"PayMongo response: {source_data}")
                
                if not source_data or 'id' not in source_data:
                    logger.error("ERROR: Failed to create PayMongo source")
                    logger.error(f"Source data: {source_data}")
                    # Rollback registrations
                    for reg in registrations_created:
                        reg.delete()
                    logger.error("=" * 80)
                    messages.error(request, 'Failed to create PayMongo payment. Please try again.')
                    return redirect('events:teacher_register_students_event')
                
                source_id = source_data['id']
                checkout_url = source_data['attributes']['redirect']['checkout_url']
                
                logger.error(f"PayMongo source created: {source_id}")
                logger.error(f"Checkout URL: {checkout_url}")
                
                # Create ONE EventPayment record for the bulk payment (linked to first registration)
                # The other registrations will be updated when payment is verified
                bulk_payment = EventPayment.objects.create(
                    registration=registrations_created[0],  # Link to first registration
                    amount=total_amount,  # Total amount for all students
                    paymongo_source_id=source_id,
                    paymongo_checkout_url=checkout_url,
                    status='pending',
                    notes=f"Bulk payment for {len(registrations_created)} students by teacher {request.user.get_full_name()}"
                )
                
                logger.error(f"Created bulk EventPayment: {bulk_payment.id}")
                
                # Store registration IDs in session for verification later
                request.session['bulk_event_registration_ids'] = [r.id for r in registrations_created]
                
                logger.error(f"Stored {len(registrations_created)} registration IDs in session")
                logger.error(f"REDIRECTING TO PAYMONGO: {checkout_url}")
                logger.error("=" * 80)
                
                # Redirect to PayMongo checkout
                return redirect(checkout_url)
                
            except Exception as e:
                logger.error(f"EXCEPTION occurred: {str(e)}")
                logger.error(f"Exception type: {type(e)}")
                import traceback
                logger.error(traceback.format_exc())
                logger.error(f"Exception creating bulk event PayMongo payment: {str(e)}", exc_info=True)
                # Rollback registrations
                for reg in registrations_created:
                    reg.delete()
                logger.error("Rolled back registrations due to exception")
                logger.error("=" * 80)
                messages.error(request, f'Error creating payment: {str(e)}. Please try again.')
                return redirect('events:teacher_register_students_event')
    else:
        logger.error("GET request - displaying form")
        form = TeacherBulkEventRegistrationForm(teacher=request.user)
    
    # Get upcoming events with payment info
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time')[:5]
    
    return render(request, 'events/teacher_bulk_register.html', {
        'form': form,
        'upcoming_events': upcoming_events,
    })

@login_required
def teacher_bulk_event_payment_status(request, event_id):
    """Handle PayMongo redirect after bulk event registration payment"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')
    
    event = get_object_or_404(Event, id=event_id)
    
    # Get registration IDs from session
    registration_ids = request.session.get('bulk_event_registration_ids', [])
    
    if not registration_ids:
        messages.warning(request, 'No pending registration payment session found.')
        return redirect('events:event_detail', pk=event.id)
    
    from .paymongo_service import PayMongoService
    
    # Get all registrations
    registrations = EventRegistration.objects.filter(id__in=registration_ids)
    
    if not registrations.exists():
        messages.error(request, 'Registration records not found.')
        return redirect('events:event_detail', pk=event.id)
    
    # Get the first payment to check PayMongo source status
    first_payment = EventPayment.objects.filter(registration__in=registrations).first()
    
    if first_payment and first_payment.paymongo_source_id:
        paymongo = PayMongoService()
        source_data = paymongo.get_source(first_payment.paymongo_source_id)
        
        if source_data and 'data' in source_data:
            source_status = source_data['data']['attributes']['status']
            
            # If source is chargeable, create payment
            if source_status == 'chargeable':
                total_amount = sum(r.amount_required for r in registrations)
                description = f"Bulk Event Registration - {len(registrations)} students for {event.title}"
                
                payment_response = paymongo.create_payment(
                    source_id=first_payment.paymongo_source_id,
                    amount=total_amount,
                    description=description
                )
                
                if payment_response and payment_response.get('data'):
                    payment_id = payment_response['data']['id']
                    payment_status = payment_response['data']['attributes']['status']
                    
                    # If paid, verify all registrations
                    if payment_status == 'paid':
                        # Update the bulk EventPayment record
                        first_payment.paymongo_payment_id = payment_id
                        first_payment.status = 'verified'
                        first_payment.verification_date = timezone.now()
                        first_payment.save()
                        
                        # Update all registrations (no need to create individual EventPayment records
                        # since they all share the same bulk payment)
                        for registration in registrations:
                            # Update registration status
                            registration.total_paid = registration.amount_required
                            registration.payment_status = 'paid'
                            registration.verified = True
                            registration.verification_date = timezone.now()
                            registration.save()
                            
                            # Send notification to student
                            send_realtime_notification(
                                user_id=registration.user.id,
                                message=f"Your event registration for {event.title} has been confirmed! Payment verified.",
                                type='event'
                            )
                        
                        # Clear session
                        del request.session['bulk_event_registration_ids']
                        
                        messages.success(
                            request,
                            f'Payment verified! {len(registrations)} student(s) successfully registered for {event.title}.'
                        )
                        return redirect('events:event_detail', pk=event.id)
    
    # If not verified yet, show waiting message and redirect
    messages.info(request, 'Processing payment... Please wait.')
    return redirect('events:event_detail', pk=event.id)

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
    # CRITICAL DEBUG: Log every webhook request
    print("=" * 80)
    print("🔔 PAYMONGO WEBHOOK RECEIVED")
    print("=" * 80)
    
    try:
        # Get webhook data (keep as bytes for signature verification)
        payload_bytes = request.body
        signature = request.META.get('HTTP_PAYMONGO_SIGNATURE', '')
        
        # Log incoming webhook with full details
        print(f"📥 Webhook Payload (first 500 chars): {payload_bytes.decode('utf-8')[:500]}...")
        print(f"🔐 Signature Present: {bool(signature)}")
        logger.info(f"PayMongo webhook received - Signature present: {bool(signature)}")
        
        # Verify webhook signature
        paymongo_service = PayMongoService()
        
        # TEMPORARY: Skip signature verification in test mode for debugging
        # TODO: Re-enable signature verification in production
        verify_signature = getattr(settings, 'PAYMONGO_VERIFY_WEBHOOK', True)
        if verify_signature and not paymongo_service.verify_webhook_signature(payload_bytes, signature):
            logger.warning("Invalid PayMongo webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Now decode the payload for processing
        payload = payload_bytes.decode('utf-8')
        logger.info(f"Webhook payload: {payload}")
        
        # Parse webhook data
        data = json.loads(payload)
        event_type = data.get('data', {}).get('attributes', {}).get('type')
        event_data = data.get('data', {}).get('attributes', {}).get('data', {})
        
        print(f"📋 Event Type: {event_type}")
        print(f"📦 Event Data ID: {event_data.get('id', 'N/A')}")
        logger.info(f"PayMongo webhook event type: {event_type}")
        logger.info(f"Event data: {json.dumps(event_data, indent=2)}")
        
        if event_type == 'source.chargeable':
            print("💳 Processing source.chargeable event...")
            # Source is ready to be charged - create payment
            source_id = event_data.get('id')
            print(f"🔍 Looking for payment with source_id: {source_id}")
            
            # Find the payment record (check both EventPayment and RegistrationPayment)
            payment = EventPayment.objects.filter(paymongo_source_id=source_id).first()
            registration_payment = None
            
            if not payment:
                print("   Not found in EventPayment, checking RegistrationPayment...")
                # Check if it's a registration payment
                from accounts.models import RegistrationPayment
                registration_payment = RegistrationPayment.objects.filter(paymongo_source_id=source_id).first()
                
                if not registration_payment:
                    print(f"❌ ERROR: Payment not found for source: {source_id}")
                    logger.error(f"Payment not found for source: {source_id}")
                    return JsonResponse({'error': 'Payment not found'}, status=404)
                else:
                    print(f"✅ Found RegistrationPayment: ID={registration_payment.id}, User={registration_payment.user.email}")
                    logger.info(f"Found registration payment for source: {source_id}, User: {registration_payment.user.email}")
            else:
                print(f"✅ Found EventPayment: ID={payment.id}")
            
            # Create payment via PayMongo
            if payment:
                # Event payment
                description = f"Event Payment - {payment.registration.event.title}"
                print(f"💰 Creating payment for Event: {description}")
            else:
                # Registration payment
                description = f"Registration Fee - {registration_payment.user.get_full_name()}"
                print(f"💰 Creating payment for Registration: {description}")
            
            print(f"🚀 Calling PayMongo API to create payment...")
            payment_response = paymongo_service.create_payment(
                source_id=source_id,
                amount=payment.amount if payment else registration_payment.amount,
                description=description
            )
            
            print(f"📨 PayMongo Response: {json.dumps(payment_response, indent=2) if payment_response else 'None'}")
            
            if payment_response and payment_response.get('data'):
                payment_id = payment_response['data']['id']
                print(f"✅ Payment created successfully: {payment_id}")
                
                if payment:
                    # Update EventPayment
                    payment.paymongo_payment_id = payment_id
                    payment.status = 'processing'
                    payment.save()
                    
                    # Update registration payment status
                    payment.registration.payment_status = 'pending'
                    payment.registration.save()
                    print(f"✅ EventPayment updated to processing")
                else:
                    # Update RegistrationPayment
                    registration_payment.paymongo_payment_id = payment_id
                    registration_payment.status = 'processing'
                    registration_payment.save()
                    print(f"✅ RegistrationPayment updated to processing")
                
                logger.info(f"Payment created: {payment_id}")
            else:
                print(f"❌ Failed to create payment - No response from PayMongo")
                if payment:
                    payment.status = 'failed'
                    payment.save()
                    payment.registration.payment_status = 'rejected'
                    payment.registration.save()
                else:
                    registration_payment.status = 'failed'
                    registration_payment.save()
                
                logger.error(f"Failed to create payment for source: {source_id}")
        
        elif event_type == 'payment.paid':
            print("✅ Processing payment.paid event...")
            # Payment successful - mark as verified
            payment_id = event_data.get('id')
            print(f"🔍 Looking for payment with payment_id: {payment_id}")
            
            # Find the payment record (check both EventPayment and RegistrationPayment)
            payment = EventPayment.objects.filter(paymongo_payment_id=payment_id).first()
            registration_payment = None
            
            if not payment:
                print("   Not found in EventPayment, checking RegistrationPayment...")
                # Check if it's a registration payment
                from accounts.models import RegistrationPayment
                registration_payment = RegistrationPayment.objects.filter(paymongo_payment_id=payment_id).first()
                
                if not registration_payment:
                    print(f"❌ ERROR: Payment not found for payment_id: {payment_id}")
                    logger.error(f"Payment not found for payment_id: {payment_id}")
                    return JsonResponse({'error': 'Payment not found'}, status=404)
                else:
                    print(f"✅ Found RegistrationPayment: ID={registration_payment.id}, User={registration_payment.user.email}")
            else:
                print(f"✅ Found EventPayment: ID={payment.id}")
            
            if payment:
                # Event payment - mark as verified
                print(f"💚 Marking EventPayment as verified...")
                payment.status = 'verified'
                payment.verification_date = timezone.now()
                payment.save()
                
                # Update registration total paid and payment status
                registration = payment.registration
                registration.total_paid += payment.amount
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
                
                logger.info(f"Event payment verified: {payment_id}")
                print(f"✅ EventPayment verified successfully")
            else:
                # Registration payment - mark as verified
                print(f"💚 Marking RegistrationPayment as verified...")
                registration_payment.status = 'verified'
                registration_payment.verification_date = timezone.now()
                registration_payment.save()
                print(f"   Status updated to: {registration_payment.status}")
                
                # Update user registration status
                user = registration_payment.user
                print(f"👤 Updating user {user.email} registration status...")
                
                # Update total paid amount
                user.registration_total_paid += registration_payment.amount
                user.registration_status = 'payment_verified'
                user.update_registration_status()  # This will set to 'active' and set membership expiry
                user.save()
                print(f"   User status updated to: {user.registration_status}")
                print(f"   User is_active: {user.is_active}")
                print(f"   Total paid: ₱{user.registration_total_paid}")
                
                # Send notification to user
                NotificationService.send_notification(
                    user=user,
                    title="Registration Payment Verified",
                    message=f"Your registration payment of ₱{registration_payment.amount} has been verified. Welcome to Boy Scout System!",
                    notification_type='payment',
                    related_object=registration_payment
                )
                
                # Notify admins
                from accounts.models import User as UserModel
                admins = UserModel.objects.filter(rank='admin')
                for admin in admins:
                    NotificationService.send_notification(
                        user=admin,
                        title="New Member Registered",
                        message=f"{user.get_full_name()} has completed registration payment and is now an active member.",
                        notification_type='registration'
                    )
                
                logger.info(f"Registration payment verified: {payment_id} for user: {user.email}")
                print(f"✅ RegistrationPayment verified successfully")
                print(f"📧 Notifications sent to user and admins")
        
        elif event_type == 'payment.failed':
            # Payment failed - mark as failed
            payment_id = event_data.get('id')
            
            # Find the payment record (check both EventPayment and RegistrationPayment)
            payment = EventPayment.objects.filter(paymongo_payment_id=payment_id).first()
            registration_payment = None
            
            if not payment:
                # Check if it's a registration payment
                from accounts.models import RegistrationPayment
                registration_payment = RegistrationPayment.objects.filter(paymongo_payment_id=payment_id).first()
                
                if not registration_payment:
                    logger.error(f"Payment not found for payment_id: {payment_id}")
                    return JsonResponse({'error': 'Payment not found'}, status=404)
            
            if payment:
                # Event payment failed
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
                
                logger.info(f"Event payment failed: {payment_id}")
            else:
                # Registration payment failed
                registration_payment.status = 'failed'
                registration_payment.save()
                
                # Send notification to user
                NotificationService.send_notification(
                    user=registration_payment.user,
                    title="Registration Payment Failed",
                    message=f"Your registration payment failed. Please try again or contact support.",
                    notification_type='payment',
                    related_object=registration_payment
                )
                
                logger.info(f"Registration payment failed: {payment_id}")
        
        print("=" * 80)
        print("✅ WEBHOOK PROCESSED SUCCESSFULLY")
        print("=" * 80)
        return JsonResponse({'status': 'success'}, status=200)
    
    except Exception as e:
        print("=" * 80)
        print(f"❌ WEBHOOK ERROR: {str(e)}")
        print("=" * 80)
        logger.error(f"PayMongo webhook error: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def payment_status(request, registration_id, status):
    """
    Payment status page - shows payment result after PayMongo redirect
    Immediately checks PayMongo source status and creates/verifies payment
    """
    registration = get_object_or_404(EventRegistration, id=registration_id, user=request.user)
    
    # Get latest payment for this registration
    latest_payment = EventPayment.objects.filter(
        registration=registration
    ).order_by('-created_at').first()
    
    # If payment is pending, check PayMongo source status immediately
    if latest_payment and latest_payment.status == 'pending' and latest_payment.paymongo_source_id:
        from .paymongo_service import PayMongoService
        paymongo = PayMongoService()
        source_data = paymongo.get_source(latest_payment.paymongo_source_id)
        
        if source_data and 'data' in source_data:
            source_status = source_data['data']['attributes']['status']
            
            # If source is chargeable, create payment immediately
            if source_status == 'chargeable':
                print(f"🔍 Source is chargeable for registration {registration.id}, creating payment...")
                
                # Create payment via PayMongo
                description = f"Event Payment - {registration.event.title}"
                payment_response = paymongo.create_payment(
                    source_id=latest_payment.paymongo_source_id,
                    amount=latest_payment.amount,
                    description=description
                )
                
                if payment_response and payment_response.get('data'):
                    payment_id = payment_response['data']['id']
                    payment_status_value = payment_response['data']['attributes']['status']
                    
                    # Update EventPayment with payment ID
                    latest_payment.paymongo_payment_id = payment_id
                    latest_payment.status = 'processing'
                    latest_payment.save()
                    
                    # If payment is already paid, mark as verified immediately
                    if payment_status_value == 'paid':
                        print(f"✅ Payment already paid, marking as verified...")
                        latest_payment.status = 'verified'
                        latest_payment.verification_date = timezone.now()
                        latest_payment.save()
                        
                        # Update registration total paid and payment status
                        registration.total_paid += latest_payment.amount
                        registration.payment_status = 'paid'
                        registration.verified = True
                        registration.verification_date = timezone.now()
                        registration.save()
                        
                        messages.success(request, 'Payment verified! Your event registration is confirmed.')
                        # Redirect to event detail page instead of showing waiting page
                        return redirect('events:event_detail', pk=registration.event.id)
    
    # If payment is verified, redirect to event page
    if latest_payment and latest_payment.status == 'verified':
        messages.success(request, 'Payment already verified! Your event registration is confirmed.')
        return redirect('events:event_detail', pk=registration.event.id)
    
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


# ========================================
# ATTENDANCE SESSION & CERTIFICATE VIEWS
# ========================================

@login_required
@admin_required
def start_attendance_session(request, event_id):
    """
    Start attendance session for an event (Admin only).
    Sends real-time notifications to all registered students.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    event = get_object_or_404(Event, id=event_id)
    
    # Create or get attendance session
    session, created = AttendanceSession.objects.get_or_create(event=event)
    
    if session.is_active:
        return JsonResponse({'error': 'Attendance session is already active!'}, status=400)
    
    # Start session
    session.start(request.user)
    
    # Send notifications to all registered students
    registered_users = EventRegistration.objects.filter(
        event=event,
        payment_status__in=['not_required', 'paid']
    ).values_list('user', flat=True)
    
    for user_id in registered_users:
        send_realtime_notification(
            user_id=user_id,
            message=f"Attendance is now open for {event.title}. Click to mark your attendance!",
            type='info'
        )
    
    return JsonResponse({
        'success': True,
        'message': f'Attendance session started for {event.title}!'
    })


@login_required
@admin_required
def stop_attendance_session(request, event_id):
    """
    Stop attendance session for an event (Admin only).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    event = get_object_or_404(Event, id=event_id)
    
    try:
        session = AttendanceSession.objects.get(event=event)
        
        if not session.is_active:
            return JsonResponse({'error': 'Attendance session is not active!'}, status=400)
        
        # Stop session
        session.stop()
        
        return JsonResponse({
            'success': True,
            'message': f'Attendance session stopped for {event.title}!'
        })
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'error': 'No attendance session found for this event!'}, status=404)


@login_required
def check_attendance_status(request, event_id):
    """
    AJAX endpoint to check attendance session status and user's attendance.
    Returns JSON with session status and attendance info.
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is registered and eligible
    try:
        registration = EventRegistration.objects.get(event=event, user=request.user)
        is_eligible = registration.payment_status in ['not_required', 'paid']
    except EventRegistration.DoesNotExist:
        is_eligible = False
    
    # Check session status
    try:
        session = AttendanceSession.objects.get(event=event)
        is_active = session.is_active
    except AttendanceSession.DoesNotExist:
        is_active = False
    
    # Check if user already marked attendance
    has_attended = Attendance.objects.filter(event=event, user=request.user).exists()
    
    # Get attendance count (for admin)
    attendance_count = Attendance.objects.filter(event=event).count() if request.user.is_admin() else 0
    
    return JsonResponse({
        'is_active': is_active,
        'has_attended': has_attended,
        'is_eligible': is_eligible,
        'attendance_count': attendance_count,
    })


@login_required
def mark_my_attendance(request, event_id):
    """
    Student marks their own attendance when session is active.
    Auto-generates certificate if template exists.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    event = get_object_or_404(Event, id=event_id)
    
    # Check if session is active
    try:
        session = AttendanceSession.objects.get(event=event)
        if not session.is_active:
            return JsonResponse({'error': 'Attendance session is not active'}, status=400)
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'error': 'No attendance session for this event'}, status=400)
    
    # Check if user is registered
    try:
        registration = EventRegistration.objects.get(event=event, user=request.user)
    except EventRegistration.DoesNotExist:
        return JsonResponse({'error': 'You are not registered for this event'}, status=403)
    
    # Check payment status
    if registration.payment_status not in ['not_required', 'paid']:
        return JsonResponse({'error': 'Payment required before marking attendance'}, status=403)
    
    # Check if already marked
    if Attendance.objects.filter(event=event, user=request.user).exists():
        return JsonResponse({'error': 'You have already marked your attendance'}, status=400)
    
    # Mark attendance
    attendance = Attendance.objects.create(
        event=event,
        user=request.user,
        status='present',
        marked_by=request.user
    )
    
    # Auto-generate certificate for attendance
    certificate_generated = False
    try:
        # Check if certificate doesn't already exist
        from events.models import EventCertificate
        if not EventCertificate.objects.filter(user=request.user, event=event).exists():
            certificate = CertificateService.generate_certificate(
                user=request.user,
                event=event,
                attendance=attendance
            )
            certificate_generated = True
            
            # Send notification about certificate
            send_realtime_notification(
                user_id=request.user.id,
                message=f"Your certificate for {event.title} has been generated! View it in My Certificates.",
                type='info'
            )
    except Exception as e:
        print(f"Certificate generation error: {e}")
        # Don't fail attendance marking if certificate generation fails
    
    messages.success(request, "Attendance marked successfully!" + 
                     (" Certificate generated!" if certificate_generated else ""))
    
    return JsonResponse({
        'success': True,
        'certificate_generated': certificate_generated,
        'message': 'Attendance marked successfully!'
    })


@login_required
@admin_required
def upload_certificate_template(request, event_id):
    """
    Upload certificate template for an event (Admin only).
    Handles both GET (show form) and POST (save template).
    """
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        # Get or create template
        template, created = CertificateTemplate.objects.get_or_create(event=event)
        
        # Update template image if provided
        if 'template_image' in request.FILES:
            template.template_image = request.FILES['template_image']
        
        # Update positioning fields
        template.name_x = int(request.POST.get('name_x', 500))
        template.name_y = int(request.POST.get('name_y', 400))
        template.name_font_size = int(request.POST.get('name_font_size', 60))
        template.name_color = request.POST.get('name_color', '#000000')
        
        template.event_name_x = int(request.POST.get('event_name_x', 500))
        template.event_name_y = int(request.POST.get('event_name_y', 550))
        template.event_font_size = int(request.POST.get('event_font_size', 40))
        template.event_color = request.POST.get('event_color', '#000000')
        
        template.date_x = int(request.POST.get('date_x', 500))
        template.date_y = int(request.POST.get('date_y', 650))
        template.date_font_size = int(request.POST.get('date_font_size', 30))
        template.date_color = request.POST.get('date_color', '#000000')
        
        template.cert_number_x = int(request.POST.get('cert_number_x', 100))
        template.cert_number_y = int(request.POST.get('cert_number_y', 100))
        template.cert_number_font_size = int(request.POST.get('cert_number_font_size', 20))
        template.cert_number_color = request.POST.get('cert_number_color', '#666666')
        
        template.save()
        
        messages.success(request, "Certificate template saved successfully!")
        return redirect('events:event_detail', pk=event_id)
    
    # GET request - show form
    try:
        template = CertificateTemplate.objects.get(event=event)
    except CertificateTemplate.DoesNotExist:
        template = None
    
    context = {
        'event': event,
        'template': template,
    }
    return render(request, 'events/upload_certificate_template.html', context)


@login_required
@admin_required
def preview_certificate_template(request, event_id):
    """
    Preview certificate template with dummy data (Admin only).
    Returns PNG image.
    """
    event = get_object_or_404(Event, id=event_id)
    
    try:
        template = CertificateTemplate.objects.get(event=event)
    except CertificateTemplate.DoesNotExist:
        messages.error(request, "No certificate template found!")
        return redirect('events:event_detail', pk=event_id)
    
    # Generate preview
    preview_name = request.GET.get('name', 'John Doe')
    preview_event = request.GET.get('event_name', event.title)
    
    try:
        preview_image = CertificateService.preview_certificate(
            template=template,
            preview_name=preview_name,
            preview_event=preview_event
        )
        
        # Return image as response
        from django.http import HttpResponse
        from io import BytesIO
        
        buffer = BytesIO()
        preview_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return HttpResponse(buffer.getvalue(), content_type='image/png')
    
    except Exception as e:
        messages.error(request, f"Error generating preview: {str(e)}")
        return redirect('events:event_detail', pk=event_id)


@login_required
def my_certificates(request):
    """
    Show all certificates earned by the logged-in user.
    """
    certificates = EventCertificate.objects.filter(user=request.user).select_related('event')
    
    context = {
        'certificates': certificates,
    }
    return render(request, 'events/my_certificates.html', context)

