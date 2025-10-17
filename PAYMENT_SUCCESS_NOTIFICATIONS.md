# 🔔 Payment Success Notifications - Complete Guide

## Overview
When a payment is successfully processed via PayMongo, the system automatically notifies both **users** and **admins** through multiple channels.

---

## 📱 User Notifications (When Payment is Successful)

### 1. **Immediate Browser Redirect** ✅
- **What happens:** After completing payment on PayMongo, user is redirected to success page
- **Page:** `/payments/payment/success/`
- **Features:**
  - ✓ Large success checkmark icon
  - ✓ "Payment Processing!" message
  - ✓ Auto-refresh every 5 seconds
  - ✓ Countdown timer showing verification progress
  - ✓ Links to payment history and dashboard

### 2. **Email Notification** 📧
**For Single Registration:**
```
Subject: Registration Confirmed - ScoutConnect

Welcome to ScoutConnect! 

Your registration payment of ₱500.00 has been confirmed. 
Your account is now active!

You can now login and access all features.
```

**For Batch Registration (Teacher):**
```
Subject: Batch Registration Complete - ScoutConnect

Dear [Teacher Name],

Your batch registration payment of ₱1,500.00 has been confirmed!

Successfully created 3 student accounts out of 3 students.

All students have been sent their login credentials via email.

Thank you for using ScoutConnect!
```

**For Batch Registration (Each Student):**
```
Subject: Welcome to ScoutConnect!

Hello [Student Name],

Your account has been created as part of a batch registration by [Teacher Name].

You can now login to ScoutConnect using your email: [email]

Welcome to our scout community!
```

### 3. **Real-Time In-App Notification** 🔴
- **Location:** Top-right notification bell icon
- **Message:** "Welcome to ScoutConnect! Your registration is confirmed."
- **Appearance:** 
  - Green success badge
  - Red dot indicator (unread)
  - Timestamp
  - Persistent until user clicks to read

### 4. **Account Activation** ✅
**Automatic Changes:**
- ✓ `registration_status` → `'active'`
- ✓ `is_active` → `True`
- ✓ `membership_expiry` → Calculated based on payment amount (₱500 = 1 year)
- ✓ Can now login and access all features

### 5. **Payment History Update** 💳
- **Location:** `/payments/` - Payment List page
- **Changes:**
  - Badge color: Yellow "Pending" → Green "Verified"
  - Payment status updated
  - Verification timestamp recorded
  - PayMongo payment ID saved

---

## 👨‍💼 Admin Notifications (When Payment is Successful)

### 1. **Real-Time In-App Notification** 🔴
**For Single Registration:**
- **Location:** Admin notification bell (top-right)
- **Message:** `"Registration payment confirmed: [Name] - ₱500.00"`
- **Type:** `registration_verified`
- **Appearance:** Green success badge

**For Batch Registration:**
- **Message:** `"Batch registration completed: [Teacher Name] (3 students) - ₱1,500.00"`
- **Type:** `batch_registration_verified`
- **Appearance:** Green success badge with student count

### 2. **Admin Dashboard Updates** 📊
**Admin Panel:** `/admin/accounts/registrationpayment/`
- ✓ Payment status changes from "Pending" to "Verified"
- ✓ User's registration status shows as "Active"
- ✓ PayMongo Payment ID recorded
- ✓ Verification timestamp recorded

**Pending Registrations Page:** `/accounts/pending_registrations/`
- ✓ User removed from pending list
- ✓ Moved to active users list
- ✓ Green "Active" badge displayed

### 3. **Analytics Dashboard** 📈
**Location:** `/analytics/dashboard/`
- ✓ Total revenue updated in real-time
- ✓ New registration counted
- ✓ Payment success rate recalculated
- ✓ Recent activities log updated

---

## 🔄 Complete Payment Flow with Notifications

### Single Registration Flow:
```
1. User completes registration form
   ↓
2. Redirected to PayMongo checkout (GCash/PayMaya/GrabPay)
   ↓
3. User completes payment on PayMongo
   ↓
4. PayMongo sends webhook: "payment.paid" → http://your-server/payments/paymongo/webhook/
   ↓
5. WEBHOOK HANDLER AUTOMATICALLY:
   ├─ Updates RegistrationPayment status → "verified"
   ├─ Activates user account (registration_status → "active")
   ├─ Sets membership expiry date
   ├─ Sends EMAIL to user: "Registration Confirmed"
   ├─ Sends REAL-TIME notification to user
   └─ Sends REAL-TIME notifications to ALL admins
   ↓
6. User redirected to success page
   ↓
7. User can now login and access system
```

### Batch Registration Flow:
```
1. Teacher fills batch registration form (3 students)
   ↓
2. System calculates: 3 × ₱500 = ₱1,500
   ↓
3. Teacher redirected to PayMongo checkout
   ↓
4. Teacher completes payment
   ↓
5. PayMongo webhook triggers: "payment.paid"
   ↓
6. WEBHOOK HANDLER AUTOMATICALLY:
   ├─ Updates BatchRegistration status → "verified"
   ├─ Creates 3 SEPARATE User accounts
   ├─ Creates 3 RegistrationPayment records (₱500 each)
   ├─ Links all students to batch registration
   ├─ Sends EMAIL to teacher: "Batch Registration Complete"
   ├─ Sends EMAIL to EACH student: "Welcome to ScoutConnect"
   ├─ Sends REAL-TIME notification to teacher
   └─ Sends REAL-TIME notifications to ALL admins
   ↓
7. Teacher redirected to success page
   ↓
8. All 3 students can now login with their credentials
```

