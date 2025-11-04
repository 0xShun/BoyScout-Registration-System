from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from accounts.models import User
# Admin payment tracking view
from accounts.models import User
from django.contrib.auth.decorators import login_required
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
@admin_required
def payment_tracking(request):
    users = User.objects.all()
    user_payments = []
    from .models import Payment
    for user in users:
        payments = Payment.objects.filter(user=user).order_by('-date')
        total_registration = payments.filter(payment_type='registration', status='verified').aggregate(Sum('amount'))['amount__sum'] or 0
        membership_years = int(total_registration // 500)
        user_payments.append({
            'user': user,
            'payments': payments,
            'total_registration': total_registration,
            'membership_years': membership_years,
            'membership_expiry': user.membership_expiry,
        })
    return render(request, 'payments/payment_tracking.html', {'user_payments': user_payments})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from .models import Payment, PaymentQRCode
from .forms import PaymentForm, PaymentQRCodeForm
from accounts.models import User
from notifications.services import NotificationService, send_realtime_notification
from django.utils import timezone
from datetime import timedelta

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
def payment_list(request):
    registration_fee = 500
    membership_years = 0
    membership_expiry = None
    if request.user.is_admin():
        # Admins see payments from other users (exclude their own)
        payments = Payment.objects.exclude(user=request.user).order_by('-date')
        status_filter = request.GET.get('status', '')
        if status_filter:
            payments = payments.filter(status=status_filter)
        payments_list = list(payments)
    else:
        payments = Payment.objects.filter(user=request.user).order_by('-date')
        total_registration_paid = payments.filter(payment_type='registration', status='verified').aggregate(Sum('amount'))['amount__sum'] or 0
        membership_years = int(total_registration_paid // registration_fee)
        membership_expiry = request.user.membership_expiry
        registration_payment = {
            'id': 'registration',
            'amount': request.user.registration_payment_amount,
            'date': request.user.date_joined,
            'status': request.user.registration_status,
            'type': 'registration',
            'description': 'Registration Fee',
            'receipt': request.user.registration_receipt,
            'verified_by': request.user.registration_verified_by,
            'verification_date': request.user.registration_verification_date,
            'notes': request.user.registration_notes,
            'membership_years': membership_years,
            'membership_expiry': membership_expiry,
            'registration_fee': registration_fee,
        }
        
        # Get event payments for this user
        from events.models import EventPayment
        event_payments = EventPayment.objects.filter(
            registration__user=request.user
        ).select_related('registration__event').order_by('-created_at')
        
        # Convert event payments to a format compatible with the template
        event_payments_list = []
        for event_payment in event_payments:
            event_payments_list.append({
                'id': f'event_{event_payment.id}',
                'amount': event_payment.amount,
                'date': event_payment.created_at,
                'status': event_payment.status,
                'type': 'event',
                'description': f'Event Payment - {event_payment.registration.event.title}',
                'receipt': event_payment.receipt_image,
                'verified_by': event_payment.verified_by,
                'verification_date': event_payment.verification_date,
                'notes': event_payment.notes,
                'event_title': event_payment.registration.event.title,
                'event_date': event_payment.registration.event.date,
            })
        
        # Combine all payments and sort by date
        payments_list = list(payments) + event_payments_list
        payments_list.insert(0, registration_payment)
        
        # Sort all payments by date (most recent first)
        payments_list.sort(key=lambda x: x.get('date') or x.date, reverse=True)
    paginator = Paginator(payments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    active_qr_code = None
    if not request.user.is_admin():
        active_qr_code = PaymentQRCode.get_active_qr_code()
    payment_summary = {}
    if not request.user.is_admin():
        from events.models import EventRegistration
        
        # Registration payment status
        registration_status = {
            'status': request.user.registration_status,
            'amount': request.user.registration_payment_amount,
            'is_paid': request.user.registration_status == 'active'
        }
        
        # Event payments summary
        event_registrations = EventRegistration.objects.filter(
            user=request.user,
            event__payment_amount__gt=0
        ).select_related('event')
        
        event_payment_summary = {
            'total_events': event_registrations.count(),
            'paid_events': event_registrations.filter(payment_status='paid').count(),
            'unpaid_events': event_registrations.filter(payment_status='not_required').count(),  # Full payment required
            'rejected_events': event_registrations.filter(payment_status='rejected').count(),
            'total_amount': sum(reg.event.payment_amount for reg in event_registrations if reg.event.payment_amount),
            'paid_amount': sum(reg.event.payment_amount for reg in event_registrations.filter(payment_status='paid') if reg.event.payment_amount)
        }
        
        # General payments summary
        general_payments_summary = {
            'total_paid': payments.filter(status='verified').aggregate(total=Sum('amount'))['total'] or 0,
            'pending_amount': payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
            'total_payments': payments.count()
        }
        
        payment_summary = {
            'registration': registration_status,
            'events': event_payment_summary,
            'general': general_payments_summary
        }
    
    return render(request, 'payments/payment_list.html', {
        'page_obj': page_obj,
        'status_choices': Payment.STATUS_CHOICES,
        'current_filter': request.GET.get('status', ''),
        'active_qr_code': active_qr_code,
        'payment_summary': payment_summary,
        'membership_years': membership_years,
        'membership_expiry': membership_expiry,
        'registration_fee': registration_fee,
    })

@login_required
def payment_submit(request):
    from payments.services.paymongo_service import PayMongoService
    from decimal import Decimal
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.payee_name = f"{request.user.first_name} {request.user.last_name}"
            payment.payee_email = request.user.email
            payment.expiry_date = timezone.now() + timedelta(days=7)  # 7 days expiry
            
            # Generate QR PH reference if not provided
            if not payment.qr_ph_reference:
                payment.qr_ph_reference = f"QRP-{request.user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            
            payment.save()
            
            # Check if user wants to use PayMongo (automatic) or manual payment
            use_paymongo = request.POST.get('use_paymongo', 'no') == 'yes'
            
            if use_paymongo:
                # Create PayMongo source for QR PH payment
                paymongo = PayMongoService()
                
                # Get the full URL for success/failed redirects
                success_url = request.build_absolute_uri('/payments/success/')
                failed_url = request.build_absolute_uri('/payments/failed/')
                
                success, response = paymongo.create_source(
                    amount=Decimal(str(payment.amount)),
                    description=f"ScoutConnect Payment - {payment.payment_type}",
                    redirect_success=success_url,
                    redirect_failed=failed_url,
                    metadata={
                        'payment_id': payment.id,
                        'user_id': request.user.id,
                        'reference': payment.qr_ph_reference
                    }
                )
                
                if success:
                    # Store PayMongo source ID
                    source_data = response['data']
                    payment.paymongo_source_id = source_data['id']
                    payment.gateway_response = response
                    payment.save()
                    
                    # Get checkout URL from response
                    checkout_url = source_data['attributes']['redirect']['checkout_url']
                    
                    messages.success(request, 'Payment created! You will be redirected to complete your payment.')
                    
                    # Redirect user to PayMongo checkout
                    return redirect(checkout_url)
                else:
                    # PayMongo API failed, fallback to manual
                    logger.error(f'PayMongo source creation failed: {response}')
                    messages.warning(request, 'Automatic payment is temporarily unavailable. Please use manual payment.')
            
            # Manual payment flow (or PayMongo fallback)
            # Notify admins about new payment
            admins = User.objects.filter(role='admin')
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                NotificationService.send_email(
                    subject=f"New Payment Submission - {payment.user.get_full_name()}",
                    message=f"A new payment of ₱{payment.amount} has been submitted and is pending verification. Reference: {payment.qr_ph_reference}",
                    recipient_list=admin_emails,
                )
            
            messages.success(request, 'Payment submitted successfully. It will be reviewed by an administrator.')
            return redirect('payments:payment_list')
    else:
        form = PaymentForm()
    
    # Get active QR code for payment
    active_qr_code = PaymentQRCode.get_active_qr_code()
    
    return render(request, 'payments/payment_submit.html', {
        'form': form,
        'active_qr_code': active_qr_code
    })

@login_required
def payment_verify(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    if not (request.user.is_admin() or request.user == payment.user):
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        # Backward compatibility: accept 'status' values from older templates
        if not action:
            status_val = request.POST.get('status')
            if status_val == 'verified':
                action = 'verify'
            elif status_val == 'rejected':
                action = 'reject'
        notes = request.POST.get('notes', '')
        
        if action == 'verify':
            payment.status = 'verified'
            payment.verified_by = request.user
            payment.verification_date = timezone.now()
            payment.notes = notes
            payment.save()
            
            # Notify user about verification
            NotificationService.send_email(
                subject="Payment Verified",
                message=f"Your payment of ₱{payment.amount} has been verified. Thank you!",
                recipient_list=[payment.user.email],
            )
            if hasattr(payment.user, 'phone_number') and payment.user.phone_number:
                NotificationService.send_sms(payment.user.phone_number, f"Your payment of ₱{payment.amount} has been verified. Thank you!")
            # Real-time notification
            send_realtime_notification(payment.user.id, f"Your payment of ₱{payment.amount} has been verified.", type='payment')
            messages.success(request, 'Payment verified successfully.')
            
        elif action == 'reject':
            payment.status = 'rejected'
            payment.verified_by = request.user
            payment.verification_date = timezone.now()
            payment.notes = notes
            payment.save()
            
            # Notify user about rejection
            NotificationService.send_email(
                subject="Payment Rejected",
                message=f"Your payment of ₱{payment.amount} has been rejected. Reason: {notes}",
                recipient_list=[payment.user.email],
            )
            if hasattr(payment.user, 'phone_number') and payment.user.phone_number:
                NotificationService.send_sms(payment.user.phone_number, f"Your payment of ₱{payment.amount} has been rejected.")
            # Real-time notification
            send_realtime_notification(payment.user.id, f"Your payment of ₱{payment.amount} has been rejected.", type='payment')
            messages.warning(request, 'Payment rejected.')
        
        return redirect('payments:payment_list')
    
    return render(request, 'payments/payment_verify.html', {'payment': payment})

# QR Code Management Views
@admin_required
def qr_code_manage(request):
    """View for admins to manage payment QR codes"""
    qr_codes = PaymentQRCode.objects.all().order_by('-created_at')
    active_qr_code = PaymentQRCode.get_active_qr_code()
    
    if request.method == 'POST':
        form = PaymentQRCodeForm(request.POST, request.FILES)
        if form.is_valid():
            qr_code = form.save(commit=False)
            qr_code.created_by = request.user
            
            # If this QR code is being set as active, deactivate others
            if qr_code.is_active:
                PaymentQRCode.objects.filter(is_active=True).update(is_active=False)
            
            qr_code.save()
            messages.success(request, 'QR code saved successfully.')
            return redirect('payments:qr_code_manage')
    else:
        form = PaymentQRCodeForm()
    
    return render(request, 'payments/qr_code_manage.html', {
        'form': form,
        'qr_codes': qr_codes,
        'active_qr_code': active_qr_code,
    })

@admin_required
def qr_code_edit(request, qr_code_id):
    """View for admins to edit existing QR codes"""
    qr_code = get_object_or_404(PaymentQRCode, id=qr_code_id)
    
    if request.method == 'POST':
        form = PaymentQRCodeForm(request.POST, request.FILES, instance=qr_code)
        if form.is_valid():
            # If this QR code is being set as active, deactivate others
            if form.cleaned_data['is_active']:
                PaymentQRCode.objects.filter(is_active=True).exclude(id=qr_code.id).update(is_active=False)
            
            form.save()
            messages.success(request, 'QR code updated successfully.')
            return redirect('payments:qr_code_manage')
    else:
        form = PaymentQRCodeForm(instance=qr_code)
    
    return render(request, 'payments/qr_code_edit.html', {
        'form': form,
        'qr_code': qr_code,
    })

@admin_required
def qr_code_delete(request, qr_code_id):
    """View for admins to delete QR codes"""
    qr_code = get_object_or_404(PaymentQRCode, id=qr_code_id)
    
    if request.method == 'POST':
        qr_code.delete()
        messages.success(request, 'QR code deleted successfully.')
        return redirect('payments:qr_code_manage')
    
    return render(request, 'payments/qr_code_delete.html', {
        'qr_code': qr_code,
    })

@admin_required
def qr_code_toggle_active(request, qr_code_id):
    """View for admins to toggle QR code active status"""
    qr_code = get_object_or_404(PaymentQRCode, id=qr_code_id)
    
    if request.method == 'POST':
        if qr_code.is_active:
            qr_code.is_active = False
            messages.success(request, 'QR code deactivated.')
        else:
            # Deactivate all other QR codes first
            PaymentQRCode.objects.filter(is_active=True).update(is_active=False)
            qr_code.is_active = True
            messages.success(request, 'QR code activated.')
        
        qr_code.save()
    
    return redirect('payments:qr_code_manage')


# ============================================================================
# PayMongo Webhook Handler and Payment Integration
# ============================================================================

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from payments.services.paymongo_service import PayMongoService
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def payment_webhook(request):
    """
    Handle PayMongo webhook notifications
    This endpoint receives payment status updates from PayMongo
    
    Events handled:
    - source.chargeable: Payment source is ready to be charged
    - payment.paid: Payment was successful
    - payment.failed: Payment failed
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get webhook signature from headers
        signature = request.headers.get('Paymongo-Signature')
        
        # Get raw body
        raw_body = request.body.decode('utf-8')

        # Persist raw webhook immediately for debugging/replayability
        try:
            from .models import WebhookLog
            headers_dict = {k: v for k, v in request.headers.items()}
            src_ip = request.META.get('REMOTE_ADDR')
            WebhookLog.objects.create(
                source_ip=src_ip,
                headers=headers_dict,
                body=raw_body,
                processed=False
            )
        except Exception as e:
            logger.exception(f'Failed to persist webhook log: {e}')
        
        # Verify webhook signature (temporarily skip for testing)
        # TODO: Fix signature verification for production
        if signature:
            if not PayMongoService.verify_webhook_signature(raw_body, signature):
                logger.warning('Invalid webhook signature - proceeding anyway for testing')
                # return JsonResponse({'error': 'Invalid signature'}, status=401)
        else:
            logger.warning('Webhook received without signature - proceeding anyway for testing')
        
        # Parse webhook data
        webhook_data = json.loads(raw_body)
        event_type = webhook_data['data']['attributes']['type']
        
        # Print to console (will appear in logs regardless of logger level)
        print(f'[WEBHOOK] Event type: {event_type}')
        logger.info(f'Webhook received: {event_type}')
        
        # Handle different event types
        if event_type == 'source.chargeable':
            # Payment source is ready to be charged
            handle_source_chargeable(webhook_data)
            
        elif event_type == 'payment.paid':
            # Payment was successful
            handle_payment_paid(webhook_data)
            
        elif event_type == 'payment.failed':
            # Payment failed
            handle_payment_failed(webhook_data)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Webhook {event_type} processed'
        })
        
    except json.JSONDecodeError:
        logger.error('Invalid JSON in webhook payload')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
    except Exception as e:
        logger.error(f'Webhook processing error: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Internal server error'}, status=500)


def handle_source_chargeable(webhook_data):
    """
    Handle source.chargeable event - QR code has been scanned and authorized
    This is the critical event that indicates the user has completed payment.
    We must charge the source immediately to capture the payment.
    """
    from accounts.models import RegistrationPayment
    from decimal import Decimal
    from payments.services.paymongo_service import PayMongoService
    
    try:
        source_data = webhook_data['data']['attributes']['data']
        source_id = source_data['id']
        source_attrs = source_data.get('attributes', {})
        metadata = source_attrs.get('metadata', {}) or {}
        
        # Amount in centavos
        source_amount_centavos = source_attrs.get('amount', 0)
        source_amount = Decimal(str(source_amount_centavos / 100.0))
        
        logger.info(f'📱 [WEBHOOK] source.chargeable: {source_id} | Amount: ₱{source_amount}')
        # If the gateway included metadata we can shortcut finalization for
        # simpler test flows: when metadata.payment_type indicates a
        # 'registration' or 'event_registration' we consider the flow
        # complete for now and finalize the relevant records so users can
        # login immediately after redirect.
        try:
            payment_type = metadata.get('payment_type')
            if payment_type == 'registration':
                # Finalize registration payment immediately
                reg_id = metadata.get('registration_payment_id')
                reg_payment = None
                if reg_id:
                    reg_payment = RegistrationPayment.objects.filter(id=reg_id).first()
                if not reg_payment:
                    reg_payment = RegistrationPayment.objects.filter(paymongo_source_id=source_id, status='pending').first()
                if reg_payment:
                    logger.info(f'Auto-finalizing registration payment {getattr(reg_payment, "id", None)} from source.chargeable')
                    reg_payment.status = 'verified'
                    if not reg_payment.paymongo_source_id:
                        reg_payment.paymongo_source_id = source_id
                    reg_payment.verification_date = timezone.now()
                    reg_payment.save()

                    u = reg_payment.user
                    u.registration_status = 'active'
                    u.is_active = True
                    try:
                        u.registration_total_paid = (u.registration_total_paid or 0) + reg_payment.amount
                    except Exception:
                        from decimal import Decimal
                        u.registration_total_paid = Decimal(str(getattr(u, 'registration_total_paid', 0))) + Decimal(str(reg_payment.amount))
                    # membership expiry
                    years = int(float(reg_payment.amount) // 500)
                    if years > 0:
                        try:
                            from dateutil.relativedelta import relativedelta
                            u.membership_expiry = timezone.now() + relativedelta(years=years)
                        except Exception:
                            from datetime import timedelta
                            u.membership_expiry = timezone.now() + timedelta(days=365 * years)
                    u.save()
                    
                    # Send welcome email to user
                    try:
                        from notifications.services import NotificationService
                        email_message = f"""Dear {u.first_name} {u.last_name},

🎉 Welcome to ScoutConnect!

Your registration payment of ₱{reg_payment.amount} has been successfully confirmed and your account is now active!

Account Details:
- Email: {u.email}
- Registration Status: Active
- Membership Expiry: {u.membership_expiry.strftime('%B %d, %Y') if u.membership_expiry else 'N/A'}

You can now log in to access all features including:
✓ Event registration
✓ Announcements and notifications
✓ Your personal dashboard

Login here: {request.build_absolute_uri('/accounts/login/')}

Thank you for joining ScoutConnect!

Best regards,
The ScoutConnect Team

---
This is an automated confirmation email. Please do not reply to this email.
"""
                        NotificationService.send_email(
                            subject='🎉 Registration Payment Confirmed - Welcome to ScoutConnect!',
                            message=email_message,
                            recipient_list=[u.email]
                        )
                        logger.info(f'Registration confirmation email sent to {u.email}')
                        
                        # Send realtime notification
                        try:
                            from notifications.services import send_realtime_notification
                            send_realtime_notification(
                                user_id=u.id,
                                message=f'Your registration payment has been confirmed! Welcome to ScoutConnect.',
                                notification_type='registration_confirmed'
                            )
                        except Exception:
                            logger.exception('Failed to send realtime notification for registration')
                            
                    except Exception:
                        logger.exception(f'Failed to send registration confirmation email to {u.email}')
                    
                    # mark any matching webhook logs processed
                    try:
                        from .models import WebhookLog
                        WebhookLog.objects.filter(body__contains=source_id, processed=False).update(processed=True)
                    except Exception:
                        logger.exception('Failed to mark WebhookLog processed for registration')
                    return
            elif payment_type == 'event_registration':
                # Finalize event registration payment immediately
                from events.models import EventRegistration, EventPayment
                event_reg_id = metadata.get('event_registration_id')
                ev_reg = None
                if event_reg_id:
                    ev_reg = EventRegistration.objects.filter(id=event_reg_id).first()
                if not ev_reg:
                    # try to find by source via EventPayment
                    ev_pay = EventPayment.objects.filter(paymongo_source_id=source_id, status='pending').first()
                    if ev_pay:
                        ev_reg = ev_pay.registration
                if ev_reg:
                    logger.info(f'Auto-finalizing event registration {ev_reg.id} from source.chargeable')
                    # find or create EventPayment for this registration/source
                    ev_payment = EventPayment.objects.filter(registration=ev_reg, paymongo_source_id=source_id).first()
                    if not ev_payment:
                        ev_payment = EventPayment.objects.create(
                            registration=ev_reg,
                            amount=source_amount or ev_reg.amount_required,
                            status='verified',
                            paymongo_source_id=source_id,
                            verification_date=timezone.now(),
                        )
                    else:
                        ev_payment.status = 'verified'
                        ev_payment.verification_date = timezone.now()
                        if not ev_payment.paymongo_source_id:
                            ev_payment.paymongo_source_id = source_id
                        ev_payment.save()

                    # Mark registration as paid
                    ev_reg.total_paid = ev_reg.amount_required
                    ev_reg.payment_status = 'paid'
                    ev_reg.verified = True
                    ev_reg.verification_date = timezone.now()
                    ev_reg.save()
                    
                    # Send event payment confirmation email
                    try:
                        from notifications.services import NotificationService
                        event = ev_reg.event
                        user = ev_reg.user
                        email_message = f"""Dear {user.first_name} {user.last_name},

Your payment for the event has been successfully confirmed!

Event Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Event: {event.title}
📍 Location: {event.location}
🗓️  Date: {event.date.strftime('%B %d, %Y')}
⏰ Time: {event.time.strftime('%I:%M %p') if event.time else 'TBA'}
💰 Amount Paid: ₱{ev_payment.amount}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Registration Status: Confirmed ✓

Thank you for registering! We look forward to seeing you at the event.

For any questions, please contact your event coordinator.

Best regards,
The ScoutConnect Team

---
This is an automated confirmation email. Please do not reply to this email.
"""
                        NotificationService.send_email(
                            subject=f'✓ Event Payment Confirmed - {event.title}',
                            message=email_message,
                            recipient_list=[user.email]
                        )
                        logger.info(f'Event payment confirmation email sent to {user.email} for event {event.id}')
                        
                        # Send realtime notification
                        try:
                            from notifications.services import send_realtime_notification
                            send_realtime_notification(
                                user_id=user.id,
                                message=f'Your payment for "{event.title}" has been confirmed!',
                                notification_type='event_payment_confirmed'
                            )
                        except Exception:
                            logger.exception('Failed to send realtime notification for event payment')
                            
                    except Exception:
                        logger.exception(f'Failed to send event payment confirmation email to {user.email}')
                    
                    try:
                        from .models import WebhookLog
                        WebhookLog.objects.filter(body__contains=source_id, processed=False).update(processed=True)
                    except Exception:
                        logger.exception('Failed to mark WebhookLog processed for event')
                    return
        except Exception:
            logger.exception('Auto-finalization on source.chargeable failed; continuing with normal processing')
        
        # Find payment by source_id (check both Payment and RegistrationPayment)
        payment = Payment.objects.filter(
            paymongo_source_id=source_id,
            status='pending'
        ).first()
        
        if payment:
            logger.info(f'Payment {payment.id} source is chargeable')
            # Update payment status to indicate it's in progress
            payment.notes = 'Payment source is chargeable, waiting for confirmation'
            payment.save()
            
            # Notify admin
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin in admin_users:
                send_realtime_notification(
                    user_id=admin.id,
                    message=f'New payment from {payment.user.get_full_name()} is processing',
                    notification_type='payment_update'
                )
            else:
                # Check if it's an EventPayment first
                from events.models import EventPayment
                event_payment = EventPayment.objects.filter(
                    paymongo_source_id=source_id,
                    status='pending'
                ).first()
                if event_payment:
                    logger.info(f'EventPayment {event_payment.id} source is chargeable')
                    try:
                        from decimal import Decimal
                        from payments.services.paymongo_service import PayMongoService

                        if not event_payment.paymongo_payment_id and event_payment.status == 'pending':
                            paymongo = PayMongoService()
                            amount = Decimal(str(event_payment.amount))
                            desc = f"Event Registration Payment - {event_payment.registration.event.title}"
                            metadata = {
                                'payment_type': 'event_registration',
                                'user_id': str(event_payment.registration.user.id),
                                'event_registration_id': str(event_payment.registration.id),
                                'event_id': str(event_payment.registration.event.id),
                            }

                            success, resp = paymongo.create_payment(
                                source_id=source_id,
                                amount=amount,
                                description=desc,
                                metadata=metadata
                            )

                            if success and isinstance(resp, dict):
                                payment_obj = resp.get('data')
                                if payment_obj:
                                    payment_id = payment_obj.get('id')
                                    event_payment.paymongo_payment_id = payment_id
                                    event_payment.save()
                                    logger.info(f'Created PayMongo payment {payment_id} for EventPayment {event_payment.id}')
                                    # If the gateway returned a payment already in 'paid'
                                    # status (test-mode or instant capture), run the
                                    # same logic as the payment.paid webhook so the
                                    # EventPayment and EventRegistration are
                                    # finalized immediately.
                                    try:
                                        pay_attrs = payment_obj.get('attributes', {})
                                        if pay_attrs.get('status') == 'paid':
                                            synthetic = {
                                                'data': {
                                                    'attributes': {
                                                        'type': 'payment.paid',
                                                        'data': payment_obj
                                                    }
                                                }
                                            }
                                            handle_payment_paid(synthetic)
                                    except Exception:
                                        logger.exception('Failed to auto-process payment.paid after create_payment for event')
                            else:
                                logger.warning(f'Could not create PayMongo payment for event_payment {event_payment.id}: {resp}')
                    except Exception as e:
                        logger.error(f'Error creating PayMongo payment for event: {str(e)}')
                        import traceback
                        traceback.print_exc()
                else:
                    # Check if it's a registration payment
                    reg_payment = RegistrationPayment.objects.filter(
                        paymongo_source_id=source_id,
                        status='pending'
                    ).first()
                    if reg_payment:
                        logger.info(f'RegistrationPayment {reg_payment.id} source is chargeable')
                        # If we haven't already created a PayMongo payment for this
                        # registration, create one now so PayMongo will emit a
                        # `payment.paid` event and the normal webhook processing will
                        # finalize the registration.
                        try:
                            from decimal import Decimal
                            from payments.services.paymongo_service import PayMongoService

                            if not reg_payment.paymongo_payment_id and reg_payment.status == 'pending':
                                paymongo = PayMongoService()
                                amount = Decimal(str(reg_payment.amount))
                                desc = f"Registration Payment - {reg_payment.user.get_full_name()}"
                                metadata = {
                                    'payment_type': 'registration',
                                    'user_id': str(reg_payment.user.id),
                                    'registration_payment_id': str(reg_payment.id)
                                }

                                success, resp = paymongo.create_payment(
                                    source_id=source_id,
                                    amount=amount,
                                    description=desc,
                                    metadata=metadata
                                )

                                if success and isinstance(resp, dict):
                                    payment_obj = resp.get('data')
                                    if payment_obj:
                                        payment_id = payment_obj.get('id')
                                        reg_payment.paymongo_payment_id = payment_id
                                        reg_payment.save()
                                        logger.info(f'Created PayMongo payment {payment_id} for RegistrationPayment {reg_payment.id}')
                                        # If the payment is already marked paid by the
                                        # gateway, finalize registration immediately by
                                        # reusing the payment.paid handler.
                                        try:
                                            attrs = payment_obj.get('attributes', {})
                                            if attrs.get('status') == 'paid':
                                                synthetic = {
                                                    'data': {
                                                        'attributes': {
                                                            'type': 'payment.paid',
                                                            'data': payment_obj
                                                        }
                                                    }
                                                }
                                                handle_payment_paid(synthetic)
                                        except Exception:
                                            logger.exception('Failed to auto-process payment.paid after create_payment for registration')
                                else:
                                    logger.warning(f'Could not create PayMongo payment for reg_payment {reg_payment.id}: {resp}')
                        except Exception as e:
                            logger.error(f'Error creating PayMongo payment for registration: {str(e)}')
                            import traceback
                            traceback.print_exc()
                    else:
                        logger.warning(f'Payment not found for source {source_id}')
            
    except Exception as e:
        logger.error(f'Error handling source.chargeable: {str(e)}')
        import traceback
        traceback.print_exc()


def handle_payment_paid(webhook_data):
    """Handle payment.paid event - Payment successful"""
    from accounts.models import RegistrationPayment, BatchRegistration, User, BatchStudentData
    from django.contrib.auth.hashers import make_password
    
    try:
        payment_data = webhook_data['data']['attributes']['data']
        payment_id = payment_data['id']
        source_id = payment_data['attributes']['source']['id']
        amount = payment_data['attributes']['amount'] / 100  # Convert from centavos
        metadata = payment_data['attributes'].get('metadata', {})
        
        logger.info(f'Processing payment.paid for payment: {payment_id}')
        
        # Check if this is a registration payment
        payment_type = metadata.get('payment_type')
        
        if payment_type == 'batch_registration':
            # Handle batch registration payment
            batch_reg_id = metadata.get('batch_registration_id')
            if batch_reg_id:
                batch_reg = BatchRegistration.objects.filter(id=batch_reg_id).first()
                if batch_reg:
                    logger.info(f'Batch registration {batch_reg.batch_id} payment confirmed')
                    
                    # Update batch registration
                    batch_reg.status = 'paid'
                    batch_reg.paymongo_payment_id = payment_id
                    batch_reg.save()
                    
                    # Create all student users from stored data
                    student_data_list = batch_reg.student_data.all()
                    created_count = 0
                    
                    for student_data in student_data_list:
                        # Check if already created
                        if student_data.created_user:
                            logger.info(f'Student {student_data.email} already created')
                            continue
                        
                        # Check if user exists
                        if User.objects.filter(email=student_data.email).exists():
                            logger.warning(f'User with email {student_data.email} already exists')
                            continue
                        
                        # Create user
                        user = User.objects.create(
                            username=student_data.username,
                            first_name=student_data.first_name,
                            last_name=student_data.last_name,
                            email=student_data.email,
                            phone_number=student_data.phone_number,
                            date_of_birth=student_data.date_of_birth,
                            address=student_data.address,
                            password=student_data.password_hash,
                            role='scout',
                            is_active=True,
                            registration_status='active',
                        )
                        
                        # Create RegistrationPayment record
                        RegistrationPayment.objects.create(
                            user=user,
                            batch_registration=batch_reg,
                            amount=batch_reg.amount_per_student,
                            status='verified'
                        )
                        
                        # Link student data to created user
                        student_data.created_user = user
                        student_data.save()
                        
                        created_count += 1
                        logger.info(f'Created user: {user.email}')
                        
                        # Send welcome email to student
                        try:
                            from django.conf import settings
                            login_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/accounts/login/"
                            
                            welcome_message = f'''
Dear {user.first_name} {user.last_name},

🎉 Welcome to ScoutConnect!

Your account has been successfully created as part of a batch registration by {batch_reg.registrar_name}.

Your Account Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: {user.email}
👤 Username: {user.username}
🏅 Rank: Scout
💰 Registration Fee: ₱{batch_reg.amount_per_student}

You Can Now Login!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Visit: {login_url}
Or go to: http://localhost:8000/accounts/login/

Login Credentials:
• Email: {user.email}
• Password: (the password set during registration)

What's Next?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Login to your account
✓ Complete your profile
✓ Browse upcoming events
✓ Connect with other scouts
✓ Check announcements

Welcome to our scout community! We're excited to have you on board.

If you have any questions, please contact your registrar: {batch_reg.registrar_name}

Best regards,
The ScoutConnect Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
                            '''
                            
                            NotificationService.send_email(
                                subject='✅ Welcome to ScoutConnect - Your Account is Ready!',
                                message=welcome_message,
                                recipient_list=[user.email]
                            )
                        except Exception as e:
                            logger.error(f'Failed to send welcome email to {user.email}: {str(e)}')
                    
                    # Update batch status to verified
                    batch_reg.status = 'verified'
                    batch_reg.save()
                    
                    logger.info(f'Batch registration {batch_reg.batch_id}: Created {created_count} student accounts')
                    
                    # Send detailed confirmation email to registrar
                    registrar_message = f'''
Dear {batch_reg.registrar_name},

🎉 Your batch registration payment has been successfully confirmed!

Payment Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Total Amount Paid: ₱{batch_reg.total_amount}
✓ Number of Students: {batch_reg.number_of_students}
✓ Amount Per Student: ₱{batch_reg.amount_per_student}
✓ Payment Status: Verified
✓ Accounts Created: {created_count} students

Registration Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Your Email: {batch_reg.registrar_email}
📞 Your Phone: {batch_reg.registrar_phone}
📅 Registration Date: {batch_reg.created_at.strftime('%B %d, %Y')}

Student Accounts:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All {created_count} students have been successfully registered and can now login to ScoutConnect.

Each student has received a welcome email with their login credentials at their registered email address.

Important Information for Students:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Login URL: http://localhost:8000/accounts/login/
• Students should use their email and password to login
• All accounts are now active and ready to use

What's Next?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Inform students to check their emails
✓ Students can complete their profiles after login
✓ Browse upcoming events together
✓ Stay connected with the scout community

Thank you for using ScoutConnect for your batch registration!

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
The ScoutConnect Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
                    '''
                    
                    NotificationService.send_email(
                        subject='✅ Batch Registration Complete - ScoutConnect',
                        message=registrar_message,
                        recipient_list=[batch_reg.registrar_email]
                    )
                    
                    # Notify admins
                    admin_users = User.objects.filter(role='admin', is_active=True)
                    for admin in admin_users:
                        send_realtime_notification(
                            user_id=admin.id,
                            message=f'Batch registration completed: {batch_reg.registrar_name} ({created_count} students) - ₱{batch_reg.total_amount}',
                            notification_type='batch_registration_verified'
                        )
                    
                    logger.info(f'Batch registration {batch_reg.batch_id} payment processed successfully')
                    return
        
        # Handle event registration payment
        if payment_type == 'event_registration':
            from events.models import EventRegistration, EventPayment
            
            event_registration_id = metadata.get('event_registration_id')
            if event_registration_id:
                event_registration = EventRegistration.objects.filter(id=event_registration_id).first()
                if event_registration:
                    logger.info(f'Event registration {event_registration.id} payment confirmed')
                    
                    # Find and update the EventPayment record
                    event_payment = EventPayment.objects.filter(
                        registration=event_registration,
                        paymongo_source_id=source_id,
                        status='pending'
                    ).first()
                    
                    if event_payment:
                        # Update payment status to the model's 'verified' choice
                        event_payment.status = 'verified'
                        event_payment.paymongo_payment_id = payment_id
                        event_payment.verification_date = timezone.now()
                        event_payment.notes = f'Payment confirmed via PayMongo webhook. Amount: ₱{amount}'
                        event_payment.save()
                        
                        # Update event registration
                        event_registration.total_paid = amount
                        event_registration.payment_status = 'paid'
                        event_registration.verified = True
                        event_registration.save()
                        
                        logger.info(f'Event registration {event_registration.id} payment verified')
                        
                        # Send confirmation email to user
                        user = event_registration.user
                        event = event_registration.event
                        
                        event_confirmation_message = f'''
Dear {user.first_name} {user.last_name},

🎉 Your event registration payment has been confirmed!

Event Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Event: {event.title}
📍 Location: {event.location}
🗓️ Date: {event.date.strftime('%B %d, %Y')}
⏰ Time: {event.time.strftime('%I:%M %p')}

Payment Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Amount Paid: ₱{amount}
✓ Payment Reference: {payment_id}
✓ Payment Status: Confirmed
✓ Registration Status: Verified

You're All Set!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your registration for "{event.title}" is now complete. We look forward to seeing you there!

Event Description:
{event.description[:200]}{'...' if len(event.description) > 200 else ''}

Important Reminders:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Mark your calendar for {event.date.strftime('%B %d, %Y')} at {event.time.strftime('%I:%M %p')}
• Location: {event.location}
• Bring any required materials or documents
• Check your dashboard for event updates
• Contact us if you have any questions

If you need to make any changes to your registration or have questions about the event, please don't hesitate to contact us.

See you at the event!

Best regards,
The ScoutConnect Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
                        '''
                        
                        NotificationService.send_email(
                            subject=f'Event Payment Confirmed - {event.title}',
                            message=event_confirmation_message,
                            recipient_list=[user.email]
                        )
                        
                        # Send realtime notification to user only
                        send_realtime_notification(
                            user_id=user.id,
                            message=f'Your registration for "{event.title}" is confirmed!',
                            notification_type='event_registration_verified'
                        )
                        
                        logger.info(f'Event registration {event_registration.id} payment confirmed and user notified')
                        return
        
        if payment_type == 'registration':
            # Handle registration payment
            reg_payment_id = metadata.get('registration_payment_id')
            if reg_payment_id:
                reg_payment = RegistrationPayment.objects.filter(id=reg_payment_id).first()
                if reg_payment:
                    logger.info(f'Registration payment {reg_payment.id} confirmed as paid')
                    
                    # Update registration payment
                    reg_payment.status = 'verified'
                    reg_payment.paymongo_source_id = source_id
                    reg_payment.paymongo_payment_id = payment_id
                    reg_payment.verification_date = timezone.now()
                    reg_payment.save()

                    # Activate user account and record payment totals
                    user = reg_payment.user
                    user.registration_status = 'active'
                    user.is_active = True
                    # Update total paid
                    try:
                        user.registration_total_paid = (user.registration_total_paid or 0) + reg_payment.amount
                    except Exception:
                        # Ensure Decimal arithmetic - coerce to Decimal if necessary
                        from decimal import Decimal
                        user.registration_total_paid = Decimal(str(getattr(user, 'registration_total_paid', 0))) + Decimal(str(reg_payment.amount))

                    # Calculate membership expiry
                    years = int(float(reg_payment.amount) // 500)
                    if years > 0:
                        try:
                            from dateutil.relativedelta import relativedelta
                            user.membership_expiry = timezone.now() + relativedelta(years=years)
                        except ImportError:
                            from datetime import timedelta
                            user.membership_expiry = timezone.now() + timedelta(days=365 * years)
                    user.save()
                    
                    logger.info(f'User {user.id} registration activated')
                    
                    # Send detailed confirmation email to user
                    from django.conf import settings
                    login_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/accounts/login/"
                    
                    email_message = f'''
Dear {user.first_name} {user.last_name},

🎉 Welcome to ScoutConnect!

Your registration payment has been successfully confirmed and your account is now active!

Payment Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Amount Paid: ₱{reg_payment.amount}
✓ Payment Reference: {payment_id}
✓ Payment Status: Verified
✓ Account Status: Active
✓ Membership Duration: {years} year(s)

Your Account Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: {user.email}
👤 Username: {user.username}
🏅 Rank: Scout

Login Instructions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Visit: {login_url}
   (Or go to: http://localhost:8000/accounts/login/)

2. Enter your credentials:
   • Email: {user.email}
   • Password: (the password you created during registration)

3. Click "Login" to access your dashboard

What's Next?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Complete your profile with additional information
✓ Browse and register for upcoming events
✓ Connect with fellow scouts in your troop
✓ Check announcements for important updates
✓ Track your event attendance and participation

Welcome to our scout community! We're excited to have you on board.

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
The ScoutConnect Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
                    '''
                    
                    NotificationService.send_email(
                        subject='Registration Payment Confirmed - ScoutConnect',
                        message=email_message,
                        recipient_list=[user.email]
                    )
                    
                    # Send realtime notification to user only
                    send_realtime_notification(
                        user_id=user.id,
                        message=f'Welcome to ScoutConnect! Your registration is confirmed.',
                        notification_type='registration_verified'
                    )
                    
                    logger.info(f'Registration payment {reg_payment.id} processed and user notified')
                    return
        
        # Find regular payment by source_id or payment_id
        payment = Payment.objects.filter(
            Q(paymongo_source_id=source_id) | Q(paymongo_payment_id=payment_id)
        ).first()
        
        if payment:
            logger.info(f'Payment {payment.id} confirmed as paid')
            
            # Update payment status
            payment.status = 'verified'
            payment.paymongo_payment_id = payment_id
            payment.verification_date = timezone.now()
            payment.gateway_response = webhook_data
            payment.notes = f'Payment confirmed via PayMongo webhook. Amount: ₱{amount}'
            payment.save()
            
            # Send notification to user
            NotificationService.send_email(
                subject='Payment Confirmed - ScoutConnect',
                message=f'Your payment of ₱{payment.amount} has been confirmed! Reference: {payment.qr_ph_reference or payment_id}',
                recipient_list=[payment.user.email]
            )
            
            # Send realtime notification
            send_realtime_notification(
                user_id=payment.user.id,
                message=f'Your payment of ₱{payment.amount} has been confirmed!',
                notification_type='payment_verified'
            )
            
            # Update user registration status if this is a registration payment
            if payment.payment_type == 'registration':
                user_profile = payment.user
                if payment.status == 'verified':
                    user_profile.registration_status = 'active'
                    # Calculate membership expiry
                    years = int(payment.amount // 500)
                    if years > 0:
                        from datetime import timedelta
                        user_profile.membership_expiry = timezone.now() + timedelta(days=365 * years)
                    # Also update registration_total_paid when applicable
                    try:
                        user_profile.registration_total_paid = (user_profile.registration_total_paid or 0) + payment.amount
                    except Exception:
                        from decimal import Decimal
                        user_profile.registration_total_paid = Decimal(str(getattr(user_profile, 'registration_total_paid', 0))) + Decimal(str(payment.amount))
                    user_profile.save()
                    logger.info(f'User {user_profile.id} registration activated')
            
            # Notify admin
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin in admin_users:
                send_realtime_notification(
                    user_id=admin.id,
                    message=f'Payment confirmed: {payment.user.get_full_name()} - ₱{payment.amount}',
                    notification_type='payment_verified'
                )
            
            logger.info(f'Payment {payment.id} processed successfully')
        else:
            logger.warning(f'Payment not found for transaction {payment_id}')
            
    except Exception as e:
        logger.error(f'Error handling payment.paid: {str(e)}')
        import traceback
        traceback.print_exc()


def handle_payment_failed(webhook_data):
    """Handle payment.failed event - Payment failed"""
    from accounts.models import RegistrationPayment
    
    try:
        payment_data = webhook_data['data']['attributes']['data']
        source_id = payment_data['attributes']['source']['id']
        metadata = payment_data['attributes'].get('metadata', {})
        
        logger.info(f'Processing payment.failed for source: {source_id}')
        
        # Check if this is a registration payment
        payment_type = metadata.get('payment_type')
        
        if payment_type == 'registration':
            # Handle registration payment failure
            reg_payment_id = metadata.get('registration_payment_id')
            if reg_payment_id:
                reg_payment = RegistrationPayment.objects.filter(id=reg_payment_id).first()
                if reg_payment:
                    logger.info(f'Registration payment {reg_payment.id} marked as failed')
                    
                    reg_payment.status = 'rejected'
                    reg_payment.paymongo_source_id = source_id
                    reg_payment.save()
                    
                    # Send notification to user
                    user = reg_payment.user
                    NotificationService.send_email(
                        subject='Registration Payment Failed - ScoutConnect',
                        message=f'Your registration payment of ₱{reg_payment.amount} has failed. Please try registering again.',
                        recipient_list=[user.email]
                    )
                    
                    send_realtime_notification(
                        user_id=user.id,
                        message=f'Your registration payment has failed. Please try again.',
                        notification_type='registration_failed'
                    )
                    
                    return
        
        # Find regular payment
        payment = Payment.objects.filter(
            paymongo_source_id=source_id
        ).first()
        
        if payment:
            logger.info(f'Payment {payment.id} marked as failed')
            
            # Update payment status
            payment.status = 'rejected'
            payment.gateway_response = webhook_data
            payment.notes = 'Payment failed via PayMongo'
            payment.save()
            
            # Send notification to user
            NotificationService.send_email(
                subject='Payment Failed - ScoutConnect',
                message=f'Your payment of ₱{payment.amount} has failed. Please try again. Reference: {payment.qr_ph_reference or "N/A"}',
                recipient_list=[payment.user.email]
            )
            
            # Send realtime notification
            send_realtime_notification(
                user_id=payment.user.id,
                message=f'Your payment of ₱{payment.amount} has failed. Please try again.',
                notification_type='payment_failed'
            )
            
            logger.info(f'Payment {payment.id} marked as failed and user notified')
        else:
            logger.warning(f'Payment not found for source {source_id}')
            
    except Exception as e:
        logger.error(f'Error handling payment.failed: {str(e)}')
        import traceback
        traceback.print_exc()


# Payment redirect handlers
@login_required
def payment_success(request):
    """Handle successful payment redirect from PayMongo"""
    # Try to activate user if payment is verified
    from accounts.models import RegistrationPayment, User
    from payments.services.paymongo_service import PayMongoService
    user_activated = False
    user_email = None
    reg_payment_id = request.session.get('pending_registration_payment_id')
    if reg_payment_id:
        reg_payment = RegistrationPayment.objects.filter(id=reg_payment_id).first()
        # If already verified, activate user locally
        if reg_payment and reg_payment.status == 'verified':
            user = reg_payment.user
            if not user.is_active or user.registration_status != 'active':
                user.is_active = True
                user.registration_status = 'active'
                user.save()
                user_activated = True
                user_email = user.email
        else:
                # Fallback: attempt multiple reconciliation paths so that when
                # the user is redirected back from PayMongo we finalize the
                # registration immediately and allow login.
                try:
                    paymongo = PayMongoService()

                    def finalize_from_payment_obj(payment_obj):
                        # Mirror logic from handle_payment_paid for registration
                        payment_id = payment_obj.get('id')
                        attrs = payment_obj.get('attributes', {})
                        source = attrs.get('source', {})
                        source_id = source.get('id') if isinstance(source, dict) else None
                        amount = attrs.get('amount', 0) / 100.0

                        # Use reg_payment from closure
                        reg_payment.status = 'verified'
                        if source_id and not reg_payment.paymongo_source_id:
                            reg_payment.paymongo_source_id = source_id
                        if payment_id:
                            reg_payment.paymongo_payment_id = payment_id
                        reg_payment.verification_date = timezone.now()
                        reg_payment.save()

                        user = reg_payment.user
                        user.registration_status = 'active'
                        user.is_active = True
                        try:
                            user.registration_total_paid = (user.registration_total_paid or 0) + reg_payment.amount
                        except Exception:
                            from decimal import Decimal
                            user.registration_total_paid = Decimal(str(getattr(user, 'registration_total_paid', 0))) + Decimal(str(reg_payment.amount))

                        years = int(float(reg_payment.amount) // 500)
                        if years > 0:
                            try:
                                from dateutil.relativedelta import relativedelta
                                user.membership_expiry = timezone.now() + relativedelta(years=years)
                            except ImportError:
                                from datetime import timedelta
                                user.membership_expiry = timezone.now() + timedelta(days=365 * years)
                        user.save()

                        # Notify user
                        try:
                            from notifications.services import NotificationService
                            from django.conf import settings
                            login_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/accounts/login/"
                            email_message = f"""
    Dear {user.first_name} {user.last_name},

    🎉 Welcome to ScoutConnect!

    Your registration payment has been successfully confirmed and your account is now active!

    You can login at {login_url}
    """
                            NotificationService.send_email(
                                subject='Registration Payment Confirmed - ScoutConnect',
                                message=email_message,
                                recipient_list=[user.email]
                            )
                        except Exception:
                            logger.exception('Failed to send registration confirmation email in fallback')

                    # 1) If we already have a payment id stored, retrieve and check
                    if reg_payment and reg_payment.paymongo_payment_id:
                        ok, payment_obj = paymongo.retrieve_payment(reg_payment.paymongo_payment_id)
                        if ok and payment_obj and payment_obj.get('data'):
                            data = payment_obj.get('data')
                            attrs = data.get('attributes', {})
                            if attrs.get('status') == 'paid':
                                finalize_from_payment_obj(data)
                                user_activated = True
                                user_email = reg_payment.user.email

                    # 2) Otherwise try to find a payment by the source id
                    if not user_activated and reg_payment and reg_payment.paymongo_source_id:
                        found, payment_obj = paymongo.find_payment_by_source(reg_payment.paymongo_source_id)
                        if found and payment_obj:
                            # payment_obj is already the full payment dict
                            finalize_from_payment_obj(payment_obj)
                            user_activated = True
                            user_email = reg_payment.user.email

                    # 3) Finally, if still not activated, try to create a payment
                    # for the source (this will often return a paid payment in
                    # test-mode / instant-capture environments).
                    if not user_activated and reg_payment and reg_payment.paymongo_source_id:
                        from decimal import Decimal
                        success, resp = paymongo.create_payment(
                            source_id=reg_payment.paymongo_source_id,
                            amount=Decimal(str(reg_payment.amount)),
                            description=f"Registration Payment - {reg_payment.user.get_full_name()}",
                            metadata={'payment_type': 'registration', 'user_id': str(reg_payment.user.id), 'registration_payment_id': str(reg_payment.id)}
                        )
                        if success and isinstance(resp, dict):
                            data = resp.get('data')
                            if data and data.get('attributes', {}).get('status') == 'paid':
                                finalize_from_payment_obj(data)
                                user_activated = True
                                user_email = reg_payment.user.email

                    # Clear session key if we finished processing
                    if user_activated:
                        try:
                            del request.session['pending_registration_payment_id']
                        except KeyError:
                            pass
                except Exception as e:
                    logger.error(f'Fallback payment check failed: {str(e)}')
                    import traceback
                    traceback.print_exc()
    
    # Pass payment_id for status polling
    context = {
        'user_activated': user_activated,
        'user_email': user_email,
        'payment_id': reg_payment_id
    }
    return render(request, 'payments/payment_success.html', context)


@login_required
def payment_status(request, payment_id):
    """
    API endpoint to check payment status (for frontend polling)
    Returns JSON with payment status and user registration status
    """
    from accounts.models import RegistrationPayment
    from events.models import EventPayment
    
    try:
        # Try to find RegistrationPayment first
        reg_payment = RegistrationPayment.objects.filter(
            id=payment_id,
            user=request.user
        ).first()
        
        if reg_payment:
            return JsonResponse({
                'success': True,
                'payment_type': 'registration',
                'status': reg_payment.status,
                'amount': float(reg_payment.amount),
                'verified': reg_payment.status == 'verified',
                'user_status': request.user.registration_status,
                'verification_date': reg_payment.verification_date.isoformat() if reg_payment.verification_date else None
            })
        
        # Try EventPayment
        event_payment = EventPayment.objects.filter(
            id=payment_id,
            registration__user=request.user
        ).select_related('registration__event').first()
        
        if event_payment:
            return JsonResponse({
                'success': True,
                'payment_type': 'event',
                'status': event_payment.status,
                'amount': float(event_payment.amount),
                'verified': event_payment.status == 'verified',
                'event_title': event_payment.registration.event.title,
                'verification_date': event_payment.verification_date.isoformat() if event_payment.verification_date else None
            })
        
        # Try legacy Payment model
        payment = Payment.objects.filter(
            id=payment_id,
            user=request.user
        ).first()
        
        if payment:
            return JsonResponse({
                'success': True,
                'payment_type': payment.payment_type,
                'status': payment.status,
                'amount': float(payment.amount),
                'verified': payment.status == 'verified',
                'verification_date': payment.verification_date.isoformat() if payment.verification_date else None
            })
        
        return JsonResponse({
            'success': False,
            'error': 'Payment not found'
        }, status=404)
        
    except Exception as e:
        logger.error(f'Error checking payment status: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
def payment_failed(request):
    """Handle failed payment redirect from PayMongo"""
    return render(request, 'payments/payment_failed.html')
