#!/usr/bin/env python
"""
DEPRECATED: This helper is intended for local manual testing only.
It now reads credentials from environment variables. See .env.example.
"""

import requests
import base64
import json
import os

def test_twilio_api_sms():
    """Test SMS using direct Twilio API calls"""
    print("📱 Testing Twilio API Direct SMS...")
    
    # Twilio credentials from environment
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    twilio_phone = os.environ.get('TWILIO_PHONE_NUMBER', '')
    
    # Your phone number
    to_phone = os.environ.get('TEST_SMS_TO', '')
    
    # API endpoint
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    
    # Prepare authentication
    credentials = f'{account_sid}:{auth_token}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Headers
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Message data
    data = {
        'To': to_phone,
        'From': twilio_phone,
        'Body': 'ScoutConnect SMS Test: Your Twilio API configuration is working! 🎉'
    }
    
    try:
        print(f"📞 Sending SMS to: {to_phone}")
        print(f"📞 From: {twilio_phone}")
        print(f"📝 Message: {data['Body']}")
        print(f"🔗 API URL: {url}")
        
        # Make the API call
        response = requests.post(url, headers=headers, data=data)
        
        print(f"\n📊 Response Status Code: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            # Success
            result = response.json()
            print("✅ SMS sent successfully!")
            print(f"📱 Message SID: {result.get('sid', 'N/A')}")
            print(f"📱 Status: {result.get('status', 'N/A')}")
            print(f"📱 Price: {result.get('price', 'N/A')}")
            print(f"📱 Price Unit: {result.get('price_unit', 'N/A')}")
            return True
        else:
            # Error
            print("❌ SMS sending failed!")
            print(f"📊 Error Response: {response.text}")
            
            try:
                error_data = response.json()
                print(f"📊 Error Code: {error_data.get('code', 'N/A')}")
                print(f"📊 Error Message: {error_data.get('message', 'N/A')}")
            except:
                print(f"📊 Raw Error: {response.text}")
            
            return False
            
    except Exception as e:
        print(f"❌ API call failed with error: {str(e)}")
        return False

def test_twilio_api_with_messaging_service():
    """Test SMS using Twilio Messaging Service (like your curl example)"""
    print("\n📱 Testing Twilio API with Messaging Service...")
    
    # Your Twilio credentials
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    messaging_service_sid = os.environ.get('TWILIO_MESSAGING_SERVICE_SID', '')
    
    # Your phone number
    to_phone = os.environ.get('TEST_SMS_TO', '')
    
    # API endpoint
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    
    # Prepare authentication
    credentials = f'{account_sid}:{auth_token}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Headers
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Message data (using Messaging Service like your curl example)
    data = {
        'To': to_phone,
        'MessagingServiceSid': messaging_service_sid,
        'Body': 'ScoutConnect SMS Test via Messaging Service! 🚀'
    }
    
    try:
        print(f"📞 Sending SMS to: {to_phone}")
        print(f"📞 Using Messaging Service: {messaging_service_sid}")
        print(f"📝 Message: {data['Body']}")
        
        # Make the API call
        response = requests.post(url, headers=headers, data=data)
        
        print(f"\n📊 Response Status Code: {response.status_code}")
        
        if response.status_code == 201:
            # Success
            result = response.json()
            print("✅ SMS sent successfully via Messaging Service!")
            print(f"📱 Message SID: {result.get('sid', 'N/A')}")
            print(f"📱 Status: {result.get('status', 'N/A')}")
            return True
        else:
            # Error
            print("❌ SMS sending failed!")
            print(f"📊 Error Response: {response.text}")
            
            try:
                error_data = response.json()
                print(f"📊 Error Code: {error_data.get('code', 'N/A')}")
                print(f"📊 Error Message: {error_data.get('message', 'N/A')}")
            except:
                print(f"📊 Raw Error: {response.text}")
            
            return False
            
    except Exception as e:
        print(f"❌ API call failed with error: {str(e)}")
        return False

def test_curl_equivalent():
    """Test the exact equivalent of your curl command"""
    print("\n📱 Testing Exact Curl Equivalent...")
    
    # Your Twilio credentials
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    messaging_service_sid = os.environ.get('TWILIO_MESSAGING_SERVICE_SID', '')
    
    # Your phone number
    to_phone = os.environ.get('TEST_SMS_TO', '')
    
    # API endpoint
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    
    # Prepare authentication
    credentials = f'{account_sid}:{auth_token}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Headers
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Message data (exact same as your curl command)
    data = {
        'To': to_phone,
        'MessagingServiceSid': messaging_service_sid,
        'Body': 'Ahoy 👋'
    }
    
    try:
        print(f"📞 Sending SMS to: {to_phone}")
        print(f"📞 Using Messaging Service: {messaging_service_sid}")
        print(f"📝 Message: {data['Body']}")
        
        # Make the API call
        response = requests.post(url, headers=headers, data=data)
        
        print(f"\n📊 Response Status Code: {response.status_code}")
        
        if response.status_code == 201:
            # Success
            result = response.json()
            print("✅ SMS sent successfully (curl equivalent)!")
            print(f"📱 Message SID: {result.get('sid', 'N/A')}")
            print(f"📱 Status: {result.get('status', 'N/A')}")
            return True
        else:
            # Error
            print("❌ SMS sending failed!")
            print(f"📊 Error Response: {response.text}")
            
            try:
                error_data = response.json()
                print(f"📊 Error Code: {error_data.get('code', 'N/A')}")
                print(f"📊 Error Message: {error_data.get('message', 'N/A')}")
            except:
                print(f"📊 Raw Error: {response.text}")
            
            return False
            
    except Exception as e:
        print(f"❌ API call failed with error: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 Twilio API Direct Test")
    print("=" * 50)
    
    # Test 1: Direct API call with phone number
    test_twilio_api_sms()
    
    # Test 2: API call with Messaging Service
    test_twilio_api_with_messaging_service()
    
    # Test 3: Exact curl equivalent
    test_curl_equivalent()
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("1. Check your phone for SMS messages")
    print("2. Compare results with your curl command")
    print("3. If any test works, we know the API is accessible")

if __name__ == "__main__":
    main() 