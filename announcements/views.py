from django.shortcuts import render, redirect, get_object_or_404
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

@login_required
def announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    # Mark as read for this user
    announcement.read_by.add(request.user)
    return render(request, 'announcements/announcement_detail.html', {'announcement': announcement})

@admin_required
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.save()
            form.save_m2m()
            
            # Send to all active users
            recipients = User.objects.filter(is_active=True)
            announcement.recipients.set(recipients)
            
            # Prepare email content
            email_subject = f"New Announcement: {announcement.title}"
            email_message = f"{announcement.title}\n\n{announcement.message}"
            
            # Send notifications to all active users
            for user in recipients:
                # Send email notification
                if user.email:
                    NotificationService.send_email(email_subject, email_message, [user.email])
                
                # Send in-app notification
                send_realtime_notification(user.id, f"New announcement: {announcement.title}", type='announcement')
            
            messages.success(request, 'Announcement created and sent to all active users.')
            return redirect('announcements:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_create.html', {'form': form})

@login_required
def announcement_mark_read(request, pk):
    announcement = Announcement.objects.get(pk=pk)
    announcement.read_by.add(request.user)
    return redirect('announcements:announcement_list')
