# 🔧 Gmail App Password Troubleshooting

## ❌ Error: "Application-specific password required"

You're getting this error:
```
(534, b'5.7.9 Application-specific password required.')
```

This means Gmail is rejecting the password. Here's how to fix it:

---

## ✅ Step-by-Step Fix

### Step 1: Enable 2-Factor Authentication

1. **Go to Google Account Security:**
   ```
   https://myaccount.google.com/security
   ```

2. **Sign in with:** `shawnlovecode14@gmail.com`

3. **Find "2-Step Verification"** in the security settings

4. **Click "Turn on"** if not already enabled

5. **Complete the setup** (you'll need your phone)

---

### Step 2: Generate New App Password

1. **After 2FA is enabled, go to:**
   ```
   https://myaccount.google.com/apppasswords
   ```
   OR
   ```
   https://myaccount.google.com/security
   → Scroll down to "2-Step Verification"
   → Click "2-Step Verification"
   → Scroll to bottom, click "App passwords"
   ```

2. **You might need to sign in again**

3. **Create App Password:**
   - Click "Select app" → Choose **"Mail"**
   - Click "Select device" → Choose **"Other (Custom name)"**
   - Type: `ScoutConnect`
   - Click **"Generate"**

4. **Google shows password like:**
   ```
   Your app password is: abcd efgh ijkl mnop
   ```

5. **IMPORTANT:** Copy this password!

---

### Step 3: Update .env File

```bash
# Open .env
nano .env
```

Find this line:
```bash
EMAIL_HOST_PASSWORD=dferpmkruerzxpea
```

Replace with your NEW App Password (remove spaces):
```bash
EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

**Save:** Press `Ctrl+O`, `Enter`, `Ctrl+X`

---

### Step 4: Test Again

```bash
# Run test
.venv/bin/python test_email_simple.py

# Should see:
# ✅ SUCCESS! Test email sent
```

---

## 🔍 Common Issues

### Issue 1: Can't Find "App passwords" Option

**Reason:** 2-Factor Authentication not enabled  
**Fix:** 
1. Go to https://myaccount.google.com/security
2. Enable "2-Step Verification" first
3. Then App passwords option will appear

### Issue 2: "This setting is not available for your account"

**Reasons:**
- Workspace/Business account (admin needs to enable)
- Advanced Protection enabled
- Account too new

**Fix:**
- Use a personal Gmail account
- OR ask workspace admin to enable App passwords
- OR use SendGrid instead

### Issue 3: Still Getting "Invalid Password"

**Check:**
1. ✅ Password is exactly 16 characters
2. ✅ No spaces in password
3. ✅ No quotes around password in .env
4. ✅ Used the NEW App Password, not old one

---

## 📋 Quick Checklist

Before testing again, verify:

- [ ] 2-Factor Authentication is enabled on Gmail
- [ ] Generated NEW App Password after enabling 2FA
- [ ] Copied App Password correctly (16 characters)
- [ ] Removed spaces from password
- [ ] Updated EMAIL_HOST_PASSWORD in .env file
- [ ] No quotes or special characters around password
- [ ] Saved .env file

---

## 🎯 Quick Test Commands

### Check if password is correct length:
```bash
.venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
pwd = os.getenv('EMAIL_HOST_PASSWORD', '')
print(f'Password length: {len(pwd)}')
print(f'Should be: 16')
print(f'Match: {\"✅ YES\" if len(pwd) == 16 else \"❌ NO\"}')"
```

### Test email again:
```bash
.venv/bin/python test_email_simple.py
```

---

## 🔐 Security Note

**App Passwords are for apps only!**
- ✅ Use App Password for ScoutConnect
- ❌ Don't use your regular Gmail password
- ❌ Don't share App Password
- ✅ Can revoke anytime from Google Account

---

## 🚀 Alternative: Use SendGrid Instead

If Gmail continues to have issues, use SendGrid:

```bash
# Update .env:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your-sendgrid-api-key
DEFAULT_FROM_EMAIL=ScoutConnect <noreply@yourdomain.com>
```

See `EMAIL_SETUP_GUIDE.md` for SendGrid setup.

---

## 📞 Still Need Help?

### Verify 2FA Status:
Visit: https://myaccount.google.com/security
Look for "2-Step Verification" - should say "On"

### Check Security Activity:
Visit: https://myaccount.google.com/notifications
See if Google blocked sign-in attempts

### Reset and Try Again:
1. Revoke old App Password
2. Generate NEW App Password  
3. Update .env
4. Test again

---

## ✅ Expected Success Output

When working correctly, you'll see:
```
============================================================
📧 Email Configuration Test
============================================================
✅ Email Backend: django.core.mail.backends.smtp.EmailBackend
✅ SMTP Host: smtp.gmail.com:587
✅ Email User: shawnlovecode14@gmail.com
✅ Password: **************** (length: 16)

============================================================
🧪 Sending Test Email...
============================================================

✅ SUCCESS! Test email sent to: shawnlovecode14@gmail.com
📬 Check your Gmail inbox
```

Then check your Gmail inbox for the test email! 📧
