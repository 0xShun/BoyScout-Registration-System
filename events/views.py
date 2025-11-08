# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Event, EventPhoto, Attendance, EventRegistration, EventPayment
import qrcode
import io
import base64
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .forms import EventForm, EventPhotoForm, EventRegistrationForm
from accounts.views import admin_required # Reusing the admin_required decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.http import HttpResponse
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

# Module logger
logger = logging.getLogger(__name__)


def _redirect_to_event(event):
    """Helper to safely redirect to an event detail page or fallback to event list.

    Some code paths may attempt to redirect to an event before the instance has
    a primary key (pk). Use this helper to avoid NoReverseMatch by falling back
    to the event list when pk is missing.
    """
    if event is not None and getattr(event, 'pk', None):
        return redirect('events:event_detail', pk=event.pk)
    return redirect('events:event_list')

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

def send_event_notifications(event, action='created'):
    """Send notifications to all active users about new/updated events"""
    from accounts.models import User
    from django.conf import settings
    from django.urls import reverse
    import logging
    
    logger = logging.getLogger(__name__)
    
    active_users = User.objects.filter(is_active=True)
    
    if action == 'created':
        subject = f"📅 New Event: {event.title}"
        sms_message = f"New event: {event.title} on {event.date}"
    else:  # updated
        subject = f"📅 Event Updated: {event.title}"
        sms_message = f"Event updated: {event.title} on {event.date}"
    
    # Plain text fallback message
    plain_text_message = f"""
Event: {event.title}
Date: {event.date}
Time: {event.time}
Location: {event.location}

{event.description}

Please log in to your dashboard to register.
    """.strip()
    
    # Collect email recipients
    email_recipients = []
    for user in active_users:
        if user.email:
            email_recipients.append(user.email)
        
        # Send SMS if phone number exists
        if user.phone_number:
            NotificationService.send_sms(user.phone_number, sms_message)
    
    # Send HTML email to all recipients
    if email_recipients:
        try:
            context = {
                'event': event,
                'recipient_name': 'Member',
                'event_url': f"{settings.SITE_URL}/events/{event.pk}/",
                'dashboard_url': f"{settings.SITE_URL}/events/",
            }
            
            NotificationService.send_html_email(
                subject=subject,
                recipient_list=email_recipients,
                html_template='notifications/email/event_notification.html',
                context=context,
                plain_text_message=plain_text_message
            )
            logger.info(f"Event notification email sent to {len(email_recipients)} recipients")
        except Exception as e:
            logger.error(f"Failed to send event notification emails: {str(e)}")

@login_required
def event_list(request):
    """
    Display events in a calendar view.
    Gate events for scouts until registration is verified.
    """
    # Force reload of user from DB to ensure latest status
    from accounts.models import User
    user = User.objects.get(pk=request.user.pk)
    # Gate events for scouts until account is active
    if hasattr(user, 'is_scout') and user.is_scout() and not user.is_active:
        messages.warning(request, 'Events are locked until your account is activated.')
        return redirect('accounts:registration_payment', user_id=user.id)
    
    return render(request, 'events/event_list.html')

@login_required
def event_calendar_data(request):
    """
    JSON API endpoint for calendar events data.
    Returns all events in FullCalendar JSON format.
    """
    # Force reload of user from DB to ensure latest status
    from accounts.models import User
    user = User.objects.get(pk=request.user.pk)
    # Gate events for scouts until account is active
    if hasattr(user, 'is_scout') and user.is_scout() and not user.is_active:
        return JsonResponse({'error': 'Events are locked until your account is activated.'}, status=403)
    
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
            return _redirect_to_event(event)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form})

