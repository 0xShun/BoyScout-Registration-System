#!/usr/bin/env python
"""
Manual helper to verify Twilio SMS using direct API calls.
Reads credentials from environment variables. See .env.example
"""
import requests
import base64
import os

def post_message(data):
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    credentials = f'{account_sid}:{auth_token}'
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    return requests.post(url, headers=headers, data=data)

def main():
    to_phone = os.environ.get('TEST_SMS_TO', '')
    messaging_service_sid = os.environ.get('TWILIO_MESSAGING_SERVICE_SID', '')
    twilio_phone = os.environ.get('TWILIO_PHONE_NUMBER', '')

    print('Testing Twilio API Direct...')
    r1 = post_message({'To': to_phone, 'From': twilio_phone, 'Body': 'ScoutConnect Direct SMS Test'})
    print('Status:', r1.status_code, r1.text[:200])

    print('Testing Twilio API with Messaging Service...')
    r2 = post_message({'To': to_phone, 'MessagingServiceSid': messaging_service_sid, 'Body': 'ScoutConnect MS Test'})
    print('Status:', r2.status_code, r2.text[:200])

if __name__ == '__main__':
    main()
