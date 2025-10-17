# 🧪 PayMongo Integration Testing Guide

## Overview
This guide provides step-by-step instructions for testing the PayMongo QR PH payment integration in TEST mode before going to production.

---

## 📋 Prerequisites

### Required Tools
- [x] Django server running locally
- [x] ngrok installed (`brew install ngrok` or download from https://ngrok.com)
- [x] PayMongo TEST API keys configured in `.env`
- [x] GCash, PayMaya, or GrabPay test account (or real account for test transactions)

### Environment Setup
```bash
# Verify .env has TEST keys
cat .env | grep PAYMONGO
# Should show:
# PAYMONGO_PUBLIC_KEY=pk_test_...
# PAYMONGO_SECRET_KEY=sk_test_...
# PAYMONGO_WEBHOOK_SECRET=whsk_...
```

---

## 🚀 Phase 1: Local Server Setup

### Step 1: Start Django Server
```bash
cd /home/shun/Documents/boyscout_system
source .venv/bin/activate
python3 manage.py runserver
```

**Expected Output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 5.2.7, using settings 'boyscout_system.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Step 2: Start ngrok
In a **new terminal**:
```bash
ngrok http 8000
```

**Expected Output:**
```
ngrok                                                                                                                                                          
                                                                                                                                                               
Session Status                online                                                                                                                           
Account                       your-account (Plan: Free)                                                                                                        
Version                       3.x.x                                                                                                                            
Region                        Asia Pacific (ap)                                                                                                                
Latency                       -                                                                                                                                
Web Interface                 http://127.0.0.1:4040                                                                                                            
Forwarding                    https://xxxx-xxx-xxx-xxx.ngrok-free.app -> http://localhost:8000
```

**IMPORTANT:** Copy the `https://` URL (e.g., `https://xxxx-xxx-xxx-xxx.ngrok-free.app`)

### Step 3: Update PayMongo Webhook URL
1. Go to https://dashboard.paymongo.com
2. Navigate to **Developers** → **Webhooks**
3. Find your webhook (or create new one)
4. Update URL to: `https://your-ngrok-url.ngrok-free.app/payments/webhook/`
5. Ensure events are selected:
   - `source.chargeable`
   - `payment.paid`
   - `payment.failed`
6. Save changes

---

## 🧪 Phase 2: Test User Registration Flow

### Test Case 1: New User Registration with Payment

#### Steps:
1. Open browser to: `http://localhost:8000/accounts/register/`
2. Fill in registration form:
   - Username: `testuser001`
   - Email: `testuser001@example.com`
   - Password: `TestPass123!`
   - First Name: `Test`
   - Last Name: `User`
   - Phone: `+639171234567`
   - Date of Birth: `2000-01-01`
   - Address: `123 Test St, Test City`
   - Registration Fee: `500` (default)
3. Click "Register & Proceed to Payment"

#### Expected Results:
- ✅ User account created in database
- ✅ Registration payment record created (status: 'pending')
- ✅ Redirected to PayMongo checkout page
- ✅ Checkout page shows:
  - Amount: ₱500.00
  - Payment options: GCash, PayMaya, GrabPay
  - QR code displayed

#### What to Check:
```bash
# In Django shell
python3 manage.py shell

from accounts.models import User, RegistrationPayment
user = User.objects.get(username='testuser001')
print(f"User Status: {user.registration_status}")  # Should be 'pending'
print(f"User Active: {user.is_active}")  # Should be True

reg_payment = RegistrationPayment.objects.filter(user=user).first()
print(f"Payment Status: {reg_payment.status}")  # Should be 'pending'
print(f"PayMongo Source ID: {reg_payment.paymongo_source_id}")  # Should have value
```

### Test Case 2: Complete Payment via PayMongo

#### Steps:
1. On PayMongo checkout page, click payment method (e.g., GCash)
2. Scan QR code with GCash app
3. Complete payment in app
4. Return to browser

#### Expected Results:
- ✅ PayMongo webhook fired to your ngrok URL
- ✅ Django server receives webhook
- ✅ Payment status updated to 'verified'
- ✅ User account activated
- ✅ Membership expiry set (1 year from now)
- ✅ Email notification sent

#### What to Check:

**Django Server Logs:**
```
POST /payments/webhook/ 200
Processing payment.paid for payment: pay_xxx...
Registration payment 1 confirmed as paid
User 1 registration activated
```

**Django Shell:**
```python
python3 manage.py shell

from accounts.models import User, RegistrationPayment
user = User.objects.get(username='testuser001')
print(f"User Status: {user.registration_status}")  # Should be 'active'
print(f"User Active: {user.is_active}")  # Should be True
print(f"Membership Expiry: {user.membership_expiry}")  # Should be ~1 year from now

reg_payment = RegistrationPayment.objects.filter(user=user).first()
print(f"Payment Status: {reg_payment.status}")  # Should be 'verified'
print(f"PayMongo Payment ID: {reg_payment.paymongo_payment_id}")  # Should have value
```

**PayMongo Dashboard:**
- Go to **Payments** tab
- Verify payment appears with status "Paid"
- Check **Webhooks** tab → Delivery logs
- Verify webhook delivery status is "Successful"

### Test Case 3: Payment Cancellation

#### Steps:
1. Register new user: `testuser002@example.com`
2. Get redirected to PayMongo checkout
3. Click "Cancel" or close the page
4. Should be redirected to payment failed page

#### Expected Results:
- ✅ User account created but not activated
- ✅ Payment status remains 'pending'
- ✅ Failed page displays with retry option

---

## 💳 Phase 3: Test Regular Payment Submission

### Test Case 4: Existing User Makes Payment

#### Steps:
1. Login as existing user: `http://localhost:8000/accounts/login/`
2. Navigate to: `http://localhost:8000/payments/submit/`
3. Enter amount: `100`
4. Click "Pay with GCash/PayMaya/GrabPay"
5. Complete payment via QR code

#### Expected Results:
- ✅ Payment record created with status 'pending'
- ✅ Redirected to PayMongo checkout
- ✅ After payment, webhook updates status to 'verified'
- ✅ Payment appears in user's payment history
- ✅ Admin can see payment in admin panel

#### What to Check:
```python
python3 manage.py shell

from payments.models import Payment
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.get(username='testuser001')
payment = Payment.objects.filter(user=user, payment_type='general').first()
print(f"Amount: {payment.amount}")
print(f"Status: {payment.status}")  # Should be 'verified'
print(f"Payment Method: {payment.payment_method}")  # Should be 'qr_ph'
print(f"PayMongo ID: {payment.paymongo_payment_id}")
```

---

## 🔍 Phase 4: Webhook Testing

### Test Case 5: Manual Webhook Test

#### Create Test Webhook Event:
```python
# test_manual_webhook.py
import requests
import json
import os

WEBHOOK_URL = "http://localhost:8000/payments/webhook/"
WEBHOOK_SECRET = os.environ.get('PAYMONGO_WEBHOOK_SECRET')

# Sample payment.paid event
test_event = {
    "data": {
        "id": "evt_test_123",
        "type": "event",
        "attributes": {
            "type": "payment.paid",
            "livemode": False,
            "data": {
                "id": "pay_test_123",
                "type": "payment",
                "attributes": {
                    "amount": 50000,  # ₱500.00
                    "status": "paid",
                    "source": {
                        "id": "src_test_123"
                    },
                    "metadata": {
                        "user_id": "1",
                        "payment_type": "registration",
                        "registration_payment_id": "1"
                    }
                }
            }
        }
    }
}

response = requests.post(
    WEBHOOK_URL,
    json=test_event,
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
```

Run test:
```bash
python3 test_manual_webhook.py
```

#### Expected Results:
- ✅ Status Code: 400 (missing signature - this is correct!)
- ✅ Response contains: "No signature in request"

### Test Case 6: Webhook with Signature (Real PayMongo Event)

This happens automatically when you make a real payment through PayMongo checkout.

**Monitor webhook deliveries:**
1. Go to PayMongo Dashboard → Webhooks → Your Webhook
2. Click "Delivery Logs"
3. Check recent deliveries
4. Status should be "Successful" (HTTP 200)

---

## 📊 Phase 5: Admin Panel Testing

### Test Case 7: Admin Views Payments

#### Steps:
1. Login to admin: `http://localhost:8000/admin/`
2. Go to **Payments** → **Payments**
3. Check list view displays:
   - User (clickable link)
   - Amount (formatted with ₱)
   - Payment Method (badge)
   - Status (colored badge)
   - PayMongo Status (badge)
   - Date

#### Test Admin Actions:
1. Select multiple pending payments
2. From "Action" dropdown, select "Mark selected as Verified"
3. Click "Go"
4. Verify payments are now verified

#### Test CSV Export:
1. Select some payments
2. From "Action" dropdown, select "Export selected to CSV"
3. Click "Go"
4. CSV file should download

#### Test Payment Details View:
1. Click on a payment ID
2. Verify:
   - All fields display correctly
   - PayMongo section shows source_id, payment_id, gateway_response
   - Receipt image preview (if uploaded)
   - Gateway response formatted as JSON

---

## 🎨 Phase 6: UI/UX Testing

### Test Case 8: Payment Success Page

#### Steps:
1. Make a payment
2. After completion, verify redirect to success page
3. Check page displays:
   - Success icon (green checkmark)
   - "Payment Processing!" message
   - Information about next steps
   - Loading spinner
   - Auto-redirect countdown
   - Links to payment history and dashboard

### Test Case 9: Payment Failed Page

#### Steps:
1. Start payment but cancel
2. Verify redirect to failed page
3. Check page displays:
   - Failed icon (red X)
   - "Payment Unsuccessful" message
   - Common reasons for failure
   - What to do next
   - "Try Again" button
   - Links to payment history and dashboard

---

## 🔒 Phase 7: Security Testing

### Test Case 10: Webhook Signature Verification

#### Test Invalid Signature:
```python
import requests

response = requests.post(
    "http://localhost:8000/payments/webhook/",
    json={"test": "data"},
    headers={
        "Content-Type": "application/json",
        "Paymongo-Signature": "invalid_signature"
    }
)

print(f"Status: {response.status_code}")  # Should be 400
print(f"Response: {response.text}")  # Should say "Invalid signature"
```

### Test Case 11: CSRF Protection

Try accessing webhook without proper headers - should be rejected.

---

## 📈 Phase 8: Performance Testing

### Test Case 12: Multiple Simultaneous Payments

Create script to simulate multiple users:
```python
import concurrent.futures
import requests

def create_payment(user_id):
    # Simulate payment creation
    pass

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(create_payment, i) for i in range(10)]
    for future in concurrent.futures.as_completed(futures):
        print(f"Result: {future.result()}")
```

Monitor:
- Server response times
- Memory usage
- Database connections

---

## ✅ Testing Checklist

### Registration Flow
- [ ] New user can register
- [ ] Redirected to PayMongo checkout
- [ ] Payment creates source_id
- [ ] Webhook updates registration status
- [ ] Email sent after payment
- [ ] Membership expiry calculated correctly
- [ ] User can login after activation

### Payment Flow
- [ ] Existing user can make payment
- [ ] Amount validated correctly
- [ ] Redirected to PayMongo checkout
- [ ] Webhook updates payment status
- [ ] Payment appears in history
- [ ] Admin sees payment in panel

### Webhook
- [ ] Webhook endpoint accessible
- [ ] Signature verification works
- [ ] payment.paid event processed
- [ ] payment.failed event processed
- [ ] source.chargeable event processed
- [ ] Logs show webhook activity

### Admin Panel
- [ ] Payments list displays correctly
- [ ] Filters work (status, method, date)
- [ ] Search works (user, paymongo IDs)
- [ ] Payment details show all fields
- [ ] Actions work (verify, CSV export)
- [ ] Links to users work
- [ ] Gateway response formatted

### UI/UX
- [ ] Success page displays correctly
- [ ] Failed page displays correctly
- [ ] Auto-redirect works
- [ ] Payment history shows details
- [ ] Mobile responsive

### Security
- [ ] Webhook signature verified
- [ ] Invalid signatures rejected
- [ ] CSRF protection active
- [ ] No sensitive data in logs
- [ ] API keys not exposed

---

## 🐛 Common Issues & Solutions

### Issue: Webhook Not Receiving Events
**Solution:**
1. Verify ngrok is running: `curl https://your-ngrok-url.ngrok-free.app`
2. Check PayMongo webhook URL matches ngrok URL
3. Check Django logs for errors
4. Verify webhook secret in `.env` matches PayMongo

### Issue: Payment Not Verifying
**Solution:**
1. Check PayMongo dashboard for transaction status
2. Look for webhook delivery errors
3. Verify signature verification in code
4. Check logs: `tail -f /path/to/django/logs`

### Issue: "No signature in request"
**Solution:** This is expected for manual tests. Real PayMongo webhooks include signature.

### Issue: User Not Activated After Payment
**Solution:**
1. Check webhook was received
2. Verify `handle_payment_paid()` function
3. Check metadata contains correct user_id
4. Look for exceptions in logs

---

## 📝 Test Results Template

```markdown
## Test Results: [Date]

### Test Environment
- Django Version: 5.2.7
- Python Version: 3.11.x
- PayMongo Mode: TEST
- ngrok URL: https://xxxx.ngrok-free.app

### Registration Flow
- [x] Pass: New user registration
- [x] Pass: Payment redirect
- [x] Pass: Webhook processing
- [x] Pass: Account activation
- [ ] Fail: Email notification (reason: SMTP not configured)

### Payment Flow
- [x] Pass: Payment submission
- [x] Pass: PayMongo checkout
- [x] Pass: Webhook verification
- [x] Pass: Payment history display

### Issues Found
1. Email notifications not working - SMTP not configured
2. Mobile view needs adjustment on payment success page

### Next Steps
1. Configure SMTP for email
2. Fix mobile responsiveness
3. Test with real GCash account
```

---

## 🎯 Ready for Production?

Before switching to LIVE mode, ensure:

- ✅ All test cases pass
- ✅ No critical bugs
- ✅ Webhook working reliably
- ✅ Email notifications working
- ✅ Admin panel fully functional
- ✅ UI tested on multiple devices
- ✅ Security checks passed
- ✅ Performance acceptable
- ✅ Backup system in place
- ✅ Monitoring setup

**Then follow the [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) to go live!**
