from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification
import logging

logger = logging.getLogger(__name__)

# Add a model for logging simulated SMS
class SimulatedSMSLog(models.Model):
    to_number = models.CharField(max_length=20)
    message = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"SMS to {self.to_number} at {self.sent_at}"

class NotificationService:
    @staticmethod
    def send_email(subject, message, recipient_list, html_template=None, context=None):
        """
        Send email with optional HTML template support.
        
        Args:
            subject: Email subject line
            message: Plain text message (fallback if no HTML template)
            recipient_list: List of recipient email addresses
            html_template: (Optional) Path to HTML email template
            context: (Optional) Dictionary of variables for template rendering
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if html_template and context:
                # Add current year to context for footer
                context['current_year'] = timezone.now().year
                
                # Render HTML from template
                html_content = render_to_string(html_template, context)
                
                # Create email with both plain text and HTML
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list,
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)
            else:
                # Send plain text email
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=False,
                )
            
            logger.info(f"Email sent successfully to {len(recipient_list)} recipient(s)")
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            print(f"Email sending failed: {str(e)}")
            return False
    
    @staticmethod
    def send_html_email(subject, recipient_list, html_template, context, plain_text_message=None):
        """
        Send email with HTML template and optional plain text fallback.
        
        Args:
            subject: Email subject line
            recipient_list: List of recipient email addresses
            html_template: Path to HTML email template
            context: Dictionary of variables for template rendering
            plain_text_message: (Optional) Plain text fallback message
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Use plain_text_message or extract from subject for fallback
        fallback_message = plain_text_message or f"View this email in an HTML-compatible email client.\n\nSubject: {subject}"
        
        return NotificationService.send_email(
            subject=subject,
            message=fallback_message,
            recipient_list=recipient_list,
            html_template=html_template,
            context=context
        )

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