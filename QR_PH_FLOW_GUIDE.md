# QR PH Payment Flow - Complete Guide

## 🔄 Overview

Your system uses **PayMongo QR PH** which supports:
- 🟢 **GCash**
- 🔵 **PayMaya** 
- 🟣 **GrabPay**

All through a single EMVCo-compliant QR code.

---

## 📝 REGISTRATION PAGE - QR PH Flow

### ✅ Single Registration (IMPLEMENTED)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Visits: /accounts/register/                        │
│    - Selects "Single Registration"                         │
│    - Fills form: name, email, password, etc.               │
│    - Sees amount: ₱500.00                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User Clicks "Register & Proceed to Payment"             │
│                                                             │
│    Backend creates:                                         │
│    ✓ User (status='pending', is_active=True)              │
│    ✓ RegistrationPayment (status='pending', amount=500)   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PayMongo Source Created                                  │
│                                                             │
│    PayMongoService.create_source(                          │
│        amount=500.00,                                       │
│        description="Registration - Juan Dela Cruz",        │
│        metadata={                                           │
│            'user_id': '123',                               │
│            'payment_type': 'registration',                 │
│            'registration_payment_id': '456'                │
│        }                                                    │
│    )                                                        │
│                                                             │
│    Returns: checkout_url                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Redirect to PayMongo Checkout                            │
│                                                             │
│    URL: https://pm.link/org-name/test/abc123               │
│                                                             │
│    User sees:                                               │
│    ┌───────────────────────────────────────┐              │
│    │  ScoutConnect                         │              │
│    │  Registration Payment                 │              │
│    │                                        │              │
│    │  Amount: ₱500.00                      │              │
│    │                                        │              │
│    │  Select Payment Method:               │              │
│    │  [ ] GCash                            │              │
│    │  [ ] PayMaya                          │              │
│    │  [ ] GrabPay                          │              │
│    └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. User Selects E-Wallet (e.g., GCash)                     │
│                                                             │
│    PayMongo generates QR PH code (EMVCo standard)          │
│                                                             │
│    ┌───────────────────────────────────────┐              │
│    │  Scan QR Code with GCash              │              │
│    │                                        │              │
│    │      ████ ▄▄▄▄ █▀▀ ████               │              │
│    │      █  █ █▀▀█ ███ █  █               │              │
│    │      ████ ▄▄▄▄ █▀▀ ████               │              │
│    │                                        │              │
│    │  Open GCash → Scan QR                 │              │
│    │                                        │              │
│    │  Or enter amount manually              │              │
│    └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. User Opens E-Wallet App                                  │
│                                                             │
│    GCash app shows:                                         │
│    ┌───────────────────────────────────────┐              │
│    │  Pay to: ScoutConnect                 │              │
│    │  Amount: ₱500.00                      │              │
│    │                                        │              │
│    │  From: GCash Wallet                   │              │
│    │  Balance: ₱5,000.00                   │              │
│    │                                        │              │
│    │  [ Confirm Payment ]                  │              │
│    └───────────────────────────────────────┘              │
│                                                             │
│    User clicks "Confirm Payment"                           │
│    Enters MPIN                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Payment Processing                                       │
│                                                             │
│    GCash → PayMongo → Your Server                          │
│                                                             │
│    GCash deducts ₱500 from user's wallet                   │
│    PayMongo receives payment confirmation                  │
│    PayMongo sends webhook to your server                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Webhook Received: /payments/paymongo/webhook/           │
│                                                             │
│    Event: payment.paid                                     │
│    Data: {                                                  │
│        id: "pay_abc123",                                   │
│        amount: 50000,  # in centavos                       │
│        metadata: {                                          │
│            payment_type: "registration",                   │
│            registration_payment_id: "456"                  │
│        }                                                    │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. Webhook Processing (Automatic!)                          │
│                                                             │
│    handle_payment_paid() executes:                         │
│                                                             │
│    ✓ Find RegistrationPayment by ID                       │
│    ✓ Update status = 'verified'                           │
│    ✓ Save paymongo_payment_id                             │
│    ✓ Get associated User                                   │
│    ✓ Update user.registration_status = 'active'           │
│    ✓ Update user.is_active = True                         │
│    ✓ Calculate membership_expiry (₱500 = 1 year)          │
│    ✓ Save user                                             │
│    ✓ Send welcome email to user                           │
│    ✓ Send notification to admins                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. User Redirected                                         │
│                                                             │
│     PayMongo redirects to:                                 │
│     /payments/payment-success/                             │
│                                                             │
│     Shows:                                                  │
│     ┌───────────────────────────────────────┐             │
│     │  ✓ Payment Successful!                │             │
│     │                                        │             │
│     │  Your registration has been           │             │
│     │  confirmed and your account is        │             │
│     │  now active!                          │             │
│     │                                        │             │
│     │  Redirecting to login in 5 seconds... │             │
│     └───────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 11. User Can Login                                          │
│                                                             │
│     Email: juan@example.com                                │
│     Password: *********                                     │
│                                                             │
│     ✓ Account is ACTIVE                                    │
│     ✓ Can access dashboard                                 │
│     ✓ Registration complete!                               │
└─────────────────────────────────────────────────────────────┘
```

**Timeline:** ~2-5 minutes from start to finish

---

### ✅ Batch Registration (IMPLEMENTED)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Teacher Visits: /accounts/register/                     │
│    - Selects "Batch Registration (Teachers)"               │
│    - Fills teacher info: name, email, phone                │
│    - Sets number of students: 5                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Teacher Fills Student Forms                              │
│                                                             │
│    Student #1: Juan Cruz                                   │
│    Student #2: Pedro Reyes                                 │
│    Student #3: Jose Garcia                                 │
│    Student #4: Maria Santos                                │
│    Student #5: Ana Lopez                                   │
│                                                             │
│    ⚡ Total updates in real-time:                          │
│       5 students × ₱500 = ₱2,500.00                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Teacher Clicks "Submit Batch Registration"              │
│                                                             │
│    Backend creates:                                         │
│    ✓ BatchRegistration (total_amount=2500, status='pending')│
│    ✓ 5× BatchStudentData records (with hashed passwords)  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PayMongo Source Created                                  │
│                                                             │
│    PayMongoService.create_source(                          │
│        amount=2500.00,  # 5 students × ₱500               │
│        description="Batch Registration - Maria (5)",       │
│        metadata={                                           │
│            'payment_type': 'batch_registration',           │
│            'batch_registration_id': '789',                 │
│            'number_of_students': 5                         │
│        }                                                    │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Redirect to PayMongo - Amount: ₱2,500.00                │
│                                                             │
│    Same QR PH flow as single registration                  │
│    Teacher scans with GCash/PayMaya/GrabPay                │
│    Pays ₱2,500.00                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Webhook Processing (Automatic!)                          │
│                                                             │
│    handle_payment_paid() for batch:                        │
│                                                             │
│    ✓ Find BatchRegistration                               │
│    ✓ Update status = 'paid'                               │
│    ✓ Loop through 5 BatchStudentData records:             │
│      → Create User account for Juan                        │
│      → Create User account for Pedro                       │
│      → Create User account for Jose                        │
│      → Create User account for Maria                       │
│      → Create User account for Ana                         │
│    ✓ Create 5× RegistrationPayment (verified)             │
│    ✓ Send 5× welcome emails to students                   │
│    ✓ Update status = 'verified'                           │
│    ✓ Send confirmation to teacher                         │
│    ✓ Notify admins                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Result: 5 Student Accounts Created!                      │
│                                                             │
│    ✓ All can login immediately                             │
│    ✓ Each received welcome email                          │
│    ✓ Teacher received confirmation                         │
│    ✓ Total paid: ₱2,500.00                                │
└─────────────────────────────────────────────────────────────┘
```

**Timeline:** ~3-7 minutes (depending on form filling time)

---

## 🎫 EVENT REGISTRATION - Current vs Proposed

### ❌ Current Flow (Manual Receipt Upload)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Views Event: /events/<id>/                         │
│                                                             │
│    If event.has_payment_required:                          │
│    - Shows event QR code (static PaymentQRCode)            │
│    - Shows amount required                                 │
│    - Shows receipt upload form                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User Manually Pays                                       │
│                                                             │
│    User:                                                    │
│    1. Opens their GCash/PayMaya app                        │
│    2. Scans the QR code shown on page                      │
│    3. Enters amount manually                               │
│    4. Pays                                                  │
│    5. Takes screenshot of receipt                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. User Uploads Receipt                                     │
│                                                             │
│    EventRegistrationForm:                                  │
│    - RSVP: Yes                                             │
│    - Receipt Image: [uploads screenshot]                   │
│                                                             │
│    Submits form                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend Processing                                       │
│                                                             │
│    EventRegistration created:                              │
│    - payment_status = 'pending'                            │
│    - verified = False                                       │
│    - receipt_image = uploaded file                         │
│                                                             │
│    Admin notification sent                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. MANUAL Admin Verification                                │
│                                                             │
│    Admin:                                                   │
│    1. Goes to admin panel                                  │
│    2. Views EventRegistration                              │
│    3. Checks receipt image                                 │
│    4. Manually marks as verified/rejected                  │
│                                                             │
│    ⚠️ PROBLEM: Manual process, delays, errors             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. User Gets Verified (Eventually)                          │
│                                                             │
│    Timeline: Hours to days                                 │
│    Depends on admin availability                           │
└─────────────────────────────────────────────────────────────┘
```

**Problems:**
- ⚠️ Manual admin verification required
- ⚠️ Slow process (hours/days delay)
- ⚠️ No automatic payment confirmation
- ⚠️ User could fake receipts
- ⚠️ No integration with PayMongo
- ⚠️ QR code is static (not per-transaction)

---

### ✅ Proposed Flow (PayMongo QR PH)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Views Event: /events/<id>/                         │
│                                                             │
│    If event.has_payment_required:                          │
│    - Shows "Register & Pay Now" button                     │
│    - Shows amount: e.g., ₱300.00                           │
│    - Info: "Instant payment via GCash/PayMaya/GrabPay"    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User Clicks "Register & Pay Now"                         │
│                                                             │
│    Backend creates:                                         │
│    ✓ EventRegistration (verified=False)                   │
│    ✓ EventPayment (status='pending', amount=300)          │
│                                                             │
│    Calls PayMongoService.create_source(                    │
│        amount=300.00,                                       │
│        description="Event: Summer Camp 2025",              │
│        metadata={                                           │
│            'payment_type': 'event_registration',           │
│            'event_registration_id': '123',                 │
│            'event_id': '456'                               │
│        }                                                    │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Redirect to PayMongo Checkout                            │
│                                                             │
│    Same QR PH flow as registration:                        │
│    - User selects GCash/PayMaya/GrabPay                    │
│    - Scans QR code                                         │
│    - Confirms payment in app                               │
│    - Pays ₱300.00                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Webhook: payment.paid                                    │
│                                                             │
│    handle_payment_paid() for events:                       │
│                                                             │
│    ✓ Find EventPayment by metadata                        │
│    ✓ Update EventPayment.status = 'verified'              │
│    ✓ Update EventRegistration:                            │
│      - verified = True                                      │
│      - payment_status = 'paid'                             │
│      - total_paid = 300.00                                 │
│    ✓ Send confirmation email                              │
│    ✓ Notify event organizer                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. User Confirmed for Event (Instant!)                      │
│                                                             │
│    ✓ Registration verified automatically                   │
│    ✓ Can attend event                                      │
│    ✓ No manual admin approval needed                      │
│                                                             │
│    Timeline: 2-3 minutes                                   │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Automatic instant verification
- ✅ No manual admin work needed
- ✅ Secure PayMongo integration
- ✅ Unique QR per transaction
- ✅ Real payment confirmation
- ✅ Fast (minutes vs hours/days)

---

## 🔑 Key Differences Summary

| Feature | Registration | Events (Current) | Events (Proposed) |
|---------|--------------|------------------|-------------------|
| **Payment Method** | PayMongo QR PH | Manual Receipt Upload | PayMongo QR PH |
| **Verification** | Automatic | Manual Admin | Automatic |
| **Timeline** | 2-5 minutes | Hours to days | 2-5 minutes |
| **QR Code** | Dynamic (per transaction) | Static | Dynamic (per transaction) |
| **Security** | High (PayMongo verified) | Low (can be faked) | High (PayMongo verified) |
| **Admin Work** | None | High (verify each receipt) | None |
| **User Experience** | Excellent | Poor (wait for admin) | Excellent |
| **Status** | ✅ IMPLEMENTED | ⚠️ CURRENT | 💡 RECOMMENDED |

---

## 📋 Implementation Status

### ✅ Fully Implemented
1. **Single Registration** with PayMongo QR PH
2. **Batch Registration** with PayMongo QR PH
3. **Webhook Handler** for registration payments
4. **Email Notifications** for registrations
5. **Admin Dashboard** for batch management

### ⚠️ Still Using Old Method
1. **Event Registration** - Still uses manual receipt upload
2. **Regular Payments** - Not yet integrated with events

### 💡 Recommended Next Steps
1. Update Event Registration to use PayMongo QR PH
2. Remove manual receipt upload from events
3. Update webhook handler to support event payments
4. Test complete event registration flow

---

## 🎯 To Update Event Registration to PayMongo QR PH

You would need to modify:

1. **events/views.py** - `event_detail()` function
   - Create PayMongo source when user registers
   - Redirect to PayMongo checkout

2. **payments/views.py** - `handle_payment_paid()`
   - Add handler for `payment_type == 'event_registration'`
   - Update EventPayment and EventRegistration

3. **events/templates/events/event_detail.html**
   - Replace receipt upload form
   - Add "Register & Pay Now" button

4. **events/models.py**
   - Add PayMongo fields to EventPayment:
     - `paymongo_source_id`
     - `paymongo_payment_id`

Would you like me to implement the PayMongo QR PH integration for event registrations?

---

**Summary:** Your registration uses automatic PayMongo QR PH (✅), but events still use manual receipts (⚠️). Updating events to match registration would provide a consistent, fast, secure payment experience across your entire system!

