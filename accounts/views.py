from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import (
    UserRegisterForm, UserEditForm, CustomLoginForm, RoleManagementForm, GroupForm,
    TeacherCreateStudentForm, TeacherEditStudentForm
)
from .models import User, Group, Badge, UserBadge
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db import models
from django.db.models.functions import TruncMonth
from payments.models import Payment
from announcements.models import Announcement
from events.models import Event
from django.utils import timezone
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from decimal import Decimal
from datetime import date
from events.models import Attendance
from django import forms
from notifications.services import NotificationService, send_realtime_notification
from decimal import Decimal
from .models import RegistrationPayment
from analytics.models import AuditLog, AnalyticsEvent

@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        # Redirect based on user role
        if request.user.is_teacher():
            return redirect('accounts:teacher_dashboard')
        elif request.user.is_scout():
            return redirect('accounts:scout_dashboard')
        else:
            return redirect('home')
    # Analytics
    member_count = User.objects.count()
    payment_total = Payment.objects.filter(status='verified').aggregate(total=models.Sum('amount'))['total'] or 0
    payment_pending = Payment.objects.filter(status='pending').count()
    announcement_count = Announcement.objects.count()
    # Membership growth by month
    member_growth = (
        User.objects.annotate(month=TruncMonth('date_joined'))
        .values('month')
        .order_by('month')
        .annotate(count=models.Count('id'))
    )
    # Payment trends by month
    payment_trends = (
        Payment.objects.filter(status='verified')
        .annotate(month=TruncMonth('date'))
        .values('month')
        .order_by('month')
        .annotate(total=models.Sum('amount'))
    )
    # Announcement engagement
    announcement_engagement = [
        {
            'title': a.title,
            'read': a.read_by.count(),
            'total': a.recipients.count() or User.objects.count(),
        }
        for a in Announcement.objects.all()
    ]
    # Most active scouts (by payment count)
    active_scouts = (
        User.objects.filter(rank='scout')
        .annotate(payment_count=models.Count('payments'))
        .order_by('-payment_count')[:5]
    )
    # Attendance analytics
    # Attendance rate per event
    attendance_rates = []
    for event in Event.objects.order_by('-date')[:5]:
        total = event.attendances.count()
        present = event.attendances.filter(status='present').count()
        rate = (present / total * 100) if total else 0
        attendance_rates.append({
            'event': event,
            'present': present,
            'total': total,
            'rate': rate,
        })
    # Most/least active scouts by attendance
    scout_attendance = User.objects.filter(rank='scout').annotate(
        present_count=models.Count('attendances', filter=models.Q(attendances__status='present')),
        absent_count=models.Count('attendances', filter=models.Q(attendances__status='absent')),
        total_attendance=models.Count('attendances')
    )
    most_active_scouts = scout_attendance.order_by('-present_count')[:5]
    least_active_scouts = scout_attendance.order_by('present_count')[:5]
    # Scouts with repeated absences (3+ absences)
    repeated_absentees = scout_attendance.filter(absent_count__gte=3).order_by('-absent_count')[:5]
    # Check if the logged-in admin user has any verified payments
    is_active_member = Payment.objects.filter(user=request.user, status='verified').exists()
    # Recent Activity: mix of audit logs and analytics events
    # Client-side filtering; default selection is 'all'
    activity_filter = 'all'
    recent_logs = list(AuditLog.objects.select_related('user').order_by('-timestamp')[:10])
    recent_events = list(AnalyticsEvent.objects.select_related('user').order_by('-timestamp')[:10])
    # Normalize to a single list of objects with common attributes for template
    unified = []
    for l in recent_logs:
        unified.append(type('Item', (), {
            'action': l.action,
            'details': l.details,
            'timestamp': l.timestamp,
            'user': l.user,
            'page_url': None,
            'event_type': 'audit',
        }))
    for e in recent_events:
        unified.append(type('Item', (), {
            'action': e.event_type.replace('_', ' ').title(),
            'details': e.metadata if isinstance(e.metadata, str) else (e.metadata or ''),
            'timestamp': e.timestamp,
            'user': e.user,
            'page_url': e.page_url,
            'event_type': e.event_type,
        }))
    # No server-side filtering; the template JS handles filter chips without reload
    recent_activity = sorted(unified, key=lambda x: x.timestamp, reverse=True)[:12]

    return render(request, 'accounts/admin_dashboard.html', {
        'member_count': member_count,
        'payment_total': payment_total,
        'payment_pending': payment_pending,
        'announcement_count': announcement_count,
        'member_growth': list(member_growth),
        'payment_trends': list(payment_trends),
        'announcement_engagement': announcement_engagement,
        'active_scouts': active_scouts,
        'attendance_rates': attendance_rates,
        'most_active_scouts': most_active_scouts,
        'least_active_scouts': least_active_scouts,
        'repeated_absentees': repeated_absentees,
        'is_active_member': is_active_member,
        'recent_activity': recent_activity,
    'activity_filter': activity_filter,
    })