@login_required
def event_detail(request, pk):
    """
    Display event details and handle event registration with QR PH payment.
    For paid events, generate PayMongo QR code instead of manual receipt upload.
    """
    # Gate events for scouts until account is active
    if hasattr(request.user, 'is_scout') and request.user.is_scout() and not request.user.is_active:
        messages.warning(request, 'Events are locked until your account is activated.')
        return redirect('accounts:registration_payment', user_id=request.user.id)
    
    # entry logged via module logger when needed
    event = get_object_or_404(Event, pk=pk)
    # Include active attendance QR (if any) and render as inline data URI for teacher/admin view
    active_qr = None
    qr_data_uri = None
    try:
        from .models import AttendanceQRCode
        active_qr = AttendanceQRCode.objects.filter(event=event, active=True).order_by('-created_at').first()
        if active_qr and active_qr.is_valid:
            # generate PNG data URI for the token verification URL
            token_url = request.build_absolute_uri(f"/events/attendance/verify/")
            # We will embed only the token in the QR so the scanner UI will POST the token to the verify endpoint
            qr_payload = str(active_qr.token)
            qr_img = qrcode.make(qr_payload)
            buf = io.BytesIO()
            qr_img.save(buf, format='PNG')
            buf.seek(0)
            qr_b64 = base64.b64encode(buf.read()).decode('ascii')
            qr_data_uri = f"data:image/png;base64,{qr_b64}"
    except Exception:
        logger.exception('Failed to generate inline QR image for event_detail')

    # If user was redirected back from PayMongo, try fallback reconciliation
    # using a session-stored pending EventPayment id. This mirrors the
    # behavior used for registration payments so users who are redirected
    # back without a webhook can still have their payment finalized.
    pending_event_payment_id = request.session.pop('pending_event_payment_id', None)
    if pending_event_payment_id:
        try:
            from payments.services.paymongo_service import PayMongoService
            ep = EventPayment.objects.filter(id=pending_event_payment_id).first()
            if ep and ep.status != 'verified' and ep.paymongo_source_id:
                paymongo = PayMongoService()
                found, payment_obj = paymongo.find_payment_by_source(ep.paymongo_source_id)
                if found and payment_obj:
                    payment_id = payment_obj.get('id') or payment_obj.get('attributes', {}).get('id')
                    source = payment_obj.get('attributes', {}).get('source', {})
                    source_id = source.get('id') if isinstance(source, dict) else ep.paymongo_source_id

                    # Finalize the EventPayment
                    ep.status = 'verified'
                    if not ep.paymongo_payment_id:
                        ep.paymongo_payment_id = payment_id
                    ep.verification_date = timezone.now()
                    ep.save()

                    # Update the registration
                    reg = ep.registration
                    try:
                        reg.total_paid = (reg.total_paid or 0) + ep.amount
                    except Exception:
                        from decimal import Decimal
                        reg.total_paid = Decimal(str(getattr(reg, 'total_paid', 0))) + Decimal(str(ep.amount))

                    reg.payment_status = 'paid'
                    reg.verified = True
                    reg.verification_date = timezone.now()
                    reg.save()

                    # Notify the user
                    try:
                        NotificationService.send_email(
                            subject=f'Event Payment Confirmed - {reg.event.title}',
                            message=f"Dear {reg.user.first_name} {reg.user.last_name},\n\nYour payment for '{reg.event.title}' has been confirmed.\n\nThank you!",
                            recipient_list=[reg.user.email]
                        )
                    except Exception:
                        logger.exception('Failed to send event payment confirmation email in fallback')
        except Exception:
            logger.exception('Fallback reconciliation for pending event payment failed')
    # (generate_attendance_qr and verify_attendance are defined below)
    
    
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
            return _redirect_to_event(event)
        
        # Import Decimal at the top
        from decimal import Decimal
        
        # Create registration with appropriate payment status and amounts
        payment_status = 'pending' if event.has_payment_required else 'not_required'
        registration = EventRegistration.objects.create(
            event=event,
            user=request.user,
            rsvp='yes',
            payment_status=payment_status,
            amount_required=event.payment_amount if event.has_payment_required else Decimal('0.00'),
            total_paid=Decimal('0.00')  # Will be set to full amount immediately below
        )
        
        # Handle payment based on event requirements
        if event.has_payment_required:
            # Auto-complete payment in database FIRST (before PayMongo redirect)
            from payments.services.paymongo_service import PayMongoService
            
            # Set registration as verified and paid immediately with FULL payment amount
            registration.payment_status = 'paid'  # Mark as paid
            registration.verified = True
            registration.total_paid = event.payment_amount  # Set to full event payment amount
            registration.save()
            
            # Create EventPayment record with verified status
            event_payment = EventPayment.objects.create(
                registration=registration,
                amount=event.payment_amount,
                status='verified',
                payment_method='qr_ph',
                verified_by=request.user,
                verification_date=timezone.now(),
                notes="Auto-completed payment (test mode - payment already verified)"
            )
            
            # Log the auto-completion
            logger.info(f"Event payment auto-completed for user {request.user.username}, event {event.title}")
            
            # Now create PayMongo redirect (just for demo purposes)
            try:
                paymongo = PayMongoService()
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
                        'note': 'Payment already completed - this is demo redirect only'
                    }
                )
                
                if success and 'data' in response:
                    source_data = response['data']
                    checkout_url = source_data['attributes']['redirect']['checkout_url']
                    event_payment.paymongo_source_id = source_data['id']
                    event_payment.save()
                    
                    messages.success(request, f'Registration complete! Payment of ₱{event.payment_amount} has been recorded. Redirecting to PayMongo for demo...')
                    return redirect(checkout_url)
                else:
                    # PayMongo failed but payment is already complete in our system
                    messages.success(request, f'You have successfully registered for this event! Payment of ₱{event.payment_amount} has been recorded.')
                    return _redirect_to_event(event)
                    
            except Exception as e:
                # PayMongo error but payment is already complete in our system
                logger.error(f"PayMongo redirect failed but payment already complete: {str(e)}")
                messages.success(request, f'You have successfully registered for this event! Payment of ₱{event.payment_amount} has been recorded.')
                return _redirect_to_event(event)
        else:
            # Free event - auto-approve registration
            registration.payment_status = 'not_required'
            registration.verified = True
            registration.save()
            messages.success(request, 'You have successfully registered for this event!')
            return _redirect_to_event(event)

    # Admin: see all registrations
    registrations = None
    if request.user.is_authenticated and request.user.is_admin():
        registrations = EventRegistration.objects.filter(event=event).select_related('user')
        paid_qs = EventRegistration.objects.filter(event=event, payment_status='paid').select_related('user')
        # Build a list including attendance info for admin display
        paid_registrations = []
        attendance_map = {}
        for att in event.attendances.select_related('user'):
            attendance_map[att.user_id] = {
                'status': att.status,
                'timestamp': att.timestamp,
            }
        for reg in paid_qs:
            att = attendance_map.get(reg.user_id)
            paid_registrations.append({
                'registration': reg,
                'attendance': att,
            })
    else:
        paid_registrations = None
        attendance_map = {}

    # render logged at debug level when needed
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
        'paid_registrations': paid_registrations,
        'attendance_map': attendance_map,
    })

