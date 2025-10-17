# 🧪 PayMongo Registration Test - Ready to Test!

## ✅ Test Registration Created Successfully!

A test registration has been created and is ready for payment testing.

---

## 📋 Test Details

**Test User:**
- **Name:** Test User
- **Email:** testuser_20251017@example.com
- **Username:** testuser_20251017
- **User ID:** 33
- **Registration Payment ID:** 8
- **Amount:** ₱500.00
- **Status:** Pending (waiting for payment)

**PayMongo Source:**
- **Source ID:** src_uEUZQCmRJGg8rALTXLxLmfYd
- **Status:** pending
- **Type:** gcash

---

## 💳 NEXT STEPS: Complete the Payment

### Option 1: Using PayMongo TEST Mode (Recommended)

1. **Open the PayMongo Checkout Page:**
   ```
   https://secure-authentication.paymongo.com/sources?id=src_uEUZQCmRJGg8rALTXLxLmfYd
   ```
   *(Already opened in Simple Browser)*

2. **On the PayMongo page:**
   - You'll see payment options: GCash, PayMaya, GrabPay
   - Select **GCash** (or any e-wallet)

3. **For TEST Mode Payment:**
   
   **GCash Test:**
   - You'll see a QR code
   - In TEST mode, PayMongo provides a way to simulate payment
   - Look for a "Pay Now" or "Simulate Payment" button
   - OR use PayMongo's test webhook trigger

   **Alternative - Use PayMongo Dashboard:**
   - Go to: https://dashboard.paymongo.com/
   - Login with your PayMongo account
   - Navigate to: Payments → Sources
   - Find source: `src_uEUZQCmRJGg8rALTXLxLmfYd`
   - Click "Mark as Chargeable" or "Test Payment"

---

## 🔔 What Happens After Payment

### Automatic Webhook Processing:

1. **PayMongo sends webhook** to: `http://127.0.0.1:8000/payments/paymongo/webhook/`
   - Event: `payment.paid`
   - Contains: payment details, metadata

2. **Your server receives webhook:**
   - Finds RegistrationPayment ID: 8
   - Updates status to 'verified'
   - Activates user account (registration_status='active')
   - Sends welcome email
   - Notifies admins

3. **User can login immediately!**

---

## 📊 How to Monitor the Test

### Watch Server Logs:

The Django server is running at: `http://127.0.0.1:8000/`

Watch the terminal for logs showing:
```
[INFO] Webhook received: payment.paid
[INFO] Processing payment for RegistrationPayment ID: 8
[INFO] User account activated: testuser_20251017@example.com
```

### Check Database After Payment:

```bash
# Run Django shell
.venv/bin/python manage.py shell

# Check user status
from accounts.models import User, RegistrationPayment
user = User.objects.get(id=33)
print(f"Registration Status: {user.registration_status}")
print(f"Is Active: {user.is_active}")

# Check payment status
payment = RegistrationPayment.objects.get(id=8)
print(f"Payment Status: {payment.status}")
print(f"PayMongo Payment ID: {payment.paymongo_payment_id}")
```

### Check Admin Panel:

1. Go to: http://127.0.0.1:8000/admin/
2. Navigate to: Accounts → Registration payments
3. Find RegistrationPayment ID: 8
4. Check if status changed to 'verified'

---

## 🧪 Alternative: Manually Trigger Webhook (for testing)

If you can't complete the payment in TEST mode, you can manually trigger the webhook:

### Create a test webhook payload:

```bash
.venv/bin/python manage.py shell
```

```python
from payments.views import handle_payment_paid
from accounts.models import RegistrationPayment

# Simulate webhook data
webhook_data = {
    'data': {
        'attributes': {
            'type': 'payment.paid',
            'data': {
                'id': 'pay_test123',
                'attributes': {
                    'amount': 50000,  # ₱500 in centavos
                    'status': 'paid',
                    'source': {
                        'id': 'src_uEUZQCmRJGg8rALTXLxLmfYd'
                    },
                    'metadata': {
                        'user_id': '33',
                        'payment_type': 'registration',
                        'registration_payment_id': '8'
                    }
                }
            }
        }
    }
}

# Process webhook
handle_payment_paid(webhook_data)

# Verify user activated
user = User.objects.get(id=33)
print(f"User Active: {user.is_active}")
print(f"Registration Status: {user.registration_status}")
```

---

## ✅ Success Criteria

After payment is completed, verify:

- [ ] RegistrationPayment status = 'verified'
- [ ] RegistrationPayment.paymongo_payment_id is set
- [ ] User.registration_status = 'active'
- [ ] User.is_active = True
- [ ] User can login with: testuser_20251017@example.com / TestPassword123
- [ ] Welcome email sent (check logs if email configured)
- [ ] Admin notification sent

---

## 🎯 Test Single vs Batch Registration

### Current Test: Single Registration ✅
- 1 user created
- ₱500.00 payment
- 1 account activated after payment

### To Test Batch Registration:

```bash
.venv/bin/python test_registration_flow.py --type batch
```

This will:
- Create 3 test students
- Generate ₱1,500 payment (3 × ₱500)
- After payment: 3 accounts created automatically!

---

## 📝 Cleanup After Testing

To remove test data:

```bash
.venv/bin/python manage.py shell
```

```python
from accounts.models import User, RegistrationPayment

# Delete test user
User.objects.filter(email='testuser_20251017@example.com').delete()

# Or keep for continued testing
```

---

## 🚨 Troubleshooting

### Webhook Not Received?

**Problem:** PayMongo can't reach localhost

**Solution:** Use ngrok to expose localhost:

```bash
# In a new terminal
ngrok http 8000
```

This gives you a public URL like: `https://abc123.ngrok.io`

Update webhook URL in PayMongo dashboard:
- Go to: https://dashboard.paymongo.com/developers/webhooks
- Update URL to: `https://abc123.ngrok.io/payments/paymongo/webhook/`
- Test webhook delivery

### Payment Stuck in Pending?

**For TEST mode:**
- Check PayMongo dashboard
- Manually mark source as "chargeable"
- Or create a payment manually linking to the source

---

## 📞 Need Help?

**PayMongo Documentation:**
- Sources API: https://developers.paymongo.com/reference/create-a-source
- Webhooks: https://developers.paymongo.com/reference/webhook-resource
- Testing: https://developers.paymongo.com/docs/testing

**PayMongo Dashboard:**
- https://dashboard.paymongo.com/

**Your Webhook Endpoint:**
- Local: http://127.0.0.1:8000/payments/paymongo/webhook/
- With ngrok: https://[your-ngrok-url]/payments/paymongo/webhook/

---

## 🎉 Happy Testing!

You now have:
✅ Test user created
✅ PayMongo source generated
✅ Checkout URL ready
✅ Webhook endpoint listening
✅ Automatic account activation configured

**Just complete the payment and watch the magic happen!** ✨