@login_required
def scout_dashboard(request):
    if not request.user.is_scout():
        # Redirect based on user role
        if request.user.is_admin():
            return redirect('accounts:admin_dashboard')
        elif request.user.is_teacher():
            return redirect('accounts:teacher_dashboard')
        else:
            return redirect('home')
    is_active_member = Payment.objects.filter(user=request.user, status='verified').exists()
    # Profile completeness check
    user = request.user
    incomplete_fields = []
    if not user.phone_number:
        incomplete_fields.append('Phone Number')
    if not user.address:
        incomplete_fields.append('Address')
    if not user.emergency_contact:
        incomplete_fields.append('Emergency Contact')
    if not user.emergency_phone:
        incomplete_fields.append('Emergency Phone')
    profile_incomplete = bool(incomplete_fields)

    # Fetch latest announcements for this user (limit 5)
    from announcements.models import Announcement
    latest_announcements = Announcement.objects.order_by('-date_posted')[:3]



    # Fetch upcoming events (limit 5)
    from events.models import Event, EventRegistration
    from django.utils import timezone
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time')[:3]
    
    # Fetch pending event payments for this user
    pending_event_payments = EventRegistration.objects.filter(
        user=user,
        event__payment_amount__gt=0,
        payment_status__in=['pending'],  # Only pending payments
        event__date__gte=today
    ).select_related('event').order_by('event__date', 'event__time')[:5]

    return render(request, 'accounts/scout_dashboard.html', {
        'is_active_member': is_active_member,
        'profile_incomplete': profile_incomplete,
        'incomplete_fields': incomplete_fields,
        'latest_announcements': latest_announcements,
        'upcoming_events': upcoming_events if user.registration_status == 'payment_verified' or user.rank == 'admin' else [],
        'pending_event_payments': pending_event_payments,
        'today': today,
    })

@login_required
def teacher_dashboard(request):
    """Teacher dashboard view - shows students managed by this teacher"""
    if not request.user.is_teacher():
        # Redirect non-teachers to their appropriate dashboard
        if request.user.is_admin():
            return redirect('accounts:admin_dashboard')
        else:
            return redirect('accounts:scout_dashboard')
    
    user = request.user
    
    # Get all students managed by this teacher
    managed_students = User.objects.filter(managed_by=user).select_related('managed_by')
    
    # Student statistics
    total_students = managed_students.count()
    active_students = managed_students.filter(registration_status__in=['active', 'payment_verified']).count()
    inactive_students = managed_students.filter(registration_status='inactive').count()
    graduated_students = managed_students.filter(registration_status='graduated').count()
    suspended_students = managed_students.filter(registration_status='suspended').count()
    
    # Get upcoming events
    from events.models import Event, EventRegistration
    from django.utils import timezone
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time')[:5]
    
    # Get students registered for upcoming events
    students_in_events = EventRegistration.objects.filter(
        user__in=managed_students,
        event__date__gte=today
    ).select_related('user', 'event').order_by('event__date', 'event__time')[:10]
    
    # Get recent activity of managed students
    from payments.models import Payment
    recent_payments = Payment.objects.filter(
        user__in=managed_students
    ).select_related('user').order_by('-date')[:5]
    
    # Check teacher's own registration status
    is_registration_complete = user.is_registration_complete
    registration_payment_pending = user.registration_status == 'pending_payment'
    
    # Profile completeness check for teacher
    incomplete_fields = []
    if not user.phone_number:
        incomplete_fields.append('Phone Number')
    if not user.address:
        incomplete_fields.append('Address')
    if not user.emergency_contact:
        incomplete_fields.append('Emergency Contact')
    if not user.emergency_phone:
        incomplete_fields.append('Emergency Phone')
    profile_incomplete = bool(incomplete_fields)
    
    # Latest announcements
    from announcements.models import Announcement
    latest_announcements = Announcement.objects.order_by('-date_posted')[:3]
    
    return render(request, 'accounts/teacher_dashboard.html', {
        'managed_students': managed_students,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'graduated_students': graduated_students,
        'suspended_students': suspended_students,
        'upcoming_events': upcoming_events,
        'students_in_events': students_in_events,
        'recent_payments': recent_payments,
        'is_registration_complete': is_registration_complete,
        'registration_payment_pending': registration_payment_pending,
        'profile_incomplete': profile_incomplete,
        'incomplete_fields': incomplete_fields,
        'latest_announcements': latest_announcements,
        'today': today,
    })

@login_required
def teacher_create_student(request):
    """Teacher creates a new student account"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can create student accounts.')
        return redirect('home')
    
    if request.method == 'POST':
        form = TeacherCreateStudentForm(request.POST, teacher=request.user)
        if form.is_valid():
            student = form.save()
            
            # Get registration fee from system config
            from payments.models import SystemConfiguration
            from events.paymongo_service import PayMongoService
            from .models import RegistrationPayment
            
            system_config = SystemConfiguration.get_config()
            registration_fee = system_config.registration_fee if system_config else Decimal('500.00')
            
            # Create PayMongo payment for this student
            paymongo = PayMongoService()
            
            try:
                # Create PayMongo source
                source_data = paymongo.create_source(
                    amount=registration_fee,
                    type='gcash',
                    redirect_success=request.build_absolute_uri('/accounts/registration-payment/'),
                    redirect_failed=request.build_absolute_uri('/accounts/registration-payment/'),
                    metadata={
                        'user_email': student.email,
                        'user_name': student.get_full_name(),
                        'description': f"Registration Fee - {student.get_full_name()} (created by teacher {request.user.get_full_name()})",
                        'payment_type': 'registration',
                    }
                )
                
                if source_data and 'id' in source_data:
                    # Create RegistrationPayment record linked to the student
                    reg_payment = RegistrationPayment.objects.create(
                        user=student,
                        amount=registration_fee,
                        paymongo_source_id=source_data['id'],
                        paymongo_checkout_url=source_data['attributes']['redirect']['checkout_url'],
                        payment_method='paymongo_gcash',
                        status='pending',
                        notes=f"Created by teacher {request.user.get_full_name()}"
                    )
                    
                    # Send welcome email to student with login credentials
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    try:
                        subject = 'Welcome to Boy Scout System - Your Account Details'
                        message = f"""
