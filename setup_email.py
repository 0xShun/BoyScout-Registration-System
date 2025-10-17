#!/usr/bin/env python3
"""
Quick Email Setup for ScoutConnect
This script helps you configure email notifications quickly.
"""

import os
import sys

def print_header():
    print("\n" + "="*60)
    print("📧 ScoutConnect Email Setup")
    print("="*60 + "\n")

def print_option(num, title, description):
    print(f"\n{num}. {title}")
    print(f"   {description}")

def setup_gmail():
    print("\n" + "="*60)
    print("📧 Gmail SMTP Setup")
    print("="*60)
    print("\n📋 Steps:")
    print("1. Go to: https://myaccount.google.com/apppasswords")
    print("2. Generate an App Password for 'Mail'")
    print("3. Copy the 16-character password (remove spaces)")
    print("\n")
    
    email = input("Enter your Gmail address: ").strip()
    print("\nNow enter the 16-character App Password (no spaces):")
    password = input("App Password: ").strip().replace(" ", "")
    
    return {
        'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'EMAIL_HOST': 'smtp.gmail.com',
        'EMAIL_PORT': '587',
        'EMAIL_USE_TLS': 'True',
        'EMAIL_HOST_USER': email,
        'EMAIL_HOST_PASSWORD': password,
        'DEFAULT_FROM_EMAIL': f'ScoutConnect <{email}>'
    }

def setup_sendgrid():
    print("\n" + "="*60)
    print("🚀 SendGrid Setup")
    print("="*60)
    print("\n📋 Steps:")
    print("1. Go to: https://app.sendgrid.com/settings/api_keys")
    print("2. Create API Key with 'Full Access' or 'Mail Send' permission")
    print("3. Copy the API key (starts with SG.)")
    print("4. Verify sender at: https://app.sendgrid.com/settings/sender_auth/senders")
    print("\n")
    
    api_key = input("Enter your SendGrid API Key: ").strip()
    from_email = input("Enter your verified sender email: ").strip()
    
    return {
        'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'EMAIL_HOST': 'smtp.sendgrid.net',
        'EMAIL_PORT': '587',
        'EMAIL_USE_TLS': 'True',
        'EMAIL_HOST_USER': 'apikey',
        'EMAIL_HOST_PASSWORD': api_key,
        'DEFAULT_FROM_EMAIL': f'ScoutConnect <{from_email}>'
    }

def setup_console():
    print("\n✅ Console backend selected - emails will print to terminal")
    return {
        'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend'
    }

def update_env_file(config):
    env_path = '.env'
    
    # Read current .env
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add email settings
    email_keys = ['EMAIL_BACKEND', 'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS', 
                  'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL']
    
    # Remove old email settings
    new_lines = [line for line in lines if not any(line.startswith(key + '=') for key in email_keys)]
    
    # Add new settings
    for key, value in config.items():
        new_lines.append(f"{key}={value}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("\n✅ .env file updated successfully!")

def test_email(test_email_address):
    print("\n" + "="*60)
    print("🧪 Testing Email Configuration")
    print("="*60)
    
    try:
        # Setup Django
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
        django.setup()
        
        from notifications.services import NotificationService
        
        print(f"\nSending test email to: {test_email_address}")
        
        result = NotificationService.send_email(
            subject='✅ ScoutConnect Email Test',
            message='Congratulations! Your email notifications are working correctly.\n\nYou can now receive:\n• Payment confirmations\n• Registration notifications\n• System alerts',
            recipient_list=[test_email_address]
        )
        
        if result:
            print("\n✅ SUCCESS! Test email sent successfully!")
            print(f"📬 Check your inbox: {test_email_address}")
            print("   (Don't forget to check spam folder)")
            return True
        else:
            print("\n❌ FAILED! Email could not be sent.")
            print("Check the error message above for details.")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure Django server is not running")
        print("2. Verify your credentials are correct")
        print("3. For Gmail: Use App Password, not regular password")
        print("4. Check EMAIL_SETUP_GUIDE.md for detailed help")
        return False

def main():
    print_header()
    
    print("Choose your email provider:")
    print_option(1, "Gmail SMTP", "✅ Recommended for testing (Free, 500 emails/day)")
    print_option(2, "SendGrid", "🚀 Recommended for production (Scalable)")
    print_option(3, "Console Backend", "🧪 For local testing only (no real emails)")
    print_option(4, "Skip", "Configure manually later")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        config = setup_gmail()
    elif choice == '2':
        config = setup_sendgrid()
    elif choice == '3':
        config = setup_console()
    elif choice == '4':
        print("\n📝 See EMAIL_SETUP_GUIDE.md for manual setup instructions")
        return
    else:
        print("\n❌ Invalid choice. Exiting.")
        return
    
    # Update .env file
    update_env_file(config)
    
    # Ask if user wants to test
    if choice != '3':  # Not console backend
        print("\n" + "="*60)
        test_choice = input("\nWould you like to test email now? (y/n): ").strip().lower()
        
        if test_choice == 'y':
            test_email_address = input("Enter email address to send test: ").strip()
            if test_email_address:
                test_email(test_email_address)
    
    print("\n" + "="*60)
    print("✅ Email Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Restart your Django server (if running)")
    print("2. Test payment flow: .venv/bin/python test_registration_flow.py --type single")
    print("3. Complete payment and check for email notifications")
    print("\n📖 For troubleshooting, see: EMAIL_SETUP_GUIDE.md")
    print("\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
