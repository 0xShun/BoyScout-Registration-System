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
from .forms import PaymentForm, PaymentQRCodeForm, TeacherPaymentForm
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
        # For scouts, show their general payments only (registration handled separately)
        payments = Payment.objects.filter(user=request.user).order_by('-date')
        
        # Get registration payment info from RegistrationPayment model
        from accounts.models import RegistrationPayment
        total_registration_paid = RegistrationPayment.objects.filter(
            user=request.user, 
            status='verified'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
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
        payments_list = list(payments)
        payments_list.insert(0, registration_payment)
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
            'pending_events': event_registrations.filter(payment_status='pending').count(),
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


@admin_required
def system_config_manage(request):
    """View for admins to manage system-wide QR codes (registration, etc.)"""
    from .models import SystemConfiguration
    from .forms import SystemConfigurationForm
    
    config = SystemConfiguration.get_config()
    
    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.updated_by = request.user
            config.save()
            messages.success(request, 'System QR code updated successfully.')
            return redirect('payments:system_config_manage')
    else:
        form = SystemConfigurationForm(instance=config)
    
    return render(request, 'payments/system_config_manage.html', {
        'form': form,
        'config': config,
    })


# ============================================
# Teacher Payment Management Views
# ============================================

@login_required
def teacher_submit_payment(request):
    """Allow teachers to submit payments on behalf of their students (single or bulk)"""
    if not request.user.is_teacher():
        messages.error(request, "Only teachers can access this page.")
        return redirect('accounts:dashboard')
    
    # Get teacher's students
    students = User.objects.filter(
        managed_by=request.user,
        registration_status='active'
    ).order_by('first_name', 'last_name')
    
    if not students.exists():
        messages.warning(request, "You don't have any active students to submit payments for.")
        return redirect('accounts:teacher_dashboard')
    
    if request.method == 'POST':
        form = TeacherPaymentForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            # Get selected students (either single or multiple)
            single_student = form.cleaned_data.get('student')
            multiple_students = form.cleaned_data.get('students')
            
            # Determine which students to process
            students_to_process = []
            if single_student:
                students_to_process = [single_student]
            elif multiple_students:
                students_to_process = list(multiple_students)
            
            # Get common payment data
            amount = form.cleaned_data['amount']
            receipt_image = form.cleaned_data.get('receipt_image')
            reference_number = form.cleaned_data.get('reference_number')
            notes = form.cleaned_data.get('notes', '')
            
            # Create payment for each student
            created_payments = []
            for student in students_to_process:
                payment = Payment.objects.create(
                    user=student,
                    payee_name=f"{student.first_name} {student.last_name}",
                    payee_email=student.email,
                    amount=amount,
                    receipt_image=receipt_image,
                    reference_number=reference_number,
                    notes=notes,
                    payment_type='other',
                    status='verified',
                    verified_by=request.user,
                    verification_date=timezone.now(),
                    expiry_date=timezone.now() + timedelta(days=365)
                )
                created_payments.append(payment)
                
                # Notify the student about the payment
                try:
                    NotificationService.send_email(
                        subject="Payment Submitted by Your Teacher",
                        message=f"Your teacher has submitted a payment of ₱{payment.amount} on your behalf. This payment has been automatically approved.",
                        recipient_list=[student.email],
                    )
                except Exception as e:
                    logger.error(f"Failed to send email notification: {e}")
                
                # Send real-time notification
                try:
                    send_realtime_notification(
                        student.id,
                        f"Your teacher submitted a payment of ₱{payment.amount} on your behalf.",
                        'payment'
                    )
                except Exception as e:
                    logger.error(f"Failed to send real-time notification: {e}")
            
            # Success message
            if len(created_payments) == 1:
                messages.success(
                    request, 
                    f'Payment of ₱{amount} submitted and approved for {students_to_process[0].get_full_name()}.'
                )
            else:
                messages.success(
                    request,
                    f'Bulk payment submitted! ₱{amount} approved for {len(created_payments)} student(s). Total: ₱{amount * len(created_payments)}'
                )
            
            return redirect('payments:teacher_payment_history')
    else:
        form = TeacherPaymentForm(request.user)
    
    # Get active QR code for payment
    active_qr_code = PaymentQRCode.get_active_qr_code()
    
    return render(request, 'payments/teacher_submit_payment.html', {
        'form': form,
        'active_qr_code': active_qr_code,
        'students': students
    })


@login_required
def teacher_payment_history(request):
    """Show payment history for all students managed by the teacher"""
    if not request.user.is_teacher():
        messages.error(request, "Only teachers can access this page.")
        return redirect('accounts:dashboard')
    
    # Get all students managed by this teacher
    students = User.objects.filter(managed_by=request.user).order_by('first_name', 'last_name')
    
    # Get payments for all these students
    payments = Payment.objects.filter(
        user__in=students
    ).select_related('user', 'verified_by').order_by('-date')
    
    # Filter by status if requested
    status_filter = request.GET.get('status', '')
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    # Filter by student if requested
    student_filter = request.GET.get('student', '')
    if student_filter:
        try:
            student_id = int(student_filter)
            payments = payments.filter(user_id=student_id)
        except (ValueError, TypeError):
            pass
    
    # Pagination
    paginator = Paginator(payments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate summary statistics
    total_verified = payments.filter(status='verified').aggregate(total=Sum('amount'))['total'] or 0
    total_pending = payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
    total_rejected = payments.filter(status='rejected').aggregate(total=Sum('amount'))['total'] or 0
    
    payment_summary = {
        'total_payments': payments.count(),
        'verified_count': payments.filter(status='verified').count(),
        'pending_count': payments.filter(status='pending').count(),
        'rejected_count': payments.filter(status='rejected').count(),
        'total_verified_amount': total_verified,
        'total_pending_amount': total_pending,
        'total_rejected_amount': total_rejected,
    }
    
    return render(request, 'payments/teacher_payment_history.html', {
        'page_obj': page_obj,
        'students': students,
        'payment_summary': payment_summary,
        'status_choices': Payment.STATUS_CHOICES,
        'current_status_filter': status_filter,
        'current_student_filter': student_filter,
    })


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse

@csrf_exempt
@require_POST
def paymongo_webhook_redirect(request):
    """
    Redirect webhook from /payments/webhook/ to /events/webhooks/paymongo/
    This is for backward compatibility with old webhook URL configuration
    """
    from events.views import paymongo_webhook
    return paymongo_webhook(request)