Hello {student.get_full_name()},

Your teacher, {request.user.get_full_name()}, has created an account for you in the Boy Scout System.

Here are your login credentials:
Email: {student.email}
Username: {student.username}
Password: (The password set by your teacher)

Your account will be activated once your teacher completes the registration payment.

You can log in at: {request.build_absolute_uri('/accounts/login/')}

If you have any questions, please contact your teacher.

Best regards,
Boy Scout System Team
"""
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [student.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        messages.warning(request, f'Student created but email notification failed: {str(e)}')
                    
                    messages.success(
                        request, 
                        f'Student {student.get_full_name()} created successfully! Please complete the registration payment of ₱{registration_fee}. '
                        f'<a href="{reg_payment.paymongo_checkout_url}" target="_blank" class="alert-link">Click here to pay now</a>',
                        extra_tags='safe'
                    )
                    return redirect('accounts:teacher_student_list')
                else:
                    # PayMongo failed, delete student and show error
                    student.delete()
                    messages.error(request, 'Failed to create payment. Please try again or contact support.')
                    
            except Exception as e:
                # Error creating payment, delete student
                student.delete()
                messages.error(request, f'Error creating payment: {str(e)}. Please try again.')
    else:
        form = TeacherCreateStudentForm(teacher=request.user)
    
    return render(request, 'accounts/teacher/create_student.html', {'form': form})

@login_required
def teacher_student_list(request):
    """List all students managed by this teacher"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can view this page.')
        return redirect('home')
    
    students = User.objects.filter(managed_by=request.user).order_by('last_name', 'first_name')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        students = students.filter(registration_status=status_filter)
    
    return render(request, 'accounts/teacher/student_list.html', {
        'students': students,
        'status_filter': status_filter,
    })

