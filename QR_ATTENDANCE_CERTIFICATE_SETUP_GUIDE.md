# QR Code Attendance & Certificate Setup Guide

This guide will help you set up and troubleshoot the QR Code attendance marking and automatic certificate generation feature.

## ✅ Prerequisites Checklist

### 1. **Install Required Python Packages on Production (PythonAnywhere)**

The following packages are required for QR code generation and certificate creation:

```bash
# SSH into PythonAnywhere or use their Bash console
cd ~/BoyScout-Registration-System
source ~/.virtualenvs/boyscout_system/bin/activate
pip install Pillow>=10.0.0 qrcode[pil]>=7.4.2
```

**Verification:**
```bash
python -c "import PIL; print('Pillow:', PIL.__version__)"
python -c "import qrcode; print('qrcode:', qrcode.__version__)"
```

Both should print version numbers without errors.

---

### 2. **Upload Certificate Template for Each Event**

For certificates to be automatically generated, you MUST upload a certificate template for each event.

#### Step-by-Step:

1. **Access Django Admin Panel**
   - Go to: `https://scoutconnect.pythonanywhere.com/admin/`
   - Login with your admin credentials

2. **Navigate to Certificate Templates**
   - Click on **Events** → **Certificate templates**
   - Click **"Add Certificate Template"**

3. **Configure the Certificate Template**
   
   **Required Fields:**
   - **Event:** Select the event this certificate is for (one template per event)
   - **Template Image:** Upload your certificate background image (PNG or JPG, recommended 1920x1080px or A4 size)
   - **Certificate Name:** e.g., "Certificate of Participation"
   
   **Text Position Configuration:**
   
   You need to specify pixel coordinates where text will appear on the certificate:
   
   | Field | Description | Default | Example |
   |-------|-------------|---------|---------|
   | **Scout Name** |  |  |  |
   | `name_x` | Horizontal position for student name | 600 | 960 (center of 1920px wide image) |
   | `name_y` | Vertical position for student name | 450 | 500 |
   | `name_font_size` | Font size for name | 48 | 60 |
   | `name_color` | Hex color code | #000000 | #1e3a8a |
   | **Event Name** |  |  |  |
   | `event_x` | Horizontal position for event title | 600 | 960 |
   | `event_y` | Vertical position for event title | 520 | 620 |
   | `event_font_size` | Font size for event | 32 | 40 |
   | `event_color` | Hex color | #333333 | #3b82f6 |
   | **Date** |  |  |  |
   | `date_x` | Horizontal position for date | 600 | 960 |
   | `date_y` | Vertical position for date | 590 | 740 |
   | `date_font_size` | Font size for date | 28 | 32 |
   | `date_color` | Hex color | #666666 | #64748b |

4. **Tips for Positioning:**
   - **Finding coordinates:** Use an image editor like GIMP, Photoshop, or online tool like Photopea
   - Open your certificate image
   - Hover your mouse where you want text to appear
   - Note the X (horizontal) and Y (vertical) pixel coordinates
   - **Text alignment:** Text is centered horizontally at the X coordinate

5. **Save the Template**

---

## 🔄 How the Feature Works

### Admin/Teacher Flow:

1. **Navigate to Event Detail Page**
   - Go to Events → Select your event
   
2. **Generate QR Code**
   - Click **"Generate Attendance QR Code"** button
   - The QR code will be displayed on screen
   - You can download it or display it during the event

3. **QR Code Details:**
   - **One QR code per event** (all students scan the same code)
   - QR code contains a unique UUID token
   - Can set expiration time (optional)
   - Can be regenerated if needed (old code becomes invalid)

### Student Flow:

1. **Scan QR Code**
   - Student scans the QR code with their phone camera or any QR scanner app
   - URL opens in browser: `https://yoursite.com/events/attendance/verify/?token=<UUID>`

2. **System Verification** (automatic):
   - ✅ Student is logged in
   - ✅ Student has registered for the event
   - ✅ Registration payment is verified/paid
   - ✅ QR code is valid and not expired

