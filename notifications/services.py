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
    def format_phone_number(phone_number):
        """Format phone number to international format for Twilio"""
        if not phone_number:
            return None
        try:
            from phonenumber_field.phonenumber import PhoneNumber
            # If it's already a PhoneNumber instance, format directly
            if isinstance(phone_number, PhoneNumber):
                return phone_number.as_e164
        except Exception:
            pass

        # Fallback: simple PH normalization
        digits_only = ''.join(filter(str.isdigit, str(phone_number)))
        if len(digits_only) == 11 and digits_only.startswith('09'):
            return f"+63{digits_only[1:]}"
        if str(phone_number).startswith('+'):
            return str(phone_number)
        if len(digits_only) == 10 and digits_only.startswith('9'):
            return f"+63{digits_only}"
        return str(phone_number)

    @staticmethod
    def send_sms(to_number, message):
        from django.conf import settings
        
        # Format phone number to international format
        formatted_number = NotificationService.format_phone_number(to_number)
        
        # Simulate SMS if Twilio is not configured
        if not all([
            getattr(settings, 'TWILIO_ACCOUNT_SID', None),
            getattr(settings, 'TWILIO_AUTH_TOKEN', None),
        ]):
            print(f"[SIMULATED SMS] To: {formatted_number} | Message: {message}")
            SimulatedSMSLog.objects.create(to_number=formatted_number, message=message)
            return True
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Use Messaging Service if available, otherwise use phone number
            if hasattr(settings, 'TWILIO_MESSAGING_SERVICE_SID') and settings.TWILIO_MESSAGING_SERVICE_SID:
                client.messages.create(
                    body=message,
                    messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
                    to=formatted_number
                )
            else:
                client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=formatted_number
                )
            return True
        except Exception as e:
            print(f"SMS sending failed: {str(e)}")
            return False

def send_realtime_notification(user_id, message, type='info', notification_type=None):
    """Send an in-app realtime notification.

    Backwards-compatible: callers may pass either `type` or the older
    `notification_type` keyword. The latter takes precedence when provided.
    """
    # Determine the effective notification type (accept legacy kwarg)
    effective_type = notification_type if notification_type is not None else type

    # Create a Notification record
    Notification.objects.create(user_id=user_id, message=message, type=effective_type)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'send_notification',
            'message': message,
            'type': effective_type,
        }
    )