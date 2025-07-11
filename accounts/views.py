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
    return render(request, 'accounts/scout_dashboard.html', {
        'is_active_member': is_active_member,
        'profile_incomplete': profile_incomplete,
        'incomplete_fields': incomplete_fields,
    })

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.rank = 'scout'
            user.is_active = True
            user.save()
            
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('accounts:login')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@admin_required
def member_list(request):
    query = request.GET.get('q', '')
    filter_rank = request.GET.get('rank', '')
    members = User.objects.all()
    if query:
        members = members.filter(models.Q(username__icontains=query) | models.Q(email__icontains=query) | models.Q(first_name__icontains=query) | models.Q(last_name__icontains=query))
    if filter_rank:
        members = members.filter(rank=filter_rank)
    member_balances = {}
    monthly_due = 100
    for member in members:
        payments = member.payments.filter(status='verified')
        total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or 0
        join_date = member.date_joined.date() if member.date_joined else date.today()
        today = date.today()
        months = (today.year - join_date.year) * 12 + (today.month - join_date.month) + 1
        total_dues = months * monthly_due
        balance = total_paid - total_dues
        member_balances[member.pk] = {
            'total_paid': total_paid,
            'total_dues': total_dues,
            'balance': balance,
        }
    paginator = Paginator(members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/member_list.html', {
        'members': members,
        'member_balances': member_balances,
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