3. **Automatic Actions:**
   - ✅ Marks attendance as "Present"
   - ✅ Generates certificate (if template exists)
   - ✅ Sends real-time notification to event organizer
   - ✅ Student can view/download certificate from "My Certificates" page

---

## ⚠️ Error Messages & Solutions

### For Students:

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "QR code not found or has been deactivated" | QR code doesn't exist or admin deactivated it | Contact event organizer to generate new QR |
| "This QR code has expired" | QR code expiration time passed | Ask organizer to generate new QR code |
| "Your registration for [Event] is not yet paid" | Registration exists but payment not verified | Complete payment and wait for admin verification |
| "You are not registered for [Event]" | No registration found | Register for the event first |
| "Attendance marked! Note: Certificate template not configured" | Attendance successful but no certificate | Attendance is recorded; admin needs to upload certificate template |

### For Admins:

| Issue | Cause | Solution |
|-------|-------|----------|
| Certificates not generating | No template uploaded | Upload certificate template in Django admin |
| Template image not found | File upload failed | Re-upload template image |
| Text not appearing correctly | Wrong coordinates | Adjust X/Y coordinates in admin panel |
| Font issues on production | Missing fonts on server | System uses fallback fonts automatically |

---

## 🧪 Testing the Feature

### Test Checklist:

1. **Install packages on production:**
   ```bash
   pip install Pillow qrcode[pil]
   ```

2. **Upload certificate template via admin panel**

3. **As Admin:**
   - [ ] Create an event
   - [ ] Upload certificate template for the event
   - [ ] Generate QR code for attendance
   - [ ] Download/display QR code

4. **As Student:**
   - [ ] Register for the event
   - [ ] Make payment (and get it verified)
   - [ ] Scan the QR code
   - [ ] Verify attendance was marked
   - [ ] Check if certificate was generated
   - [ ] View certificate in "My Certificates" page
   - [ ] Download certificate

---

## 📝 Production Deployment (PythonAnywhere)

### Step 1: Install Dependencies

```bash
# In PythonAnywhere Bash console
cd ~/BoyScout-Registration-System
source ~/.virtualenvs/boyscout_system/bin/activate
pip install -r requirements.txt
```

### Step 2: Reload Web App

- Go to PythonAnywhere **Web** tab
- Click **"Reload"** button for your web app

### Step 3: Upload Certificate Templates

- Login to admin panel
- Upload at least one certificate template for testing

### Step 4: Test End-to-End

- Generate QR code as admin
- Scan as student (with paid registration)
- Verify certificate generation

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"

**Solution:**
```bash
pip install Pillow
```

### "ModuleNotFoundError: No module named 'qrcode'"

**Solution:**
```bash
pip install qrcode[pil]
```

### Certificates not showing student names

**Check:**
1. Template coordinates are correct
2. Font size is appropriate
3. Text color contrasts with background

### QR code scanning not working

**Check:**
1. QR code is active (`active=True`)
2. QR code hasn't expired
3. Student has paid registration
4. Student is logged in

---

## 📚 Related Files

- **Models:** `events/models.py` (AttendanceQRCode, CertificateTemplate, EventCertificate)
- **Views:** `events/views.py` (verify_attendance, generate_attendance_qr)
- **Service:** `events/services/certificate_service.py` (generate_certificate)
- **Admin:** `events/admin.py` (CertificateTemplateAdmin)

---

## ✨ Feature Summary

**What Works:**
- ✅ QR code generation for events
- ✅ Automatic attendance marking
- ✅ Automatic certificate generation
- ✅ Student certificate viewing/downloading
- ✅ Real-time notifications
- ✅ Payment verification before attendance
- ✅ Clear error messages

**Requirements:**
- ⚠️ Pillow and qrcode packages installed
- ⚠️ Certificate template uploaded per event
- ⚠️ Student must have paid registration

---

## 🆘 Need Help?

If you encounter issues not covered in this guide:

1. Check Django admin logs
2. Check PythonAnywhere error logs
3. Verify all requirements are installed
4. Ensure certificate template is properly configured
5. Test with a simple event first

---

**Last Updated:** November 25, 2025