@login_required
def generate_attendance_qr(request, pk):
    """Generate a new AttendanceQRCode for the given event.

    Only users with teacher or admin privileges can generate a QR. This view
    creates a new token valid for 24 hours (multiple concurrent tokens allowed).
    """
    event = get_object_or_404(Event, pk=pk)
    # Permission: teacher or admin
    user_role = getattr(request.user, 'role', '')
    if not (request.user.is_staff or user_role == 'teacher' or getattr(request.user, 'is_admin', lambda: False)()):
        raise PermissionDenied()

    # Create a new token without invalidating existing ones — support multiple concurrent tokens
    from .models import AttendanceQRCode
    try:
        expires_at = timezone.now() + timedelta(hours=24)
        qr = AttendanceQRCode.objects.create(event=event, created_by=request.user, expires_at=expires_at, active=True)
        messages.success(request, 'Attendance QR generated successfully.')
    except Exception:
        logger.exception('Failed to generate attendance QR')
        messages.error(request, 'Failed to generate attendance QR. See logs.')

    return _redirect_to_event(event)


@login_required
def download_attendance_qr(request, pk):
    """Server-side PNG download for the latest active AttendanceQRCode for an event.

    Only teachers/admins may download. Returns a PNG attachment.
    """
    event = get_object_or_404(Event, pk=pk)
    user_role = getattr(request.user, 'role', '')
    if not (request.user.is_staff or user_role == 'teacher' or getattr(request.user, 'is_admin', lambda: False)()):
        raise PermissionDenied()

    from .models import AttendanceQRCode
    qr = AttendanceQRCode.objects.filter(event=event, active=True).order_by('-created_at').first()
    if not qr or not qr.is_valid:
        messages.error(request, 'No active attendance QR available to download.')
        return _redirect_to_event(event)

    # Generate PNG bytes
    try:
        img = qrcode.make(str(qr.token))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='image/png')
        filename = f"attendance_qr_{event.pk}.png"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        logger.exception('Failed to generate attendance QR PNG for download')
        messages.error(request, 'Failed to generate QR image.')
        return _redirect_to_event(event)


