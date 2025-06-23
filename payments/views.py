from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PaymentForm
from .models import Payment
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from boyscout_system.utils import render_to_pdf

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
def payment_list(request):
    if request.user.is_admin():
        payments = Payment.objects.all()
    else:
        payments = request.user.payments.all()
    return render(request, 'payments/payment_list.html', {'payments': payments})

@login_required
def payment_submit(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            # Check if user has any pending payments
            pending_payments = Payment.objects.filter(
                user=request.user,
                status='pending',
                date__gte=timezone.now() - timedelta(days=7)
            )
            if pending_payments.exists():
                messages.warning(request, 'You already have a pending payment. Please wait for verification.')
                return redirect('payment_list')

            payment = form.save(commit=False)
            payment.user = request.user
            payment.expiry_date = timezone.now() + timedelta(days=7)  # Payment expires in 7 days
            payment.save()
            
            # Notify admins about new payment
            admins = User.objects.filter(role='admin')
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                send_mail(
                    'New Payment Submission',
                    f'A new payment has been submitted by {request.user.get_full_name()}',
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=True,
                )
            
            messages.success(request, 'Payment submitted. Awaiting verification.')
            return redirect('payment_list')
    else:
        form = PaymentForm(user=request.user)
    return render(request, 'payments/payment_submit.html', {'form': form})

@admin_required
def payment_verify(request, pk):
    payment = Payment.objects.get(pk=pk)
    
    # Check if payment has expired
    if payment.expiry_date and payment.expiry_date < timezone.now():
        payment.status = 'expired'
        payment.save()
        messages.warning(request, 'This payment has expired.')
        return redirect('payment_list')
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status not in ['verified', 'rejected']:
            messages.error(request, 'Invalid status.')
            return redirect('payment_list')
            
        payment.status = status
        payment.verified_by = request.user
        payment.verification_date = timezone.now()
        payment.save()
        
        # Notify user about payment status
        send_mail(
            f'Payment {status.capitalize()}',
            f'Your payment has been {status}.',
            settings.DEFAULT_FROM_EMAIL,
            [payment.user.email],
            fail_silently=True,
        )
        
        messages.success(request, f'Payment marked as {status}.')
        return redirect('payment_list')
    return render(request, 'payments/payment_verify.html', {'payment': payment})

@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    
    # Check if the user has permission to view the receipt
    if not (request.user.is_admin() or request.user == payment.user):
        messages.error(request, "You do not have permission to view this receipt.")
        return redirect('payments:payment_list')

    # Only allow receipts for verified payments
    if payment.status != 'verified':
        messages.error(request, "Receipts are only available for verified payments.")
        return redirect('payments:payment_list')

    pdf = render_to_pdf(
        'payments/receipt_template.html',
        {
            'payment': payment,
        }
    )
    if pdf:
        response = pdf
        filename = f"receipt_{payment.pk}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    messages.error(request, "Could not generate PDF receipt.")
    return redirect('payments:payment_list')
