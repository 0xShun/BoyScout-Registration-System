from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import models
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

# Add a model for logging simulated SMS
class SimulatedSMSLog(models.Model):
    to_number = models.CharField(max_length=20)
    message = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"SMS to {self.to_number} at {self.sent_at}"

class NotificationService:
    @staticmethod
    def send_email(subject, message, recipient_list):
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False

    @staticmethod
    def send_sms(to_number, message):
        from django.conf import settings
        # Simulate SMS if Twilio is not configured
        if not all([
            getattr(settings, 'TWILIO_ACCOUNT_SID', None),
            getattr(settings, 'TWILIO_AUTH_TOKEN', None),
            getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        ]):
            print(f"[SIMULATED SMS] To: {to_number} | Message: {message}")
            SimulatedSMSLog.objects.create(to_number=to_number, message=message)
            return True
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_number
            )
            return True
        except Exception as e:
            print(f"SMS sending failed: {str(e)}")
            return False

def send_realtime_notification(user_id, message, type='info'):
    # Create a Notification record
    Notification.objects.create(user_id=user_id, message=message, type=type)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'send_notification',
            'message': message,
            'type': type,
        }
    ) 