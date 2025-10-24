from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Event, EventPhoto, Attendance, EventRegistration, EventPayment
from .forms import EventForm, EventPhotoForm, EventRegistrationForm
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
    """
    Display events in a calendar view.
    Gate events for scouts until registration is verified.
    """
    # Gate events for scouts until registration is verified
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_registration_complete:
        messages.warning(request, 'Events are locked until your registration payment is verified.')
        return redirect('accounts:registration_payment', user_id=request.user.id)
    
    return render(request, 'events/event_list.html')

@login_required
def event_calendar_data(request):
    """
    JSON API endpoint for calendar events data.
    Returns all events in FullCalendar JSON format.
    """
    # Gate events for scouts until registration is verified
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_registration_complete:
        return JsonResponse({'error': 'Events are locked until registration is verified'}, status=403)
    
    # Get all events
    events = Event.objects.all().select_related('created_by')
    
    # Format events for FullCalendar
    calendar_events = []
    for event in events:
        calendar_events.append({
            'id': event.pk,
            'title': event.title,
            'start': event.date.isoformat(),  # ISO format for date
            'url': f'/events/{event.pk}/',  # Link to event detail page
            'extendedProps': {
                'location': event.location,
                'time': event.time.strftime('%I:%M %p'),
                'description': event.description[:100] + '...' if len(event.description) > 100 else event.description,
            }
        })
    
    return JsonResponse(calendar_events, safe=False)

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
    """
    Display event details and handle event registration with QR PH payment.
    For paid events, generate PayMongo QR code instead of manual receipt upload.
    """
    # Gate events for scouts until registration is verified
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_registration_complete:
        messages.warning(request, 'Events are locked until your registration payment is verified.')
        return redirect('accounts:registration_payment', user_id=request.user.id)
    
    event = get_object_or_404(Event, pk=pk)
    
    # Get event photos
    photos = event.photos.all().order_by('-is_featured', '-uploaded_at')
    
    # Attendance summary
    attendance_qs = event.attendances.select_related('user')
    present_list = [a.user for a in attendance_qs if a.status == 'present']
    absent_list = [a.user for a in attendance_qs if a.status == 'absent']
    present_count = len(present_list)
    absent_count = len(absent_list)
    total_scouts = present_count + absent_count

    # Check if user already registered
    registration = None
    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
    
    # Handle event registration with QR PH payment
    if request.method == 'POST' and 'register_event' in request.POST and request.user.is_authenticated:
        # Check if already registered
        if registration:
            messages.info(request, 'You are already registered for this event.')
            return redirect('events:event_detail', pk=event.pk)
        
        # Create registration with appropriate payment status
        payment_status = 'pending' if event.has_payment_required else 'not_required'
        registration = EventRegistration.objects.create(
            event=event,
            user=request.user,
            rsvp='yes',
            payment_status=payment_status
        )
        
        # Handle payment based on event requirements
        if event.has_payment_required:
            # Create PayMongo payment source for QR PH
            from payments.services.paymongo_service import PayMongoService
            from decimal import Decimal
            
            try:
                # Initialize PayMongo service
                paymongo = PayMongoService()
                
                # Create payment source
                success, response = paymongo.create_source(
                    amount=event.payment_amount,
                    description=f"Event Registration: {event.title}",
                    redirect_success=request.build_absolute_uri(f'/events/{event.pk}/'),
                    redirect_failed=request.build_absolute_uri(f'/events/{event.pk}/'),
                    metadata={
                        'payment_type': 'event_registration',
                        'event_id': str(event.pk),
                        'event_registration_id': str(registration.pk),
                        'user_id': str(request.user.pk),
                        'event_title': event.title,
                    }
                )
                
                if success and 'data' in response:
                    source_data = response['data']
                    source_id = source_data['id']
                    checkout_url = source_data['attributes']['redirect']['checkout_url']
                    
                    # Create EventPayment record to track this payment
                    event_payment = EventPayment.objects.create(
                        registration=registration,
                        amount=event.payment_amount,
                        status='pending',
                        payment_method='qr_ph',
                        paymongo_source_id=source_id,
                        notes=f"PayMongo QR PH payment for {event.title}"
                    )
                    
                    # Log the payment initiation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Event payment initiated: User {request.user.username}, Event {event.title}, Source {source_id}")
                    
                    # Redirect to PayMongo checkout
                    return redirect(checkout_url)
                else:
                    # PayMongo source creation failed
                    messages.error(request, 'Unable to process payment at this time. Please try again later.')
                    # Delete the registration since payment failed
                    registration.delete()
                    return redirect('events:event_detail', pk=event.pk)
                    
            except Exception as e:
                # Handle any errors
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Event payment error: {str(e)}")
                messages.error(request, 'An error occurred while processing your registration. Please try again.')
                # Delete the registration since payment failed
                registration.delete()
                return redirect('events:event_detail', pk=event.pk)
        else:
            # Free event - auto-approve registration
            registration.payment_status = 'not_required'
            registration.verified = True
            registration.save()
            messages.success(request, 'You have successfully registered for this event!')
            return redirect('events:event_detail', pk=event.pk)

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
        'registrations': registrations,
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
@admin_required
def pending_payments(request):
    """View for admins to see all unpaid event registrations (full payment required)"""
    unpaid_registrations = EventRegistration.objects.filter(
        payment_status='not_required',  # Not paid yet
        event__payment_amount__gt=0  # Only events that require payment
    ).select_related('user', 'event').prefetch_related('payments').order_by('-registered_at')
    
    return render(request, 'events/pending_payments.html', {
        'pending_registrations': unpaid_registrations,  # Keep template variable name for compatibility
    })
