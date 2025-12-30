from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Event, EventPhoto, Attendance, EventRegistration, EventPayment
from .forms import EventForm, EventPhotoForm, EventRegistrationForm, EventPaymentForm
from accounts.views import admin_required # Reusing the admin_required decorator
from django.core.paginator import Paginator
from django.db.models import Q
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
    events = Event.objects.all().order_by('-date', '-time')
    paginator = Paginator(events, 10)
    page = request.GET.get('page')
    events = paginator.get_page(page)
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
        form = EventForm()
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
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
        if request.method == 'POST' and 'register_event' in request.POST:
            if registration:
                registration_form = EventRegistrationForm(request.POST, request.FILES, instance=registration, event=event)
            else:
                registration_form = EventRegistrationForm(request.POST, request.FILES, event=event)
            if registration_form.is_valid():
                reg = registration_form.save(commit=False)
                reg.event = event
                reg.user = request.user
                
                # Handle payment status
                if event.has_payment_required and reg.receipt_image:
                    reg.payment_status = 'pending'
                    reg.verified = False
                elif not event.has_payment_required:
                    reg.payment_status = 'not_required'
                    reg.verified = True
                
                reg.save()
                
                # Send notification to admin if payment is pending
                if reg.payment_status == 'pending':
                    admins = User.objects.filter(rank='admin')
                    for admin in admins:
                        send_realtime_notification(
                            admin.id, 
                            f"New event registration with payment pending: {reg.user.get_full_name()} for {event.title}",
                            type='event'
                        )
                
                messages.success(request, 'Event registration submitted successfully!')
                if reg.payment_status == 'pending':
                    messages.info(request, 'Your payment receipt is pending verification by an administrator.')
                return redirect('events:event_detail', pk=event.pk)
            else:
                messages.error(request, 'There was an error with your registration. Please check the form.')
        else:
            registration_form = EventRegistrationForm(instance=registration, event=event)

    # Admin: see all registrations
    registrations = None
    if request.user.is_authenticated and request.user.is_admin():
        registrations = EventRegistration.objects.filter(event=event).select_related('user')

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
                payment.status = 'rejected'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.notes = notes
                payment.save()
                
                # Email and notification
                subject = f"Event Payment Rejected: {registration.event.title}"
                message = f"Your payment of ₱{payment.amount} for event '{registration.event.title}' has been rejected."
                if notes:
                    message += f"\n\nAdmin notes: {notes}"
                NotificationService.send_email(subject, message, [registration.user.email])
                send_realtime_notification(registration.user.id, f"Your payment of ₱{payment.amount} for '{registration.event.title}' has been rejected.", type='event')
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
                    receipt_image=receipt_image if receipt_image else None,
                    amount_required=event.payment_amount if event.has_payment_required else Decimal('0.00')
                )
                
                # Handle payment auto-approval for teacher submissions
                if event.has_payment_required and receipt_image:
                    registration.payment_status = 'paid'  # Auto-approve teacher payments
                    registration.total_paid = event.payment_amount
                    registration.verified = True
                    registration.verified_by = request.user
                    registration.verification_date = timezone.now()
                else:
                    registration.payment_status = 'not_required'
                    registration.verified = True
                
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
            
            # Success message
            if registered_count > 0:
                if event.has_payment_required:
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
