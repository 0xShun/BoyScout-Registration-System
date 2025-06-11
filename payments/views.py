from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PaymentForm
from .models import Payment
from accounts.models import User

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
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.save()
            messages.success(request, 'Payment submitted. Awaiting verification.')
            return redirect('payment_list')
    else:
        form = PaymentForm()
    return render(request, 'payments/payment_submit.html', {'form': form})

@admin_required
def payment_verify(request, pk):
    payment = Payment.objects.get(pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        payment.status = status
        payment.save()
        messages.success(request, f'Payment marked as {status}.')
        return redirect('payment_list')
    return render(request, 'payments/payment_verify.html', {'payment': payment})
