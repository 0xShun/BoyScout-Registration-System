# 📧 Email Notification Setup - Complete Guide

## 🎯 Quick Setup for Payment Notifications

Your email settings are already configured in `.env`, but need credentials. Here are 3 options:

---

## ✅ Option 1: Gmail SMTP (Recommended for Testing)

**Perfect for:** Testing PayMongo payments and notifications  
**Time:** 5 minutes  
**Cost:** Free (500 emails/day)

### Step 1: Generate Gmail App Password

1. **Go to Google Account Security:**
   - Visit: https://myaccount.google.com/security
   - Enable **2-Step Verification** (if not already enabled)

2. **Create App Password:**
   - Visit: https://myaccount.google.com/apppasswords
   - Select App: **Mail**
   - Select Device: **Other (Custom name)**
   - Enter: `ScoutConnect`
   - Click **Generate**
   - **Copy the 16-character password** (e.g., `abcd efgh ijkl mnop`)

### Step 2: Update Your .env File

```bash
# Open .env file
nano .env
```

Update these lines:
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your.email@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=ScoutConnect <your.email@gmail.com>
```

**Important:**
- Replace `your.email@gmail.com` with your actual Gmail
- Replace `abcdefghijklmnop` with the 16-char password (no spaces!)
- Save: Press `Ctrl+O`, `Enter`, then `Ctrl+X`

### Step 3: Test Email

```bash
# Restart Django server (if running)
# Then test:
.venv/bin/python manage.py shell

# In shell, run:
from notifications.services import NotificationService
NotificationService.send_email(
    subject='✅ ScoutConnect Email Test',
    message='If you receive this, email notifications are working!',
    recipient_list=['your.email@gmail.com']
)

# Should return: True
# Check your Gmail inbox!
exit()
```

---

## 🚀 Option 2: SendGrid (Recommended for Production)

**Perfect for:** Production deployment, large-scale usage  
**Time:** 10 minutes  
**Cost:** Free tier (100 emails/day), Scalable paid plans

### Step 1: Create SendGrid Account

1. Sign up: https://signup.sendgrid.com/
2. Verify your email
3. Complete the onboarding

### Step 2: Create API Key

1. Go to: https://app.sendgrid.com/settings/api_keys
2. Click **Create API Key**
3. Name: `ScoutConnect`
4. Permissions: **Full Access** (or Restricted Access with Mail Send permission)
5. Click **Create & View**
6. **Copy the API key** (starts with `SG.` - you can only see this once!)

### Step 3: Verify Sender

1. Go to: https://app.sendgrid.com/settings/sender_auth/senders
2. Click **Create New Sender**
3. Fill in your details:
   - From Name: `ScoutConnect`
   - From Email Address: `noreply@yourdomain.com`
   - Reply To: Your support email
   - Company details
4. Click **Create**
5. **Verify the email** sent to your address

### Step 4: Update .env File

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_actual_sendgrid_api_key_here
DEFAULT_FROM_EMAIL=ScoutConnect <noreply@yourdomain.com>
```

### Step 5: Test SendGrid

```bash
.venv/bin/python manage.py shell

from notifications.services import NotificationService
NotificationService.send_email(
    subject='SendGrid Test - ScoutConnect',
    message='SendGrid email is working!',
    recipient_list=['your.email@example.com']
)
# Should return: True
```

---

## 🧪 Option 3: Console Backend (Local Testing Only)

**Perfect for:** Local development without sending real emails  
**Time:** 1 minute  
**Cost:** Free

All emails are printed to the terminal/console instead of being sent.

### Update .env File

```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

That's it! Now run your Django server and watch emails appear in the console:

```bash
.venv/bin/python manage.py runserver

# Emails will be printed to this terminal
```

---

## 🧪 Complete Test Flow

Once email is configured, test the entire payment notification flow:

### 1. Create Test Registration

```bash
.venv/bin/python test_registration_flow.py --type single
```

### 2. Complete Payment

- PayMongo checkout will open automatically
- Complete the payment using test payment method

### 3. Check for Email

Within 1-2 minutes, you should receive:

**Email Subject:** `Registration Confirmed - ScoutConnect`

**Email Body:**
```
Welcome to ScoutConnect! 

Your registration payment of ₱500.00 has been confirmed. 
Your account is now active!

You can now login and access all features.
```

### 4. Verify User Can Login

```bash
# Check user activation
.venv/bin/python manage.py shell -c "
from accounts.models import User
user = User.objects.filter(email__startswith='testuser_2025').first()
print(f'Email: {user.email}')
print(f'Status: {user.registration_status}')
print(f'Active: {user.is_active}')
"

# Try logging in via browser:
# http://127.0.0.1:8000/accounts/login/
# Email: testuser_20251017@example.com
# Password: TestPassword123
```

---

## 🐛 Troubleshooting

### Error: "SMTPAuthenticationError: Username and Password not accepted"

**Cause:** Wrong email credentials or not using App Password

**Fix:**
```bash
# For Gmail:
1. Make sure you're using App Password, NOT your regular Gmail password
2. Check EMAIL_HOST_USER is your full Gmail address
3. Check EMAIL_HOST_PASSWORD has no spaces
4. Verify 2-Step Verification is enabled

