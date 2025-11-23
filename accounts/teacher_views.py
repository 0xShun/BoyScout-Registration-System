"""
Views for teacher functionality: registration, dashboard, and student management.
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction, models
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from decimal import Decimal
import secrets
import string
import logging

logger = logging.getLogger(__name__)

from .models import User, RegistrationPayment, SystemSettings
from .teacher_forms import (
    TeacherRegisterForm, 
    TeacherBulkStudentForm, 
    StudentForm,
    StudentFormSet,
    StudentEditForm,
    StudentPasswordResetForm
)
from payments.services.paymongo_service import PayMongoService
from notifications.services import NotificationService


def is_teacher(user):
    """Check if user is a teacher"""
    return user.is_authenticated and user.role == 'teacher'


def register_teacher(request):
    """
    Teacher registration view with .edu email validation and payment integration.
    """
    if request.method == 'POST':
        form = TeacherRegisterForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the teacher user and activate immediately
                    user = form.save(commit=False)
                    user.is_active = True  # Active immediately per requirement
                    user.registration_status = 'active'
                    user.save()
                    
                    # Log successful teacher account creation
                    logger.info(f"Teacher account created: {user.email} (ID: {user.id}, Role: {user.role})")

                    # NOTE: auto-login is performed later (after session flags are set)
                    # to avoid session lifecycle races where session data might be
                    # rotated/deleted during the request lifecycle.

                    # Get registration fee from system settings
                    registration_fee = SystemSettings.get_registration_fee()

                    # Create registration payment record and mark as verified (user is already active)
                    payment = RegistrationPayment.objects.create(
                        user=user,
                        amount=registration_fee,
                        status='verified',
                        notes='Teacher registration payment - created at registration'
                    )

                    # Initiate PayMongo payment so the user can complete payment after account creation
                    paymongo_service = PayMongoService()

                    # Create payment source
                    source_result = paymongo_service.create_source(
                        amount=float(registration_fee),
                        description=f"Teacher Registration - {user.get_full_name()}"
                    )

                    if source_result.get('success'):
                        source_data = source_result.get('data')
                        if source_data:
                            payment.paymongo_source_id = source_data.get('id')
                            payment.save()

                            # Store a session flag so we can display the success message on the login page
                            request.session['registration_success'] = 'Your teacher account was created — please complete payment to finalize your registration.'

                            # If the registrant was anonymous (self-registration), auto-login now.
                            # Perform this after writing session flags to avoid session rotation
                            # races that can raise SessionInterrupted.
                            try:
                                if request.user.is_anonymous:
                                    backend = None
                                    if getattr(settings, 'AUTHENTICATION_BACKENDS', None):
                                        backend = settings.AUTHENTICATION_BACKENDS[0]
                                    else:
                                        backend = 'django.contrib.auth.backends.ModelBackend'
                                    user.backend = backend
                                    login(request, user)
                                    logger.info(f"Teacher auto-logged in after registration: {user.email}")
                            except Exception as login_error:
                                # Best-effort auto-login: on error, continue without failing registration.
                                logger.warning(f"Auto-login failed for teacher {user.email}: {login_error}")
                                pass

                            # Redirect to PayMongo checkout
                            checkout_url = source_data.get('attributes', {}).get('redirect', {}).get('checkout_url')
                            messages.success(
                                request,
                                f'✓ Teacher account created successfully! You will be redirected to complete payment of ₱{registration_fee:.2f}.'
                            )
                            return redirect(checkout_url) if checkout_url else redirect('home')
                        else:
                            # No source data
                            logger.error(f"PayMongo returned no source data for teacher registration: {user.email}")
                            messages.error(request, 'Payment gateway returned no checkout information. Please contact support.')
                            return redirect('accounts:register_teacher')
                    else:
                        error_msg = source_result.get('error', 'Unknown error')
                        logger.error(f"PayMongo source creation failed for teacher {user.email}: {error_msg}")
                        messages.error(request, f'Failed to create payment link: {error_msg}. Please contact support.')
                        return redirect('accounts:register_teacher')

            except Exception as e:
                logger.exception(f"Teacher registration failed: {str(e)}")
                messages.error(request, f'❌ Registration failed: {str(e)}. Please try again or contact support.')
                return redirect('accounts:register_teacher')
        else:
            # Form validation errors
            logger.warning(f"Teacher registration form validation failed: {form.errors}")
            messages.error(
                request, 
                '❌ Registration form has errors. Please check your input and ensure you\'re using a .edu email address.'
            )
    else:
        form = TeacherRegisterForm()
    
    return render(request, 'accounts/register_teacher.html', {'form': form})


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_dashboard(request):
    """
    Teacher dashboard - overview of their students and activities.
    """
    teacher = request.user
    
    # Get all students registered by this teacher
    students = User.objects.filter(registered_by_teacher=teacher)
    
    # Statistics
    total_students = students.count()
    active_students = students.filter(is_active=True).count()
    inactive_students = students.filter(is_active=False).count()
    
    # Recent students (last 5)
    recent_students = students.order_by('-date_joined')[:5]
    
    # Payment statistics
    total_paid = RegistrationPayment.objects.filter(
        paid_by_teacher=teacher,
        status='verified'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    pending_payments = RegistrationPayment.objects.filter(
        paid_by_teacher=teacher,
        status='pending'
    ).count()
    
    context = {
        'teacher': teacher,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'recent_students': recent_students,
        'total_paid': total_paid,
        'pending_payments': pending_payments,
    }
    
    return render(request, 'accounts/teacher_dashboard.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_students(request):
    """
    List all students registered by this teacher with search and filter.
    """
    teacher = request.user
    students = User.objects.filter(registered_by_teacher=teacher).order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(username__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'students': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_students': students.count(),
    }
    
    return render(request, 'accounts/teacher_students.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_register_students(request):
    """
    Bulk student registration by teachers with payment integration.
    Students are activated immediately after payment.
    """
    teacher = request.user
    
    if request.method == 'POST':
        formset = StudentFormSet(request.POST)
        
        if formset.is_valid():
            # Collect valid student data
            student_data_list = []
            
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    student_data = form.cleaned_data.copy()
                    # Auto-generate username
                    base_username = f"{student_data['first_name']}{student_data['last_name']}".lower().replace(' ', '')
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists() or \
                          any(s.get('username') == username for s in student_data_list):
                        username = f"{base_username}{counter}"
                        counter += 1
                    student_data['username'] = username
                    student_data_list.append(student_data)
            
            if not student_data_list:
                messages.error(request, 'Please add at least one student.')
                registration_fee = SystemSettings.get_registration_fee()
                context = {
                    'formset': formset,
                    'registration_fee': registration_fee,
                    'total_fee': registration_fee,
                }
                return render(request, 'accounts/teacher_register_students.html', context)
            
            try:
                with transaction.atomic():
                    # Get registration fee
                    registration_fee = SystemSettings.get_registration_fee()
                    number_of_students = len(student_data_list)
                    total_amount = registration_fee * number_of_students
                    
                    # Create student users and payment records
                    created_students = []
                    
                    for student_data in student_data_list:
                        # Generate secure random password
                        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
                        
                        # Create user account - ACTIVE immediately
                        user = User.objects.create(
                            username=student_data['username'],
                            first_name=student_data['first_name'],
                            last_name=student_data['last_name'],
                            email=student_data['email'],
                            phone_number=student_data.get('phone_number', ''),
                            date_of_birth=student_data['date_of_birth'],
                            address=student_data['address'],
                            password=make_password(password),
                            role='scout',
                            is_active=True,  # ACTIVE IMMEDIATELY
                            registration_status='active',
                            registered_by_teacher=teacher
                        )
                        
                        # Create RegistrationPayment record
                        payment = RegistrationPayment.objects.create(
                            user=user,
                            paid_by_teacher=teacher,
                            amount=registration_fee,
                            status='verified',  # VERIFIED immediately
                            notes=f'Bulk registration by teacher {teacher.get_full_name()}'
                        )
                        
                        created_students.append({
                            'user': user,
                            'password': password,
                            'email': student_data['email']
                        })
                    
                    # Initiate PayMongo payment for teacher
                    paymongo_service = PayMongoService()
                    
                    source_result = paymongo_service.create_source(
                        amount=float(total_amount),
                        description=f"Bulk Student Registration - {number_of_students} students by {teacher.get_full_name()}"
                    )
                    
                    if source_result['success']:
                        source_data = source_result['data']
                        
                        # Update all payment records with source ID
                        for student_info in created_students:
                            payment = RegistrationPayment.objects.get(user=student_info['user'])
                            payment.paymongo_source_id = source_data['id']
                            payment.save()
                        
                        # Store student info in session for email sending after payment
                        request.session['created_students'] = [
                            {
                                'email': s['email'],
                                'first_name': s['user'].first_name,
                                'username': s['user'].username,
                                'password': s['password']
                            }
                            for s in created_students
                        ]
                        request.session['bulk_registration_complete'] = True
                        
                        # Send welcome emails to all students
                        for student_info in created_students:
                            try:
                                NotificationService.send_email(
                                    subject='Welcome to ScoutConnect - Your Account Details',
                                    message=f'''
Dear {student_info['user'].get_full_name()},

Your student account has been created by your teacher {teacher.get_full_name()}!

Your login credentials:
Username: {student_info['user'].username}
Email: {student_info['email']}
Password: {student_info['password']}

You can now log in at: http://127.0.0.1:8000/accounts/login/

Please change your password after your first login for security.

Welcome to ScoutConnect!
                                    ''',
                                    recipient_list=[student_info['email']]
                                )
                            except Exception as e:
                                # Log error but don't fail the registration
                                print(f'Could not send email to {student_info["email"]}: {str(e)}')
                        
                        # Redirect to PayMongo checkout
                        checkout_url = source_data['attributes']['redirect']['checkout_url']
                        
                        messages.success(
                            request,
                            f'✓ Successfully created {number_of_students} student accounts! '
                            f'Please complete the payment of ₱{total_amount:.2f}. '
                            f'All students have been emailed their login credentials.'
                        )
                        
                        return redirect(checkout_url)
                    else:
                        # Payment creation failed - rollback will happen automatically
                        messages.error(
                            request,
                            'Failed to create payment link. Please try again or contact support.'
                        )
                        return redirect('accounts:teacher_register_students')
                        
            except Exception as e:
                messages.error(
                    request,
                    f'Registration failed: {str(e)}. Please try again.'
                )
                registration_fee = SystemSettings.get_registration_fee()
                context = {
                    'formset': formset,
                    'registration_fee': registration_fee,
                    'total_fee': registration_fee,
                }
                return render(request, 'accounts/teacher_register_students.html', context)
        else:
            # Form validation failed
            messages.error(request, 'Please correct the errors below.')
            registration_fee = SystemSettings.get_registration_fee()
            context = {
                'formset': formset,
                'registration_fee': registration_fee,
                'total_fee': registration_fee,
            }
            return render(request, 'accounts/teacher_register_students.html', context)
    
    else:
        # GET request - show the formset
        formset = StudentFormSet()
    
    # Get registration fee for display
    registration_fee = SystemSettings.get_registration_fee()
    
    context = {
        'formset': formset,
        'registration_fee': registration_fee,
        'total_fee': registration_fee,  # Will be updated by JavaScript
    }
    
    return render(request, 'accounts/teacher_register_students.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_edit_student(request, student_id):
    """
    Edit student profile - teachers can only edit their own students.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student {student.get_full_name()} updated successfully!')
            return redirect('accounts:teacher_students')
    else:
        form = StudentEditForm(instance=student)
    
    context = {
        'form': form,
        'student': student,
    }
    
    return render(request, 'accounts/teacher_edit_student.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_delete_student(request, student_id):
    """
    Delete student account - teachers can only delete their own students.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    if request.method == 'POST':
        student_name = student.get_full_name()
        student.delete()
        messages.success(request, f'Student {student_name} has been deleted.')
        return redirect('accounts:teacher_students')
    
    context = {
        'student': student,
    }
    
    return render(request, 'accounts/teacher_delete_student_confirm.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_reset_student_password(request, student_id):
    """
    Reset student password - teachers can set a new password for their students.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    if request.method == 'POST':
        form = StudentPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            student.set_password(new_password)
            student.save()
            
            # Send email notification to student
            try:
                NotificationService.send_email(
                    subject='Your Password Has Been Reset - ScoutConnect',
                    message=f'''
Dear {student.get_full_name()},

Your password has been reset by your teacher {teacher.get_full_name()}.

Your new login credentials:
Username: {student.username}
Email: {student.email}
New Password: {new_password}

Please log in and change your password for security.

Login at: http://127.0.0.1:8000/accounts/login/
                    ''',
                    recipient_list=[student.email]
                )
            except Exception as e:
                messages.warning(request, f'Password reset but email notification failed: {str(e)}')
            
            messages.success(request, f'Password reset for {student.get_full_name()}!')
            return redirect('accounts:teacher_students')
    else:
        form = StudentPasswordResetForm()
    
    context = {
        'form': form,
        'student': student,
    }
    
    return render(request, 'accounts/teacher_reset_password.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_toggle_student_active(request, student_id):
    """
    Activate/deactivate student account.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    if request.method == 'POST':
        student.is_active = not student.is_active
        student.save()
        
        status = 'activated' if student.is_active else 'deactivated'
        messages.success(request, f'Student {student.get_full_name()} has been {status}.')
        
        return redirect('accounts:teacher_students')
    
    context = {
        'student': student,
    }
    
    return render(request, 'accounts/teacher_toggle_active_confirm.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_view_student_payments(request, student_id):
    """
    View payment history for a specific student.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    # Get all payments for this student
    payments = RegistrationPayment.objects.filter(user=student).order_by('-created_at')
    
    # Calculate statistics
    total_payments = payments.count()
    total_amount = sum(p.amount for p in payments if p.status == 'verified')
    paid_by_teacher = payments.filter(paid_by_teacher=teacher).count()
    teacher_paid_amount = sum(p.amount for p in payments if p.paid_by_teacher == teacher and p.status == 'verified')
    
    context = {
        'student': student,
        'payments': payments,
        'total_payments': total_payments,
        'total_amount': total_amount,
        'paid_by_teacher': paid_by_teacher,
        'teacher_paid_amount': teacher_paid_amount,
    }
    
    return render(request, 'accounts/teacher_student_payments.html', context)


@login_required
@user_passes_test(is_teacher, login_url='/accounts/login/')
def teacher_view_student_events(request, student_id):
    """
    View event registrations for a specific student.
    """
    teacher = request.user
    student = get_object_or_404(User, id=student_id, registered_by_teacher=teacher)
    
    # Get all event registrations for this student
    from events.models import EventRegistration
    from django.utils import timezone
    
    registrations = EventRegistration.objects.filter(user=student).order_by('-registration_date')
    
    # Calculate statistics
    today = timezone.now().date()
    total_events = registrations.count()
    upcoming_events = sum(1 for r in registrations if r.event.date >= today)
    past_events = total_events - upcoming_events
    
    context = {
        'student': student,
        'registrations': registrations,
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'today': today,
    }
    
    return render(request, 'accounts/teacher_student_events.html', context)
