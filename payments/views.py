from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from .models import Payment
from .forms import PaymentForm
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
    else:
        # Regular users see only their payments
        payments = Payment.objects.filter(user=request.user).order_by('-date')
    
    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'payments/payment_list.html', {
        'page_obj': page_obj,
        'status_choices': Payment.STATUS_CHOICES,
        'current_filter': request.GET.get('status', ''),
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
                NotificationService.send_sms(payment.user.phone_number, f"Your payment of ₱{payment.amount} has been rejected. Reason: {notes}")
            # Real-time notification
            send_realtime_notification(payment.user.id, f"Your payment of ₱{payment.amount} has been rejected. Reason: {notes}", type='payment')
            messages.warning(request, 'Payment rejected.')
        
        return redirect('payments:payment_list')
    
    return render(request, 'payments/payment_verify.html', {'payment': payment})