def public_attendance_qr(request, token):
    """Public shareable PNG endpoint for a QR token UUID.

    This returns the PNG for the token if it's active/valid. The token itself
    is the UUID in the URL; verify endpoint still enforces auth+paid checks.
    """
    from .models import AttendanceQRCode
    try:
        qr = AttendanceQRCode.objects.filter(token=token, active=True).first()
        if not qr or not qr.is_valid:
            return HttpResponse(status=404)

        img = qrcode.make(str(qr.token))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='image/png')
        # Let browsers display inline when opened
        response['Content-Disposition'] = f'inline; filename="attendance_qr_{qr.event.pk}.png"'
        return response
    except Exception:
        logger.exception('Failed to serve public attendance QR PNG')
        return HttpResponse(status=500)


@login_required
def verify_attendance(request):
    """AJAX endpoint that students call to verify attendance by token.

    Expects POST with 'token'. Requires authenticated user and a paid EventRegistration.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    token = request.POST.get('token') or request.POST.get('qr_token')
    if not token:
        # Support JSON body too
        try:
            import json
            payload = json.loads(request.body.decode('utf-8') or '{}')
            token = payload.get('token') or payload.get('qr_token')
        except Exception:
            token = None

    if not token:
        return JsonResponse({'success': False, 'error': 'token missing'}, status=400)

    try:
        from .models import AttendanceQRCode
        qr = AttendanceQRCode.objects.filter(token=token, active=True).first()

        if not qr or not qr.is_valid:
            return JsonResponse({'success': False, 'error': 'invalid_or_expired_token'}, status=400)

        event = qr.event

        # Ensure user has a paid registration
        reg_qs = EventRegistration.objects.filter(event=event, user=request.user, payment_status='paid')
        reg = reg_qs.first()
        if not reg:
            return JsonResponse({'success': False, 'error': 'registration_not_paid_or_missing'}, status=403)

        # Check if attendance already recorded
        existing = Attendance.objects.filter(event=event, user=request.user).first()
        if existing:
            return JsonResponse({'success': True, 'already_marked': True, 'timestamp': existing.timestamp.isoformat()})

        attendance = Attendance.objects.create(event=event, user=request.user, status='present', marked_by=request.user)

        # Broadcast via Channels group
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'event_{event.pk}_attendance',
                {
                    'type': 'attendance.update',
                    'event_id': event.pk,
                    'user_id': request.user.pk,
                    'user_full_name': request.user.get_full_name(),
                    'timestamp': attendance.timestamp.isoformat(),
                    'status': attendance.status,
                }
            )
        except Exception:
            logger.exception('Failed to send channels attendance update')

        # Fallback notification to event creator (if available)
        try:
            if event.created_by and event.created_by.pk:
                send_realtime_notification(event.created_by.pk, f"{request.user.get_full_name()} marked present for {event.title}")
        except Exception:
            logger.exception('Failed to send fallback realtime notification')

        return JsonResponse({'success': True, 'timestamp': attendance.timestamp.isoformat()})

    except Exception:
        logger.exception('Attendance verification failed')
        return JsonResponse({'success': False, 'error': 'internal_error'}, status=500)

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
            return _redirect_to_event(event)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form})


@login_required
def send_event_payment_confirmation_ajax(request, pk):
    """AJAX endpoint called from the event detail page to send a payment confirmation
    email when a registration shows as Fully Paid or Verified. Uses session key to
    avoid duplicate sends in the same user session.
    """
    if request.method != 'POST' or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    try:
        logger.info('send_event_payment_confirmation_ajax called', extra={'user_id': request.user.id if request.user.is_authenticated else None, 'event_id': pk})
        # Find the registration for this user and event
        registration = EventRegistration.objects.filter(event_id=pk, user=request.user).first()
        if not registration:
            return JsonResponse({'success': False, 'error': 'Registration not found'}, status=404)

        # Determine if payment is in a completed state
        paid = registration.payment_status == 'paid' or registration.verified or registration.total_paid >= registration.amount_required
        any_verified_payment = registration.payments.filter(status='verified').exists()
        if not (paid or any_verified_payment):
            return JsonResponse({'success': False, 'error': 'Registration not paid/verified'}, status=400)

        session_key = f'sent_event_email_{registration.pk}'
        if request.session.get(session_key):
            return JsonResponse({'success': True, 'sent': False, 'reason': 'already_sent_in_session'})

        # Build and send the same confirmation email used in server-side flows
        try:
            logger.info('Sending event payment confirmation email', extra={'registration_id': registration.pk, 'user': registration.user.email})
            subject = f'✅ Event Payment Confirmed - {registration.event.title}'
            plain_text_message = f"Dear {registration.user.first_name} {registration.user.last_name},\n\n"
            plain_text_message += f"Your payment for the event '{registration.event.title}' has been confirmed.\n\n"
            plain_text_message += "Thank you and see you at the event!"

            context = {
                'recipient_name': registration.user.first_name or 'Member',
                'event_title': registration.event.title,
                'amount': registration.total_paid or registration.amount_required,
                'event_date': registration.event.date,
                'event_time': registration.event.time,
                'event_location': registration.event.location,
                'reference_number': registration.id,
                'event_url': f"{settings.SITE_URL}/events/{registration.event.pk}/" if hasattr(settings, 'SITE_URL') else "#",
                'is_event_payment': True,
            }

            NotificationService.send_html_email(
                subject=subject,
                recipient_list=[registration.user.email],
                html_template='notifications/email/payment_success.html',
                context=context,
                plain_text_message=plain_text_message
            )
            logger.info('Event payment confirmation email sent', extra={'registration_id': registration.pk, 'recipient': registration.user.email})

            # Optionally send a realtime notification
            try:
                send_realtime_notification(
                    user_id=registration.user.id,
                    message=f'Your payment for "{registration.event.title}" has been confirmed.',
                    notification_type='event_payment_confirmed'
                )
            except Exception:
                logger.exception('Failed to send realtime notification after sending event payment email')

            # Mark as sent in session to avoid duplicates
            request.session[session_key] = True
            request.session.modified = True

            return JsonResponse({'success': True, 'sent': True})
        except Exception:
            logger.exception('Failed to send event payment confirmation email')
            return JsonResponse({'success': False, 'error': 'email_failed'}, status=500)

    except Exception:
        logger.exception('Error in send_event_payment_confirmation_ajax')
        return JsonResponse({'success': False, 'error': 'server_error'}, status=500)

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
                    return _redirect_to_event(event)
                
                # Validate image format
                try:
                    img = Image.open(image)
                    if img.format.lower() not in ['jpeg', 'jpg', 'png', 'gif']:
                        messages.error(request, 'Invalid image format. Please upload JPG, PNG, or GIF.')
                        return _redirect_to_event(event)
                except Exception as e:
                    messages.error(request, 'Invalid image file.')
                    return _redirect_to_event(event)

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
                return _redirect_to_event(event)
                
            except Exception as e:
                    messages.error(request, f'Error uploading photo: {str(e)}')
                    return _redirect_to_event(event)
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
    return _redirect_to_event(photo.event)

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
    
    return _redirect_to_event(photo.event)

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
            
    # Safely redirect to the event detail page (if it exists) or fallback to the list
    # After processing POST we redirect back to the event
    if request.method == 'POST':
        return _redirect_to_event(Event.objects.filter(pk=event_pk).first())

    # For GET requests, render the verification page so an admin can
    # click Verify Payment and enter amount/notes.
    return render(request, 'events/verify_event_registration.html', {'registration': registration, 'event_pk': event_pk})

@login_required
@admin_required
def pending_payments(request):
    """View for admins to see all unpaid event registrations (full payment required)"""
    unpaid_registrations = EventRegistration.objects.filter(
        payment_status='pending',  # Unpaid registrations awaiting verification
        event__payment_amount__gt=0  # Only events that require payment
    ).select_related('user', 'event').prefetch_related('payments').order_by('-registered_at')
    
    return render(request, 'events/pending_payments.html', {
        'pending_registrations': unpaid_registrations,  # Keep template variable name for compatibility
    })


@login_required
@admin_required
def verify_event_registration_ajax(request):
    """AJAX endpoint for admins to verify/reject event payments inline from pending list."""
    if request.method != 'POST' or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    try:
        reg_id = request.POST.get('registration_id')
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action')
        payment_amount = request.POST.get('payment_amount')

        registration = EventRegistration.objects.filter(id=reg_id).first()
        if not registration:
            return JsonResponse({'success': False, 'error': 'Registration not found'}, status=404)

        if payment_id:
            payment = EventPayment.objects.filter(id=payment_id, registration=registration).first()
            if not payment:
                return JsonResponse({'success': False, 'error': 'Payment not found'}, status=404)

            if action == 'verify':
                # Validate amount
                if not payment_amount:
                    return JsonResponse({'success': False, 'error': 'Missing payment amount'}, status=400)
                try:
                    amount = Decimal(payment_amount)
                except Exception:
                    return JsonResponse({'success': False, 'error': 'Invalid amount'}, status=400)

                payment.status = 'verified'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.notes = request.POST.get('notes', '')
                payment.amount = amount
                payment.save()

                # Update registration
                registration.total_paid += payment.amount
                registration.update_payment_status()
                registration.save()

                # Notifications
                try:
                    NotificationService.send_email(
                        subject=f'Event Payment Verified: {registration.event.title}',
                        message=f'Your payment of ₱{payment.amount} for event "{registration.event.title}" has been verified.',
                        recipient_list=[registration.user.email]
                    )
                except Exception:
                    logger.exception('Failed to send verification email')

                return JsonResponse({'success': True, 'status': 'verified', 'amount_paid': str(registration.total_paid)})

            elif action == 'reject':
                payment.status = 'rejected'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.notes = request.POST.get('notes', '')
                payment.save()
                return JsonResponse({'success': True, 'status': 'rejected'})

        else:
            # Legacy verification (no EventPayment)
            if action == 'verify':
                registration.verified = True
                registration.payment_status = 'paid'
                registration.verified_by = request.user
                registration.verification_date = timezone.now()
                registration.payment_notes = request.POST.get('notes', '')
                registration.total_paid = registration.amount_required
                registration.save()
                try:
                    NotificationService.send_email(
                        subject=f'Event Registration Payment Verified: {registration.event.title}',
                        message=f'Your payment for event "{registration.event.title}" has been verified.',
                        recipient_list=[registration.user.email]
                    )
                except Exception:
                    logger.exception('Failed to send verification email')
                return JsonResponse({'success': True, 'status': 'verified', 'amount_paid': str(registration.total_paid)})
            elif action == 'reject':
                registration.verified = False
                registration.payment_status = 'rejected'
                registration.verified_by = request.user
                registration.verification_date = timezone.now()
                registration.payment_notes = request.POST.get('notes', '')
                registration.save()
                return JsonResponse({'success': True, 'status': 'rejected'})

        return JsonResponse({'success': False, 'error': 'Unsupported action'}, status=400)

    except Exception as e:
        logger.exception('AJAX verification error')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
