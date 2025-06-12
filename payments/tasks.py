from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Payment
from accounts.models import User

def send_payment_reminders():
    # Get users with pending payments
    pending_payments = Payment.objects.filter(
        status='pending',
        date__lte=timezone.now() - timedelta(days=3)  # Remind after 3 days
    ).select_related('user')

    for payment in pending_payments:
        # Send reminder to user
        send_mail(
            'Payment Reminder',
            f'Your payment of {payment.amount} is still pending. Please submit your payment proof soon.',
            settings.DEFAULT_FROM_EMAIL,
            [payment.user.email],
            fail_silently=True,
        )

def send_payment_expiry_notifications():
    # Get payments expiring in 24 hours
    expiring_payments = Payment.objects.filter(
        status='pending',
        expiry_date__lte=timezone.now() + timedelta(days=1),
        expiry_date__gt=timezone.now()
    ).select_related('user')

    for payment in expiring_payments:
        # Send expiry notification to user
        send_mail(
            'Payment Expiring Soon',
            f'Your payment of {payment.amount} will expire in 24 hours. Please submit your payment proof soon.',
            settings.DEFAULT_FROM_EMAIL,
            [payment.user.email],
            fail_silently=True,
        )

def send_monthly_payment_reminders():
    # Get all active users
    active_users = User.objects.filter(is_active=True)
    
    for user in active_users:
        # Check if user has any payments in the last month
        last_month = timezone.now() - timedelta(days=30)
        recent_payments = Payment.objects.filter(
            user=user,
            date__gte=last_month,
            status='verified'
        ).exists()
        
        if not recent_payments:
            # Send monthly reminder
            send_mail(
                'Monthly Payment Reminder',
                'This is a reminder to submit your monthly payment.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            ) 