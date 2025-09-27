from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AuditLog
from accounts.models import User
from payments.models import Payment
from announcements.models import Announcement
from ipware import get_client_ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip, _ = get_client_ip(request)
    AuditLog.objects.create(
        user=user,
        action='user_logged_in',
        ip_address=ip,
        details=f"User {user.username} logged in."
    )

@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            user=instance,
            action='user_registered',
            details=f"New user {instance.username} registered."
        )

@receiver(post_save, sender=Payment)
def log_payment_action(sender, instance, created, **kwargs):
    action = 'payment_submitted' if created else 'payment_updated'
    details = f"Payment {instance.pk} was {action.replace('_', ' ')}."
    if instance.status in ['verified', 'rejected']:
        action = f"payment_{instance.status}"
        details = f"Payment {instance.pk} was {instance.status} by {instance.verified_by}."
    
    AuditLog.objects.create(
        user=instance.user,
        action=action,
        details=details
    )

@receiver(post_save, sender=Announcement)
def log_announcement_creation(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            action='announcement_created',
            details=f"Announcement '{instance.title}' was created."
        ) 