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
    if request.user.is_admin():
        # Admin sees all payments
        payments = Payment.objects.all().order_by('-date')
        # Filter options
        status_filter = request.GET.get('status', '')
        if status_filter:
            payments = payments.filter(status=status_filter)
        payments_list = list(payments)
    else:
        # Regular users see only their payments
        payments = Payment.objects.filter(user=request.user).order_by('-date')
        
        # Always include registration payment information for users
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
        }
        
        # Add to payments list
        payments_list = list(payments)
        payments_list.insert(0, registration_payment)
    
    paginator = Paginator(payments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get active QR code for scouts
    active_qr_code = None
    if not request.user.is_admin():
        active_qr_code = PaymentQRCode.get_active_qr_code()
    
    return render(request, 'payments/payment_list.html', {
        'page_obj': page_obj,
        'status_choices': Payment.STATUS_CHOICES,
        'current_filter': request.GET.get('status', ''),
        'active_qr_code': active_qr_code,
    })

@login_required
def payment_submit(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.payee_name = f"{request.user.first_name} {request.user.last_name}"
            payment.payee_email = request.user.email
            payment.expiry_date = timezone.now() + timedelta(days=7)  # 7 days expiry
            payment.save()
            
            # Notify admins about new payment
            admins = User.objects.filter(rank='admin')
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                NotificationService.send_email(
                    subject=f"New Payment Submission - {payment.user.get_full_name()}",
                    message=f"A new payment of ₱{payment.amount} has been submitted and is pending verification.",
                    recipient_list=admin_emails,
                )
            
            messages.success(request, 'Payment submitted successfully. It will be reviewed by an administrator.')
            return redirect('payments:payment_list')
    else:
        form = PaymentForm()
    
    return render(request, 'payments/payment_submit.html', {'form': form})

@login_required
def payment_verify(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    if not (request.user.is_admin() or request.user == payment.user):
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        action = request.POST.get('action')
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