---

## 🎯 How to Check Payment Success

### **For Users:**

1. **Check Email** 📧
   - Look for "Registration Confirmed - ScoutConnect" email
   - Should arrive within 1-2 minutes

2. **Check Notification Bell** 🔔
   - Click bell icon (top-right)
   - Look for green "Registration Confirmed" notification

3. **Check Payment History** 💳
   - Go to: `/payments/`
   - Your payment should show green "Verified" badge
   - Verification date should be displayed

4. **Try to Login** 🔐
   - If registration payment successful, you can login
   - Email: Your registered email
   - Password: The password you set during registration

5. **Check Dashboard** 🏠
   - Login and visit dashboard
   - Membership status should show "Active"
   - Expiry date should be set (1 year from now)

### **For Admins:**

1. **Check Notification Bell** 🔔
   - Look for green badge with "Registration payment confirmed" message
   - Shows user name and payment amount

2. **Admin Panel** 🛠️
   - Visit: `/admin/accounts/registrationpayment/`
   - Filter by status: "Verified"
   - View recent verifications

3. **Pending Registrations** 📋
   - Visit: `/accounts/pending_registrations/`
   - Verified users removed from pending list
   - Check active users for newly verified accounts

4. **Analytics Dashboard** 📊
   - Visit: `/analytics/dashboard/`
   - Recent activities section shows new payments
   - Revenue graph updated

5. **Django Admin** 💻
   - `/admin/`
   - Check User model: `registration_status` = "active"
   - Check RegistrationPayment: `status` = "verified"

---

## 🚨 What If Payment Doesn't Show as Successful?

### **For Users:**

1. **Wait 5 minutes**
   - PayMongo webhook might be delayed
   - System will retry if webhook fails

2. **Check email spam folder**
   - Confirmation email might be in spam

3. **Contact Admin**
   - Provide: Email, payment date/time, amount
   - Admin can manually verify payment in PayMongo dashboard

### **For Admins:**

1. **Check PayMongo Dashboard**
   - Login to: https://dashboard.paymongo.com/
   - Check "Payments" section
   - Look for payment ID and status

2. **Check Django Logs**
   - View server logs for webhook events
   - Look for: "Processing payment.paid for payment: [payment_id]"

3. **Manual Verification**
   - Django Admin → RegistrationPayment
   - Find pending payment
   - Manually change status to "verified"
   - Click "Save"
   - System will trigger activation

4. **Check Webhook Endpoint**
   - Ensure webhook URL is accessible: `http://your-domain/payments/paymongo/webhook/`
   - Test locally: Use ngrok if testing on localhost

---

## 🧪 Testing Notifications

### Test with PayMongo TEST Mode:
```bash
# 1. Create test registration
.venv/bin/python test_registration_flow.py --type single

# 2. Complete payment in PayMongo checkout (opened automatically)

# 3. Check notifications:
# - User email: testuser_[date]@example.com
# - Admin panel: /admin/accounts/registrationpayment/
# - Server logs: Watch for "payment.paid" webhook

# 4. Verify account activation:
# - Try login with test user credentials
# - Should be able to access dashboard
```

### Manual Webhook Test:
```python
# In Django shell: python manage.py shell
from payments.views import paymongo_webhook_handler
from django.http import HttpRequest
import json

# Simulate PayMongo webhook
request = HttpRequest()
request.method = 'POST'
request.body = json.dumps({
    "data": {
        "attributes": {
            "type": "payment.paid",
            "data": {
                "id": "pay_test123",
                "attributes": {
                    "amount": 50000,  # ₱500.00 in centavos
                    "source": {"id": "src_test123"},
                    "metadata": {
                        "payment_type": "registration",
                        "registration_payment_id": "8"
                    }
                }
            }
        }
    }
}).encode()

response = paymongo_webhook_handler(request)
print(response.status_code)  # Should be 200
```

---

## 📝 Summary

### ✅ Users Get Notified Via:
1. Browser redirect to success page (immediate)
2. Email confirmation (1-2 minutes)
3. Real-time in-app notification (instant)
4. Account activation (instant login access)
5. Updated payment history page

### ✅ Admins Get Notified Via:
1. Real-time in-app notification bell (instant)
2. Admin panel status updates
3. Pending registrations list updates
4. Analytics dashboard updates
5. Django admin interface updates

### 🔑 Key Points:
- **Automatic:** No manual intervention needed
- **Real-time:** Webhook processes payment within seconds
- **Multi-channel:** Email + in-app + status updates
- **Reliable:** Payment status changes trigger all notifications
- **Secure:** PayMongo handles payment verification

---

## 📞 Support

If payment is not showing as successful after 5 minutes:
1. Check PayMongo dashboard for payment status
2. Check Django server logs for webhook errors
3. Verify webhook URL is accessible
4. Contact system administrator with payment details
