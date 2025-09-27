#!/usr/bin/env python
"""Manual helper to send test email and SMS via configured backends."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from notifications.services import NotificationService

def main():
    email_to = os.environ.get('TEST_EMAIL_TO', '')
    sms_to = os.environ.get('TEST_SMS_TO', '')

    if email_to:
        NotificationService.send_email(
            'ScoutConnect - Email Test',
            'This is a test email from ScoutConnect.',
            [email_to],
        )
        print('Email sent to', email_to)
    else:
        print('TEST_EMAIL_TO not set; skipping email test')

    if sms_to:
        NotificationService.send_sms(sms_to, 'ScoutConnect SMS test: Working!')
        print('SMS sent to', sms_to)
    else:
        print('TEST_SMS_TO not set; skipping SMS test')

if __name__ == '__main__':
    main()
