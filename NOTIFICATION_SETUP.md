# 📧📱 Notification System Setup Guide

## 🔧 **Step-by-Step Configuration**

### **1. Gmail Email Setup**

#### **A. Enable 2-Step Verification**

1. Go to: https://myaccount.google.com/
2. Click **Security**
3. Enable **2-Step Verification** if not already enabled

#### **B. Generate App Password**

1. Go to: https://myaccount.google.com/apppasswords
2. Select **Mail** from the dropdown
3. Click **Generate**
4. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

#### **C. Update Settings**

In `boyscout_system/settings.py`, replace:

```python
EMAIL_HOST_PASSWORD = 'your-16-character-app-password-here'
```

With your actual app password (remove spaces).

### **2. Twilio SMS Setup**

#### **A. Get Twilio Credentials**

1. Go to: https://console.twilio.com/
2. Sign up/Login to your Twilio account
3. Copy your **Account SID** (starts with 'AC')
4. Copy your **Auth Token**
5. Note your **Twilio Phone Number**

#### **B. Update Settings**

In `boyscout_system/settings.py`, replace:

```python
TWILIO_ACCOUNT_SID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN = 'your-twilio-auth-token-here'
TWILIO_PHONE_NUMBER = '+17756409700'
```

With your actual Twilio credentials.

### **3. Test Your Configuration**

#### **A. Update Test Script**

In `test_notifications.py`, update:

```python
test_phone = "+639123456789"  # Replace with your actual phone number
```

#### **B. Run Test**

```bash
python test_notifications.py
```

## ✅ **Expected Results**

### **Successful Email Test:**

```
📧 Testing Email Configuration...
✅ Email sent successfully!
   Check your inbox: shawnmichael.sudaria@evsu.edu.ph
```

### **Successful SMS Test:**

```
📱 Testing SMS Configuration...
✅ SMS sent successfully!
   Check your phone: +639123456789
```

## 🚨 **Common Issues & Solutions**

### **Email Issues:**

-   **"Username and Password not accepted"**: Use App Password, not regular password
-   **"Less secure app access"**: Enable 2-Step Verification and use App Password

### **SMS Issues:**

-   **"Authentication Error"**: Check Account SID and Auth Token
-   **"Invalid phone number"**: Ensure phone number is in international format (+63...)

## 🔒 **Security Notes**

1. **Never commit credentials to Git**
2. **Use environment variables in production**
3. **Keep your App Password and Auth Token secure**

## 🎯 **Next Steps After Configuration**

1. ✅ Test email and SMS work
2. ✅ Create event to test notifications
3. ✅ Test payment verification notifications
4. ✅ Monitor notification delivery

## 📞 **Support**

-   **Gmail**: https://support.google.com/mail/
-   **Twilio**: https://support.twilio.com/
-   **Django Email**: https://docs.djangoproject.com/en/5.1/topics/email/