@login_required
def teacher_edit_student(request, student_id):
    """Teacher edits a student account they manage"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can edit student accounts.')
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, managed_by=request.user)
    
    if request.method == 'POST':
        form = TeacherEditStudentForm(request.POST, instance=student)
        if form.is_valid():
            updated_student = form.save()
            
            # Notify teacher if student updated their own profile
            messages.success(request, f'Student {updated_student.get_full_name()} updated successfully!')
            
            # Send notification to student about profile update
            try:
                send_realtime_notification(
                    student.id,
                    f"Your teacher, {request.user.get_full_name()}, has updated your profile information.",
                    type='profile_update'
                )
            except Exception as e:
                # Don't fail the whole operation if notification fails
                pass
            
            return redirect('accounts:teacher_student_list')
        else:
            # Show form errors
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TeacherEditStudentForm(instance=student)
    
    return render(request, 'accounts/teacher/edit_student.html', {
        'form': form,
        'student': student,
    })

@login_required
def teacher_student_detail(request, student_id):
    """View detailed information about a student"""
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can view student details.')
        return redirect('home')
    
    student = get_object_or_404(User, id=student_id, managed_by=request.user)
    
    # Get student's event registrations
    from events.models import EventRegistration, Attendance
    event_registrations = EventRegistration.objects.filter(user=student).select_related('event').order_by('-event__date')
    
    # Get student's attendance records
    attendance_records = Attendance.objects.filter(user=student).select_related('event').order_by('-event__date')
    
    # Get student's payments
    from payments.models import Payment
    payments = Payment.objects.filter(user=student).order_by('-date')
    
    return render(request, 'accounts/teacher/student_detail.html', {
        'student': student,
        'event_registrations': event_registrations,
        'attendance_records': attendance_records,
        'payments': payments,
    })

def register(request):
    from django.db import models
    from payments.models import Payment, SystemConfiguration
    from django.utils import timezone
    from events.paymongo_service import PayMongoService
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        relativedelta = None
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            # Create user account
            user = form.save(commit=False)
            user.rank = form.cleaned_data.get('rank', 'scout')
            user.is_active = True
            user.registration_status = 'pending_payment'
            user.save()

            # Get registration fee from system config
            system_config = SystemConfiguration.get_config()
            registration_fee = system_config.registration_fee if system_config else Decimal('500.00')
            
            # Create PayMongo payment
            from .models import RegistrationPayment
            paymongo = PayMongoService()
            
            try:
                # Create PayMongo source with registration details
                source_data = paymongo.create_source(
                    amount=registration_fee,
                    type='gcash',
                    redirect_success=request.build_absolute_uri('/accounts/registration-payment/'),
                    redirect_failed=request.build_absolute_uri('/accounts/registration-payment/'),
                    metadata={
                        'user_email': user.email,
                        'user_name': user.get_full_name(),
                        'description': f"Registration Fee - {user.get_full_name()}",
                        'payment_type': 'registration',
                    }
                )
                
                if source_data and 'id' in source_data:
                    # Create RegistrationPayment record with PayMongo data
                    reg_payment = RegistrationPayment.objects.create(
                        user=user,
                        amount=registration_fee,
                        paymongo_source_id=source_data['id'],
                        paymongo_checkout_url=source_data['attributes']['redirect']['checkout_url'],
                        payment_method='paymongo_gcash',
                        status='pending',
                        notes=f"PayMongo payment created for registration"
                    )
                    
                    # Notify admins
                    admins = User.objects.filter(rank='admin')
                    for admin in admins:
                        send_realtime_notification(
                            admin.id,
                            f"New user registered: {user.get_full_name()} ({user.email}) - Payment pending",
                            type='registration'
                        )
                    
                    messages.success(
                        request, 
                        f'Registration successful! Please complete your payment of ₱{registration_fee}. Click the "Pay Now" button on the next page.'
                    )
                    return redirect('accounts:registration_payment', user_id=user.id)
                else:
                    # PayMongo failed, show error
                    user.delete()  # Clean up user account
                    messages.error(request, 'Failed to create payment. Please try again or contact support.')
                    
            except Exception as e:
                # Error creating payment
                user.delete()  # Clean up user account
                messages.error(request, f'Error creating payment: {str(e)}. Please try again.')
                
    else:
        form = UserRegisterForm()
    
    # Get the registration fee from system configuration
    system_config = SystemConfiguration.get_config()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'registration_fee': system_config.registration_fee if system_config else Decimal('500.00')
    })

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        print(f"[DEBUG] admin_required decorator: user={request.user}, is_authenticated={request.user.is_authenticated}, is_admin={request.user.is_admin() if request.user.is_authenticated else 'N/A'}")
        if request.user.is_authenticated and request.user.is_admin():
            print(f"[DEBUG] admin_required: Access granted")
            return view_func(request, *args, **kwargs)
        else:
            print(f"[DEBUG] admin_required: Access denied, redirecting")
            return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)(request, *args, **kwargs)
    return wrapper

@admin_required
def member_list(request):
    query = request.GET.get('q', '')
    filter_rank = request.GET.get('rank', '')
    members = User.objects.all()
    if query:
        members = members.filter(models.Q(username__icontains=query) | models.Q(email__icontains=query) | models.Q(first_name__icontains=query) | models.Q(last_name__icontains=query))
    if filter_rank:
        members = members.filter(rank=filter_rank)
    
    registration_fee = 500  # Registration fee instead of monthly dues
    
    # Import EventRegistration for event payments
    from events.models import EventRegistration
    
    for member in members:
        # Get verified general payments
        payments = member.payments.filter(status='verified')
        total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Add verified registration payments
        verified_registration_payments = member.registration_payments.filter(status='verified')
        registration_payments_total = verified_registration_payments.aggregate(total=models.Sum('amount'))['total'] or 0
        total_paid += registration_payments_total
        
        # Add verified event payments
        verified_event_payments = EventRegistration.objects.filter(
            user=member,
            payment_status='paid'
        ).select_related('event')
        
        event_payments_total = sum(
            reg.event.payment_amount for reg in verified_event_payments 
            if reg.event.payment_amount
        )
        total_paid += event_payments_total
        
        # Calculate registration dues
        registration_dues = member.registration_amount_remaining
        
        # Calculate event dues (pending and partial payments)
        event_dues = EventRegistration.objects.filter(
            user=member,
            payment_status__in=['pending', 'partial']
        ).select_related('event')
        
        event_dues_total = sum(
            reg.amount_remaining for reg in event_dues
            if reg.amount_remaining > 0
        )
        
        # Calculate total dues (registration + event dues)
        total_dues = registration_dues + event_dues_total
        
        balance = total_paid - total_dues
        member.balance_info = {
            'total_paid': total_paid,
            'total_dues': total_dues,
            'balance': balance,
            'registration_status': member.registration_status,
            'registration_payments': registration_payments_total,
            'registration_dues': registration_dues,
            'event_payments': event_payments_total,
            'event_dues': event_dues_total,
            'general_payments': payments.aggregate(total=models.Sum('amount'))['total'] or 0,
        }
    
    paginator = Paginator(members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/member_list.html', {
        'members': members,
        'query': query,
        'filter_rank': filter_rank,
        'rank_choices': User.RANK_CHOICES,
    })

@login_required
def member_detail(request, pk):
    user = User.objects.get(pk=pk)
    if not (request.user.is_admin() or request.user.pk == user.pk):
        return HttpResponseForbidden()
    
    registration_fee = 500  # Registration fee instead of monthly dues
    
    # Get verified general payments
    payments = user.payments.filter(status='verified')
    total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Add verified registration payments
    verified_registration_payments = user.registration_payments.filter(status='verified')
    registration_payments_total = verified_registration_payments.aggregate(total=models.Sum('amount'))['total'] or 0
    total_paid += registration_payments_total
    
    # Add verified event payments
    from events.models import EventRegistration
    verified_event_payments = EventRegistration.objects.filter(
        user=user,
        payment_status='paid'
    ).select_related('event')
    
    event_payments_total = sum(
        reg.event.payment_amount for reg in verified_event_payments 
        if reg.event.payment_amount
    )
    total_paid += event_payments_total
    
    # Calculate registration dues
    registration_dues = user.registration_amount_remaining
    
    # Calculate event dues (pending and partial payments)
    event_dues = EventRegistration.objects.filter(
        user=user,
        payment_status__in=['pending', 'partial']
    ).select_related('event')
    
    event_dues_total = sum(
        reg.amount_remaining for reg in event_dues
        if reg.amount_remaining > 0
    )
    
    # Calculate total dues (registration + event dues)
    total_dues = registration_dues + event_dues_total
    
    balance = total_paid - total_dues
    
    # Badge progress for this member
    user_badges = user.user_badges.select_related('badge').all().order_by('-awarded', '-percent_complete', 'badge__name')
    return render(request, 'accounts/member_detail.html', {
        'member': user,
        'total_paid': total_paid,
        'total_dues': total_dues,
        'balance': balance,
        'user_badges': user_badges,
        'registration_status': user.registration_status,
        'registration_payments': registration_payments_total,
        'registration_dues': registration_dues,
        'event_payments': event_payments_total,
        'event_dues': event_dues_total,
        'general_payments': payments.aggregate(total=models.Sum('amount'))['total'] or 0,
        'verified_event_payments': verified_event_payments,
        'verified_registration_payments': verified_registration_payments,
    })

@admin_required
@admin_required
def member_edit(request, pk):
    user = User.objects.get(pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member updated successfully.')
            return redirect('accounts:member_list')
        else:
            messages.error(request, 'There was an error updating the member profile. Please check the form for details.')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'accounts/member_edit.html', {'form': form, 'member': user})

@admin_required
def member_delete(request, pk):
    user = User.objects.get(pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Member deleted successfully.')
        return redirect('accounts:member_list')
    return render(request, 'accounts/member_delete_confirm.html', {'member': user})

@login_required
def profile_edit(request):
    user = request.user
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'There was an error updating your profile. Please check the form for details.')
    else:
        form = UserEditForm(instance=user, user=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def profile_view(request):
    user = request.user
    incomplete_fields = []
    if not user.phone_number:
        incomplete_fields.append('Phone Number')
    if not user.address:
        incomplete_fields.append('Address')
    if not user.emergency_contact:
        incomplete_fields.append('Emergency Contact')
    if not user.emergency_phone:
        incomplete_fields.append('Emergency Phone')
    profile_incomplete = bool(incomplete_fields)
    # Attendance history
    attendance_history = Attendance.objects.filter(user=user).select_related('event').order_by('-event__date')
    # Badge progress
    user_badges = user.user_badges.select_related('badge').all().order_by('-awarded', '-percent_complete', 'badge__name')
    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile_incomplete': profile_incomplete,
        'incomplete_fields': incomplete_fields,
        'attendance_history': attendance_history,
        'user_badges': user_badges,
    })

@admin_required
def settings_view(request):
    if request.method == 'POST':
        form = RoleManagementForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            rank = form.cleaned_data['rank']
            user.rank = rank
            user.save()
            messages.success(request, f"Successfully updated {user.username}'s rank to {rank}.")
            return redirect('accounts:settings')
    else:
        form = RoleManagementForm()
    
    return render(request, 'accounts/settings.html', {'form': form})

@admin_required
def group_list(request):
    groups = Group.objects.all().order_by('name')
    return render(request, 'accounts/group_list.html', {'groups': groups})

@admin_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, 'Group created successfully.')
            return redirect('accounts:group_list')
    else:
        form = GroupForm()
    return render(request, 'accounts/group_form.html', {'form': form, 'action': 'Create'})

@admin_required
def group_edit(request, pk):
    group = Group.objects.get(pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group updated successfully.')
            return redirect('accounts:group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'accounts/group_form.html', {'form': form, 'action': 'Edit'})

@admin_required
def group_delete(request, pk):
    group = Group.objects.get(pk=pk)
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Group deleted successfully.')
        return redirect('accounts:group_list')
    return render(request, 'accounts/group_confirm_delete.html', {'group': group})

@admin_required
def group_detail(request, pk):
    group = Group.objects.get(pk=pk)
    scouts = User.objects.filter(rank='scout').order_by('last_name', 'first_name')
    if request.method == 'POST':
        # Assign scouts to group
        selected_ids = request.POST.getlist('scouts')
        group.members.set(selected_ids)
        group.save()
        messages.success(request, 'Group members updated.')
        return redirect('accounts:group_detail', pk=group.pk)
    return render(request, 'accounts/group_detail.html', {
        'group': group,
        'scouts': scouts,
        'selected_ids': [u.id for u in group.members.all()],
    })

# Announcement views have been moved to announcements/views.py

def home(request):
    latest_announcements = Announcement.objects.order_by('-date_posted')[:3]
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time')[:3]

    return render(request, 'home.html', {
        'latest_announcements': latest_announcements,
        'upcoming_events': upcoming_events,
    })

class MyLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomLoginForm
    redirect_field_name = '' # Explicitly ignore 'next' parameter

    def get_success_url(self):
        # Check if user has completed registration
        if not self.request.user.is_registration_complete:
            # Only redirect if user is not already on a payment-related page
            current_path = self.request.path
            if 'registration-payment' not in current_path and 'payments' not in current_path:
                if self.request.user.registration_status == 'pending_payment':
                    return reverse_lazy('accounts:registration_payment', kwargs={'user_id': self.request.user.id})
                else:
                    messages.warning(self.request, 'Your registration payment is pending verification. Please wait for admin approval.')
                    return reverse_lazy('accounts:registration_payment', kwargs={'user_id': self.request.user.id})
        
        # Redirect based on user role after successful login
        if self.request.user.is_admin():
            return reverse_lazy('accounts:admin_dashboard')
        elif self.request.user.is_teacher():
            return reverse_lazy('accounts:teacher_dashboard')
        elif self.request.user.is_scout():
            return reverse_lazy('accounts:scout_dashboard')
        else:
            # Default redirect for other roles or if role is not explicitly handled
            return reverse_lazy('home')

class MyLogoutView(LogoutView):
    next_page = reverse_lazy('home') # Redirect to home after logout

@admin_required
def quick_announcement(request):
    """Handle quick announcement creation from admin dashboard"""
    print(f"[DEBUG] quick_announcement view entered. Method: {request.method}, User: {request.user}, Is Admin: {request.user.is_admin() if request.user.is_authenticated else 'Not authenticated'}")
    
    if request.method == 'POST':
        print(f"[DEBUG] Processing POST request")
        title = request.POST.get('title')
        message = request.POST.get('message')
        recipients = request.POST.getlist('recipients')
        send_email = request.POST.get('send_email') == 'on'
        send_sms = request.POST.get('send_sms') == 'on'
        print(f"[DEBUG] Quick Announcement POST: title={title}, message={message}, recipients={recipients}, send_email={send_email}, send_sms={send_sms}")
        
        if not title or not message:
            print("[DEBUG] Missing title or message")
            messages.error(request, 'Title and message are required.')
            return redirect('accounts:admin_dashboard')
        
        try:
            # Create the announcement
            announcement = Announcement.objects.create(
                title=title,
                message=message
            )
            print(f"[DEBUG] Announcement created: id={announcement.id}, title={announcement.title}")
            
            # Determine recipients
            if not recipients or 'all' in recipients:
                all_users = User.objects.all()
                announcement.recipients.set(all_users)
                target_users = all_users
                print(f"[DEBUG] Recipients set to all users: count={all_users.count()}")
            else:
                target_users = []
                if 'scouts' in recipients:
                    scouts = User.objects.filter(rank='scout')
                    target_users.extend(scouts)
                if 'admins' in recipients:
                    admins = User.objects.filter(rank='admin')
                    target_users.extend(admins)
                announcement.recipients.set(target_users)
                print(f"[DEBUG] Recipients set to filtered users: count={len(target_users)}")
            
            # Send notifications
            for user in target_users:
                try:
                    send_realtime_notification(user.id, f"New announcement: {announcement.title}", type='announcement')
                except Exception as e:
                    print(f"[DEBUG] Failed to send real-time notification to user {user.id}: {e}")
                
                # Send email if enabled
                if send_email and user.email:
                    try:
                        from django.core.mail import send_mail
                        send_mail(
                            subject=f"[ScoutConnect] {announcement.title}",
                            message=f"{announcement.message}\n\nPosted on: {announcement.date_posted.strftime('%B %d, %Y at %I:%M %p')}",
                            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@scoutconnect.com',
                            recipient_list=[user.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"[DEBUG] Failed to send email to {user.email}: {e}")
                
                # Send SMS if enabled and available
                if send_sms and hasattr(user, 'phone_number') and user.phone_number:
                    try:
                        NotificationService.send_sms(user.phone_number, f"[ScoutConnect] {announcement.title}: {announcement.message[:100]}...")
                    except Exception as e:
                        print(f"[DEBUG] Failed to send SMS to {user.phone_number}: {e}")
            print(f"[DEBUG] Announcement process complete. Title: {announcement.title}")
            messages.success(request, f'Announcement "{announcement.title}" created and sent to {len(target_users)} recipients.')
            
        except Exception as e:
            messages.error(request, f'Failed to create announcement: {str(e)}')
            print(f"[DEBUG] Error creating announcement: {e}")
        
        return redirect('accounts:admin_dashboard')
    
    else:
        print(f"[DEBUG] Not a POST request, redirecting to admin dashboard")
    return redirect('accounts:admin_dashboard')

@admin_required
def badge_list(request):
    badges = Badge.objects.all().order_by('name')
    return render(request, 'accounts/badge_list.html', {'badges': badges})

@admin_required
def badge_manage(request, pk):
    badge = Badge.objects.get(pk=pk)
    scouts = User.objects.filter(rank='scout').order_by('last_name', 'first_name')
    # Get or create UserBadge for each scout
    user_badges = [UserBadge.objects.get_or_create(user=scout, badge=badge)[0] for scout in scouts]
    if request.method == 'POST':
        for user_badge in user_badges:
            prefix = f'scout_{user_badge.user.id}_'
            awarded = request.POST.get(prefix + 'awarded') == 'on'
            percent = request.POST.get(prefix + 'percent', '0')
            notes = request.POST.get(prefix + 'notes', '')
            date_awarded = request.POST.get(prefix + 'date_awarded', '')
            user_badge.awarded = awarded
            user_badge.percent_complete = int(percent) if percent.isdigit() else 0
            user_badge.notes = notes
            user_badge.date_awarded = date_awarded if date_awarded else None
            user_badge.save()
        messages.success(request, 'Badge assignments and progress updated.')
        return redirect('accounts:badge_manage', pk=badge.pk)
    return render(request, 'accounts/badge_manage.html', {
        'badge': badge,
        'user_badges': user_badges,
    })

def registration_payment(request, user_id):
    """View for users to view their registration payment status"""
    user = get_object_or_404(User, id=user_id)
    
    # Allow users to access their own registration payment page, or admins to view any user
    if request.user != user and not request.user.is_admin():
        messages.error(request, 'You can only access your own registration payment page.')
        return redirect('accounts:login')
    
    # Admin users don't need to pay registration fees
    if user.rank == 'admin':
        messages.info(request, 'Admin users do not need to pay registration fees.')
        return redirect('accounts:admin_dashboard' if user.is_admin() else 'accounts:scout_dashboard')
    
    # If user is already active and registration is complete, redirect to dashboard
    if user.is_active and user.registration_status == 'active':
        messages.info(request, 'Your account is already active!')
        return redirect('home')
    
    # Get payment history for this user
    from .models import RegistrationPayment
    payments = user.registration_payments.all().order_by('-created_at')
    
    return render(request, 'accounts/registration_payment.html', {
        'user': user,
        'payments': payments,
    })

@admin_required
def verify_registration_payment(request, user_id):
    """View for admins to verify registration payments"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        payment_id = request.POST.get('payment_id')
        payment_amount = request.POST.get('payment_amount')
        
        if payment_id:
            # Verify a specific payment
            payment = get_object_or_404(RegistrationPayment, pk=payment_id, user=user)
            
            if action == 'verify':
                # Validate payment amount
                try:
                    if payment_amount:
                        amount = Decimal(payment_amount)
                        if amount <= 0:
                            messages.error(request, 'Payment amount must be greater than 0.')
                            return redirect('accounts:verify_registration_payment', user_id=user_id)
                        payment.amount = amount
                    else:
                        messages.error(request, 'Please enter the payment amount.')
                        return redirect('accounts:verify_registration_payment', user_id=user_id)
                except (ValueError, TypeError):
                    messages.error(request, 'Please enter a valid payment amount.')
                    return redirect('accounts:verify_registration_payment', user_id=user_id)
                
                payment.status = 'verified'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.notes = notes
                payment.save()
                
                # Update user total paid
                user.registration_total_paid += payment.amount
                user.update_registration_status()
                user.save()
                
                # Send notification to user
                send_realtime_notification(
                    user.id, 
                    f"Your registration payment of ₱{payment.amount} has been verified!",
                    type='registration'
                )
                
                # Send email notification
                NotificationService.send_email(
                    subject="Registration Payment Verified - ScoutConnect",
                    message=f"Dear {user.get_full_name()},\n\nYour registration payment of ₱{payment.amount} has been verified by an administrator.\n\nTotal paid: ₱{user.registration_total_paid}\nRemaining: ₱{user.registration_amount_remaining}\n\nBest regards,\nScoutConnect Team",
                    recipient_list=[user.email]
                )
                
                messages.success(request, f'Registration payment of ₱{payment.amount} verified.')
                
            elif action == 'reject':
                rejection_reason = request.POST.get('rejection_reason', '').strip()
                
                payment.status = 'rejected'
                payment.verified_by = request.user
                payment.verification_date = timezone.now()
                payment.rejection_reason = rejection_reason if rejection_reason else 'No reason provided'
                payment.notes = notes
                payment.save()
                
                # Send notification to user
                reason_text = f" Reason: {rejection_reason}" if rejection_reason else ""
                send_realtime_notification(
                    user.id, 
                    f"Your registration payment of ₱{payment.amount} has been rejected.{reason_text}",
                    type='registration'
                )
                
                # Send email notification
                NotificationService.send_email(
                    subject="Registration Payment Rejected - ScoutConnect",
                    message=f"Dear {user.get_full_name()},\n\nYour registration payment of ₱{payment.amount} has been rejected by an administrator.\n\nReason: {payment.rejection_reason}\n\nPlease submit a new payment receipt with the correct information.\n\nBest regards,\nScoutConnect Team",
                    recipient_list=[user.email]
                )
                
                messages.warning(request, f'Registration payment of ₱{payment.amount} rejected.')
        else:
            # Legacy verification for old registrations without RegistrationPayment records
            if action == 'verify':
                user.registration_status = 'active'
                user.is_active = True
                user.registration_verified_by = request.user
                user.registration_verification_date = timezone.now()
                user.registration_notes = notes
                user.save()
                
                # Send notification to user
                send_realtime_notification(
                    user.id, 
                    f"Your registration payment has been verified! Your account is now active.",
                    type='registration'
                )
                
                # Send email notification
                NotificationService.send_email(
                    subject="Registration Payment Verified - ScoutConnect",
                    message=f"Dear {user.get_full_name()},\n\nYour registration payment has been verified by an administrator. Your account is now active and you can log in to ScoutConnect.\n\nWelcome to the ScoutConnect community!\n\nBest regards,\nScoutConnect Team",
                    recipient_list=[user.email]
                )
                
                messages.success(request, f'Registration payment for {user.get_full_name()} has been verified.')
                
            elif action == 'reject':
                user.registration_status = 'pending_payment'
                user.registration_verified_by = request.user
                user.registration_verification_date = timezone.now()
                user.registration_notes = notes
                user.save()
                
                # Send notification to user
                send_realtime_notification(
                    user.id, 
                    f"Your registration payment has been rejected. Please submit a new payment receipt.",
                    type='registration'
                )
                
                # Send email notification
                NotificationService.send_email(
                    subject="Registration Payment Rejected - ScoutConnect",
                    message=f"Dear {user.get_full_name()},\n\nYour registration payment has been rejected by an administrator. Please submit a new payment receipt.\n\nReason: {notes}\n\nBest regards,\nScoutConnect Team",
                    recipient_list=[user.email]
                )
                
                messages.warning(request, f'Registration payment for {user.get_full_name()} has been rejected.')
        
        return redirect('accounts:verify_registration_payment', user_id=user_id)
    
    # Get payment history for this user
    payments = user.registration_payments.all().order_by('-created_at')
    
    registration_fee = user.registration_amount_required
    total_paid = user.registration_total_paid
    membership_years = int(total_paid // registration_fee) if registration_fee else 0
    membership_expiry = user.membership_expiry
    return render(request, 'accounts/verify_registration_payment.html', {
        'user': user,
        'payments': payments,
        'membership_years': membership_years,
        'membership_expiry': membership_expiry,
    })

@admin_required
def pending_registrations(request):
    """View for admins to see all pending registration payments"""
    pending_users = User.objects.filter(
        registration_status__in=['payment_submitted', 'pending_payment']
    ).order_by('-date_joined')
    
    return render(request, 'accounts/pending_registrations.html', {
        'pending_users': pending_users,
    })


# ============================================
# Admin Teacher Management Views
# ============================================

@admin_required
def admin_create_teacher(request):
    """Admin creates a new teacher account directly"""
    from .forms import AdminCreateTeacherForm
    
    if request.method == 'POST':
        form = AdminCreateTeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            
            # Send welcome email to teacher with login credentials and payment instructions
            from django.core.mail import send_mail
            from django.conf import settings
            
            try:
                subject = 'Welcome to Boy Scout System - Teacher Account Created'
                message = f"""
Hello {teacher.get_full_name()},

An administrator has created a teacher account for you in the Boy Scout System.

Here are your login credentials:
Email: {teacher.email}
Username: {teacher.username}
Password: (The password set by the administrator)

IMPORTANT: To activate your account, you need to complete your registration payment of ₱500.00.

Please follow these steps:
1. Log in at: {request.build_absolute_uri('/accounts/login/')}
2. Go to your Teacher Dashboard
3. Navigate to "My Payments" tab
4. Submit your registration payment with proof of payment (GCash receipt)
5. Wait for admin verification

Once your payment is verified, you will be able to:
- Create and manage student accounts
- Register students for events
- Mark attendance for your students
- Submit payments on behalf of students
- View reports and statistics

If you have any questions, please contact the administrator.

Best regards,
Boy Scout System Team
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [teacher.email],
                    fail_silently=True,
                )
            except Exception as e:
                messages.warning(request, f'Teacher created but email notification failed: {str(e)}')
            
            messages.success(request, f'Teacher account for {teacher.get_full_name()} created successfully! They will need to complete their ₱500 registration payment.')
            return redirect('accounts:admin_teacher_list')
    else:
        form = AdminCreateTeacherForm()
    
    return render(request, 'accounts/admin/create_teacher.html', {'form': form})


@admin_required
def admin_teacher_list(request):
    """List all teachers with their statistics"""
    from django.db.models import Count, Q
    from payments.models import Payment
    from events.models import EventRegistration
    
    teachers = User.objects.filter(rank='teacher').annotate(
        student_count=Count('managed_students', distinct=True),
        active_student_count=Count('managed_students', filter=Q(managed_students__registration_status='active'), distinct=True)
    ).order_by('-date_joined')
    
    # Add statistics for each teacher
    teacher_stats = []
    for teacher in teachers:
        # Get students managed by this teacher
        students = User.objects.filter(managed_by=teacher)
        
        # Count payments submitted by teacher
        payments_submitted = Payment.objects.filter(verified_by=teacher).count()
        
        # Count event registrations
        event_registrations = EventRegistration.objects.filter(user__in=students).count()
        
        teacher_stats.append({
            'teacher': teacher,
            'total_students': teacher.student_count,
            'active_students': teacher.active_student_count,
            'payments_submitted': payments_submitted,
            'event_registrations': event_registrations,
        })
    
    return render(request, 'accounts/admin/teacher_list.html', {
        'teacher_stats': teacher_stats,
    })


@admin_required
def admin_teacher_hierarchy(request):
    """View teacher hierarchy - all teachers and their students"""
    from django.db.models import Count
    
    teachers = User.objects.filter(rank='teacher').prefetch_related('managed_students').annotate(
        student_count=Count('managed_students')
    ).order_by('last_name', 'first_name')
    
    # Build hierarchy data
    hierarchy = []
    for teacher in teachers:
        students = teacher.managed_students.all().order_by('last_name', 'first_name')
        hierarchy.append({
            'teacher': teacher,
            'students': students,
            'student_count': students.count(),
        })
    
    # Calculate totals
    total_teachers = teachers.count()
    total_students = User.objects.filter(managed_by__isnull=False).count()
    independent_students = User.objects.filter(rank='scout', managed_by__isnull=True).count()
    
    return render(request, 'accounts/admin/teacher_hierarchy.html', {
        'hierarchy': hierarchy,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'independent_students': independent_students,
    })
