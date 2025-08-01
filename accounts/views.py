from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm, UserEditForm, CustomLoginForm, RoleManagementForm, GroupForm
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
from datetime import date
from events.models import Attendance
from django import forms
from notifications.services import NotificationService, send_realtime_notification

@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        return redirect('accounts:scout_dashboard')
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
    })

@login_required
def scout_dashboard(request):
    if not request.user.is_scout():
        return redirect('accounts:admin_dashboard')
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
    latest_announcements = Announcement.objects.filter(recipients=user).order_by('-date_posted')[:5]

    # Fetch upcoming events (limit 5)
    from events.models import Event
    from django.utils import timezone
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(date__gte=today).order_by('date', 'time')[:5]

    return render(request, 'accounts/scout_dashboard.html', {
        'is_active_member': is_active_member,
        'profile_incomplete': profile_incomplete,
        'incomplete_fields': incomplete_fields,
        'latest_announcements': latest_announcements,
        'upcoming_events': upcoming_events,
    })

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.rank = 'scout'
            user.is_active = False  # User must pay registration fee first
            user.registration_status = 'pending_payment'
            user.save()
            
            # If receipt is uploaded, update status
            if user.registration_receipt:
                user.registration_status = 'payment_submitted'
                user.save()
                
                # Notify admins about new registration payment
                admins = User.objects.filter(rank='admin')
                for admin in admins:
                    send_realtime_notification(
                        admin.id, 
                        f"New registration payment submitted: {user.get_full_name()} ({user.email})",
                        type='registration'
                    )
                
                messages.success(request, 'Registration successful! Your payment receipt has been submitted and is pending verification by an administrator.')
            else:
                messages.success(request, 'Registration successful! Please submit your registration payment to complete your account activation.')
            
            return redirect('accounts:registration_payment', user_id=user.id)
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

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
    monthly_due = 100
    for member in members:
        payments = member.payments.filter(status='verified')
        total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or 0
        join_date = member.date_joined.date() if member.date_joined else date.today()
        today = date.today()
        months = (today.year - join_date.year) * 12 + (today.month - join_date.month) + 1
        total_dues = months * monthly_due
        balance = total_paid - total_dues
        member.balance_info = {
            'total_paid': total_paid,
            'total_dues': total_dues,
            'balance': balance,
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
    monthly_due = 100
    payments = user.payments.filter(status='verified')
    total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    join_date = user.date_joined.date() if user.date_joined else date.today()
    today = date.today()
    months = (today.year - join_date.year) * 12 + (today.month - join_date.month) + 1
    total_dues = months * monthly_due
    balance = total_paid - total_dues
    # Badge progress for this member
    user_badges = user.user_badges.select_related('badge').all().order_by('-awarded', '-percent_complete', 'badge__name')
    return render(request, 'accounts/member_detail.html', {
        'member': user,
        'total_paid': total_paid,
        'total_dues': total_dues,
        'balance': balance,
        'user_badges': user_badges,
    })

@admin_required
def member_edit(request, pk):
    user = User.objects.get(pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
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
        form = UserEditForm(request.POST, instance=user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:scout_dashboard' if user.is_scout() else 'accounts:admin_dashboard')
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
    """View for users to submit registration payment receipt"""
    user = get_object_or_404(User, id=user_id)
    
    # Allow users to access their own registration payment page
    if request.user != user:
        messages.error(request, 'You can only access your own registration payment page.')
        return redirect('accounts:login')
    
    # If user is already active and registration is complete, redirect to dashboard
    if user.is_active and user.registration_status == 'active':
        messages.info(request, 'Your account is already active. Please log in.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        if 'receipt' in request.FILES:
            user.registration_receipt = request.FILES['receipt']
            user.registration_status = 'payment_submitted'
            user.save()
            
            # Notify admins about new registration payment
            admins = User.objects.filter(rank='admin')
            for admin in admins:
                send_realtime_notification(
                    admin.id, 
                    f"New registration payment submitted: {user.get_full_name()} ({user.email})",
                    type='registration'
                )
            
            messages.success(request, 'Payment receipt submitted successfully! Your account will be activated once an administrator verifies your payment.')
            return redirect('accounts:registration_payment', user_id=user.id)
        else:
            messages.error(request, 'Please upload a payment receipt.')
    
    return render(request, 'accounts/registration_payment.html', {
        'user': user,
        'registration_fee': user.registration_payment_amount
    })

@admin_required
def verify_registration_payment(request, user_id):
    """View for admins to verify registration payments"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
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
        
        return redirect('accounts:pending_registrations')
    
    return render(request, 'accounts/verify_registration_payment.html', {
        'user': user
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
