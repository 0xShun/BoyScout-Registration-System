def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

from django.urls import reverse
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

from django.urls import reverse
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

@admin_required
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully.')
        return redirect('announcements:announcement_list')
    return render(request, 'announcements/announcement_confirm_delete.html', {'announcement': announcement})

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
            email_recipients = []
            for user in recipients:
                # Send SMS if phone number exists
                if hasattr(user, 'phone_number') and user.phone_number:
                    NotificationService.send_sms(user.phone_number, f"[Announcement] {announcement.title}: {announcement.message}")
                
                # Send realtime notification
                send_realtime_notification(user.id, f"New announcement: {announcement.title}", type='announcement')
                
                # Collect email addresses for bulk email
                if user.email:
                    email_recipients.append(user.email)
            
            # Send HTML email to all recipients
            if email_recipients:
                try:
                    subject = f"📢 ScoutConnect Announcement: {announcement.title}"
                    plain_text_message = f"""
Dear ScoutConnect Member,

{announcement.message}

Posted on: {announcement.date_posted.strftime('%B %d, %Y at %I:%M %p')}

Best regards,
The ScoutConnect Team

---
This is an automated message from ScoutConnect. Please do not reply to this email.
                    """.strip()
                    
                    # Build dashboard URL
                    from django.urls import reverse
                    dashboard_url = f"{settings.SITE_URL}{reverse('announcements:announcement_list')}" if hasattr(settings, 'SITE_URL') else "#"
                    
                    context = {
                        'announcement': announcement,
                        'recipient_name': 'Member',
                        'dashboard_url': dashboard_url,
                    }
                    
                    NotificationService.send_html_email(
                        subject=subject,
                        recipient_list=email_recipients,
                        html_template='notifications/email/announcement.html',
                        context=context,
                        plain_text_message=plain_text_message
                    )
                    logger.info(f"Announcement email sent to {len(email_recipients)} recipients")
                except Exception as e:
                    logger.error(f"Failed to send announcement emails: {str(e)}")
                    messages.warning(request, f'Announcement created but email sending failed: {str(e)}')
            
            messages.success(request, f'Announcement created and sent to {len(recipients)} recipients via SMS, email, and notifications.')
            return redirect('announcements:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_create.html', {'form': form})

@login_required
def announcement_mark_read(request, pk):
    announcement = Announcement.objects.get(pk=pk)
    announcement.read_by.add(request.user)
    return redirect('announcements:announcement_list')
