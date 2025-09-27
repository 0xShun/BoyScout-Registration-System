#!/usr/bin/env python
"""
Test script to verify email and SMS notifications are working
Run this script to test your configuration before using in the main application
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from notifications.services import NotificationService
from accounts.models import User

def test_email_configuration():
    """Test email configuration"""
    print("📧 Testing Email Configuration...")
    
    try:
        # Test email to a test recipient from environment
        test_email = os.environ.get('TEST_EMAIL_TO', '')
        
        subject = "ScoutConnect - Email Test"
        message = """
        Hello!
        
        This is a test email from ScoutConnect to verify that your email configuration is working properly.
        
        If you receive this email, your Gmail SMTP configuration is working correctly.
        
        Best regards,
        ScoutConnect System
        """
        
        success = NotificationService.send_email(subject, message, [test_email])
        
        if success:
            print("✅ Email sent successfully!")
            print(f"   Check your inbox: {test_email}")
        else:
            print("❌ Email sending failed!")
            
    except Exception as e:
        print(f"❌ Email test failed with error: {str(e)}")

def test_sms_configuration():
    """Test SMS configuration"""
    print("\n📱 Testing SMS Configuration...")
    
    try:
        # Test SMS to your phone number from environment
        test_phone = os.environ.get('TEST_SMS_TO', '')
        
        message = "ScoutConnect SMS test: Your SMS configuration is working! 🎉"
        
        success = NotificationService.send_sms(test_phone, message)
        
        if success:
            print("✅ SMS sent successfully!")
            print(f"   Check your phone: {test_phone}")
        else:
            print("❌ SMS sending failed!")
            
    except Exception as e:
        print(f"❌ SMS test failed with error: {str(e)}")

def test_with_existing_users():
    """Test notifications with existing users in the database"""
    print("\n👥 Testing with Existing Users...")
    
    try:
        # Get first few active users
        users = User.objects.filter(is_active=True)[:3]
        
        if not users.exists():
            print("⚠️  No active users found in database. Skipping user notification test.")
            return
        
        print(f"Found {users.count()} active users for testing...")
        
        # Test email to existing users
        subject = "ScoutConnect - System Test"
        message = """
        Hello Scout!
        
        This is a test notification from ScoutConnect to verify that the notification system is working properly.
        
        If you receive this message, the system is ready for production use.
        
        Best regards,
        ScoutConnect Team
        """
        
        for user in users:
            if user.email:
                print(f"   Sending email to: {user.email}")
                NotificationService.send_email(subject, message, [user.email])
            
            if user.phone_number:
                print(f"   Sending SMS to: {user.phone_number}")
                NotificationService.send_sms(user.phone_number, f"ScoutConnect test: Hello {user.first_name}! System is working. 🎉")
        
        print("✅ User notification test completed!")
        
    except Exception as e:
        print(f"❌ User notification test failed: {str(e)}")

def main():
    """Main test function"""
    print("🚀 ScoutConnect Notification System Test")
    print("=" * 50)
    
    # Test basic configurations
    test_email_configuration()
    test_sms_configuration()
    
    # Test with existing users
    test_with_existing_users()
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("1. Check your email inbox for test emails")
    print("2. Check your phone for test SMS messages")
    print("3. If both work, your notification system is ready!")
    print("4. If there are errors, check your configuration in settings.py")

if __name__ == "__main__":
    main() 