from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm, UserEditForm, CustomLoginForm, RoleManagementForm
from .models import User
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
        'is_active_member': is_active_member,
    })

@login_required
def scout_dashboard(request):
    if not request.user.is_scout():
        return redirect('accounts:admin_dashboard')

    # Check if the scout has paid and is an active member
    is_active_member = Payment.objects.filter(user=request.user, status='verified').exists()

    return render(request, 'accounts/scout_dashboard.html', {'is_active_member': is_active_member})

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
    return render(request, 'accounts/member_detail.html', {'member': user})

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
        form = UserEditForm(instance=user, user=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
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