# Test credentials:
.venv/bin/python manage.py shell -c "
from django.conf import settings
print(f'User: {settings.EMAIL_HOST_USER}')
print(f'Pass: {settings.EMAIL_HOST_PASSWORD[:4]}... (length: {len(settings.EMAIL_HOST_PASSWORD)})')
"
```

### Error: "Connection refused" or "Timeout"

**Cause:** Firewall or port blocked

**Fix:**
```bash
# Test SMTP connection
telnet smtp.gmail.com 587

# Should show:
# Connected to smtp.gmail.com
# 220 smtp.gmail.com ESMTP...

# If fails, check:
1. Firewall settings
2. Antivirus blocking port 587
3. Network restrictions
```

### Emails Not Arriving

**Check:**
1. ✅ Spam/Junk folder
2. ✅ Email address is correct
3. ✅ For SendGrid: Sender is verified
4. ✅ For Gmail: Not exceeded 500 emails/day limit
5. ✅ Check Django logs for errors

```bash
# Check if email was sent
# Look for in Django server logs:
# "Email sending failed: ..." or successful send
```

### Email Shows But Not Sending

**Check Environment Variables:**
```bash
# Verify .env is being loaded
.venv/bin/python manage.py shell -c "
from django.conf import settings
print('Backend:', settings.EMAIL_BACKEND)
print('Host:', settings.EMAIL_HOST)
print('User:', settings.EMAIL_HOST_USER)
print('From:', settings.DEFAULT_FROM_EMAIL)
"
```

---

## 📊 View Email Logs

### Gmail
- Login to Gmail account used for EMAIL_HOST_USER
- Check **Sent** folder to see emails sent by ScoutConnect
- Check for security alerts

### SendGrid
- Login: https://app.sendgrid.com/
- Go to **Activity Feed** to see all email delivery status
- View bounces, spam reports, and delivery rates

---

## 🔍 Test Email Manually

### Quick Test Command
```bash
.venv/bin/python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
import django
django.setup()
from notifications.services import NotificationService
result = NotificationService.send_email(
    subject='Manual Test',
    message='Testing email notifications',
    recipient_list=['your.email@example.com']
)
print('✅ Email sent!' if result else '❌ Email failed!')
"
```

### Test with Real Webhook Simulation
```bash
.venv/bin/python manage.py shell

from payments.views import handle_payment_paid
from accounts.models import RegistrationPayment

# Get a pending payment
payment = RegistrationPayment.objects.filter(status='pending').first()
if payment:
    # Simulate PayMongo webhook
    webhook_data = {
        'data': {
            'attributes': {
                'type': 'payment.paid',
                'data': {
                    'id': 'pay_test_manual',
                    'attributes': {
                        'amount': int(float(payment.amount) * 100),
                        'source': {'id': 'src_test_manual'},
                        'metadata': {
                            'payment_type': 'registration',
                            'registration_payment_id': str(payment.id)
                        }
                    }
                }
            }
        }
    }
    
    handle_payment_paid(webhook_data)
    print(f'✅ Webhook processed for payment ID: {payment.id}')
    print(f'Check email: {payment.user.email}')
else:
    print('No pending payments to test')
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Email credentials added to `.env`
- [ ] Django server restarted
- [ ] Test email command returns `True`
- [ ] Email arrives in inbox (check spam)
- [ ] Can complete test payment
- [ ] Payment confirmation email received
- [ ] User account activated automatically
- [ ] Admin receives notification

---

## 📝 Current Status

Your current `.env` file has:
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=                    ❌ EMPTY - Add your Gmail
EMAIL_HOST_PASSWORD=                ❌ EMPTY - Add App Password
```

**Next Step:** Choose Option 1 (Gmail), Option 2 (SendGrid), or Option 3 (Console) and update your `.env` file!

---

## 🎯 Recommended Setup

| Environment | Recommended Option |
|------------|-------------------|
| Local Development | Option 3: Console Backend |
| Testing with Real Emails | Option 1: Gmail SMTP |
| Production | Option 2: SendGrid |

---

## 📞 Need Help?

Common questions:

**Q: Do I need to restart Django after updating .env?**  
A: Yes! Restart your Django server for changes to take effect.

**Q: Can I use a different email provider?**  
A: Yes! Update EMAIL_HOST (e.g., `smtp.outlook.com`, `smtp.mail.yahoo.com`), EMAIL_PORT, and credentials.

**Q: How do I know if email is working?**  
A: Run the test command - it should return `True` and you should receive the email.

**Q: What if I exceed Gmail's 500 emails/day limit?**  
A: Upgrade to SendGrid or another provider for production use.

---

Once configured, the system will automatically send emails for:
- ✅ Registration payment confirmed
- ✅ Batch registration complete
- ✅ Welcome emails to new students
- ✅ Event notifications
- ✅ Payment reminders

🎉 **Ready to set up email? Choose an option above and follow the steps!**
