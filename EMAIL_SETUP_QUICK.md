    # 🎉 Email Notification Setup - Ready to Configure!

## Current Status
✅ Email system is integrated and ready  
✅ Webhook sends emails automatically on payment success  
❌ Email credentials need to be configured  

---

## 🚀 Quick Setup (2 Ways)

### Option A: Interactive Setup Script (Easiest!)

Run this command and follow the prompts:
```bash
.venv/bin/python setup_email.py
```

The script will:
1. Ask you to choose: Gmail, SendGrid, or Console
2. Guide you through credential entry
3. Automatically update your .env file
4. Test email sending
5. Confirm everything works!

---

### Option B: Manual Setup

#### For Gmail (Testing):

1. **Generate App Password:**
   - Visit: https://myaccount.google.com/apppasswords
   - Select App: Mail
   - Copy the 16-character password

2. **Update .env file:**
   ```bash
   nano .env
   ```

3. **Add these lines:**
   ```bash
   EMAIL_HOST_USER=your.email@gmail.com
   EMAIL_HOST_PASSWORD=abcdefghijklmnop
   DEFAULT_FROM_EMAIL=ScoutConnect <your.email@gmail.com>
   ```

4. **Test:**
   ```bash
   .venv/bin/python manage.py shell -c "
   from notifications.services import NotificationService
   NotificationService.send_email(
       'Test', 
       'Email works!', 
       ['your.email@gmail.com']
   )
   "
   ```

#### For Console (No Real Emails):

Just update .env:
```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Emails will print to terminal instead of sending.

---

## 📧 What Emails Are Sent?

Once configured, the system automatically sends:

### 1. Registration Payment Confirmed
**When:** PayMongo webhook confirms payment  
**To:** User who registered  
**Subject:** Registration Confirmed - ScoutConnect  
**Content:** Welcome message + account activated

### 2. Batch Registration Complete
**When:** Teacher pays for multiple students  
**To:** Teacher who registered  
**Subject:** Batch Registration Complete  
**Content:** Confirmation + number of accounts created

### 3. Welcome Email (Each Student)
**When:** Batch registration processed  
**To:** Each student in the batch  
**Subject:** Welcome to ScoutConnect!  
**Content:** Login credentials + welcome message

---

## 🧪 Testing the Complete Flow

Once email is configured:

1. **Create test registration:**
   ```bash
   .venv/bin/python test_registration_flow.py --type single
   ```

2. **Complete payment** in PayMongo checkout (opens automatically)

3. **Watch for notifications:**
   - ✅ Email arrives (1-2 minutes)
   - ✅ User account activated
   - ✅ Admin receives notification
   - ✅ Payment status shows "Verified"

4. **Login with test account:**
   - URL: http://127.0.0.1:8000/accounts/login/
   - Email: testuser_20251017@example.com
   - Password: TestPassword123

---

## 📊 Email Flow Diagram

```
Payment Completed on PayMongo
            ↓
PayMongo sends webhook → /payments/paymongo/webhook/
            ↓
Webhook Handler Processes:
            ├─ Update payment status → "verified"
            ├─ Activate user account
            ├─ Set membership expiry
            ├─ 📧 Send email to user → "Registration Confirmed"
            ├─ 🔔 Send real-time notification to user
            └─ 🔔 Send real-time notification to admins
            ↓
User receives email and can login immediately
```

---

## 🐛 Quick Troubleshooting

### "SMTPAuthenticationError"
- **Gmail:** Use App Password, not regular password
- Verify EMAIL_HOST_USER has your full email
- Check for typos in credentials

### "Connection refused"
- Check firewall/antivirus blocking port 587
- Test: `telnet smtp.gmail.com 587`

### "Email not arriving"
- Check spam folder
- Verify email address is correct
- For Gmail: Check you haven't exceeded 500/day limit
- View server logs for errors

### "Settings not loading"
- Restart Django server after updating .env
- Verify .env file is in project root
- Check for syntax errors in .env

---

## 📝 Files Created/Updated

✅ **EMAIL_SETUP_GUIDE.md** - Complete setup documentation  
✅ **setup_email.py** - Interactive setup script  
✅ **PAYMENT_SUCCESS_NOTIFICATIONS.md** - How notifications work  
✅ **accounts/models.py** - Added PayMongo fields to RegistrationPayment  
✅ **Migration 0017** - Database updated with new fields  

---

## ✅ Ready to Setup!

Choose your method:

### Interactive (Recommended):
```bash
.venv/bin/python setup_email.py
```

### Manual:
```bash
# Edit .env file
nano .env

# Add email credentials
# See EMAIL_SETUP_GUIDE.md for details
```

### Testing Only:
```bash
# Just add this to .env:
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## 🎯 Next Steps After Setup

1. ✅ Run setup script or update .env manually
2. ✅ Restart Django server
3. ✅ Test email with: `.venv/bin/python setup_email.py`
4. ✅ Create test payment and verify email arrives
5. ✅ Complete PayMongo payment
6. ✅ Confirm user receives registration email
7. ✅ Verify admin receives notification

---

## 📞 Need Help?

- **Detailed Guide:** See `EMAIL_SETUP_GUIDE.md`
- **How Notifications Work:** See `PAYMENT_SUCCESS_NOTIFICATIONS.md`
- **PayMongo Testing:** See `PAYMONGO_TEST_GUIDE.md`

---

**Time to setup:** 5 minutes  
**Difficulty:** Easy  
**Required:** Gmail account with App Password OR SendGrid account

🚀 **Run `./venv/bin/python setup_email.py` to get started!**
