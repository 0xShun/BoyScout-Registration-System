from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AnnouncementForm
from .models import Announcement
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
import logging

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
            announcement = form.save()
            
            # Handle notifications
            send_email = form.cleaned_data.get('send_email')
            send_sms = form.cleaned_data.get('send_sms')

            if send_email or send_sms:
                recipients = announcement.recipients.all()
                if not recipients:
                    recipients = User.objects.all() # Or some other logic for all users

                for user in recipients:
                    if send_email and user.email:
                        # In a real app, this would be an asynchronous task
                        send_mail(
                            announcement.title,
                            announcement.message,
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email],
                            fail_silently=False,
                        )
                        logger.info(f"Email sent to {user.email} for announcement: {announcement.title}")

                    if send_sms and hasattr(user, 'phone_number') and user.phone_number:
                        # SMS sending logic (simulation)
                        logger.info(f"SMS sent to {user.phone_number} for announcement: {announcement.title}")
                        messages.info(request, f"Simulated SMS sent to {user.username}.")

            messages.success(request, 'Announcement created.')
            return redirect('announcements:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_create.html', {'form': form})

@login_required
def announcement_mark_read(request, pk):
    announcement = Announcement.objects.get(pk=pk)
    announcement.read_by.add(request.user)
    return redirect('announcement_list')
