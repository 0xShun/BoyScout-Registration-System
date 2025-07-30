from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AnnouncementForm
from .models import Announcement
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
import logging
from notifications.services import NotificationService, send_realtime_notification

# Get an instance of a logger
logger = logging.getLogger(__name__)

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
def announcement_list(request):
    announcements = Announcement.objects.all().order_by('-date_posted')
    return render(request, 'announcements/announcement_list.html', {'announcements': announcements})

@admin_required
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.save()
            form.save_m2m()
            # Determine recipients
            selected_groups = form.cleaned_data.get('groups')
            if selected_groups and selected_groups.exists():
                recipients = User.objects.filter(groups_membership__in=selected_groups).distinct()
            else:
                recipients = announcement.recipients.all()
                if not recipients:
                    recipients = User.objects.all()
            announcement.recipients.set(recipients)
            # Send notifications
            for user in recipients:
                if hasattr(user, 'phone_number') and user.phone_number:
                    NotificationService.send_sms(user.phone_number, f"[Announcement] {announcement.title}: {announcement.message}")
                send_realtime_notification(user.id, f"New announcement: {announcement.title}", type='announcement')
            messages.success(request, 'Announcement created and sent to selected recipients.')
            return redirect('announcements:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_create.html', {'form': form})

@login_required
def announcement_mark_read(request, pk):
    announcement = Announcement.objects.get(pk=pk)
    announcement.read_by.add(request.user)
    return redirect('announcements:announcement_list')
