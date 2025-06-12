# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ''  # Add your email
EMAIL_HOST_PASSWORD = ''  # Add your email password
DEFAULT_FROM_EMAIL = 'ScoutConnect <noreply@scoutconnect.com>'

# Twilio Configuration for SMS
TWILIO_ACCOUNT_SID = ''  # Add your Twilio Account SID
TWILIO_AUTH_TOKEN = ''   # Add your Twilio Auth Token
TWILIO_PHONE_NUMBER = '' # Add your Twilio phone number 