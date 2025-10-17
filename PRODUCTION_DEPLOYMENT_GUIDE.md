# 🚀 Production Deployment Guide - PayMongo Integration

## Overview
This guide walks you through deploying the ScoutConnect Boy Scout registration system with PayMongo payment integration to production.

---

## 📋 Pre-Deployment Checklist

### 1. PayMongo Account Setup
- [ ] Create PayMongo account at https://dashboard.paymongo.com
- [ ] Complete business verification
- [ ] Get LIVE API keys approved
- [ ] Verify bank account for settlements
- [ ] Test in TEST mode first

### 2. Server Requirements
- [ ] Ubuntu 20.04+ or similar Linux server
- [ ] Python 3.8+
- [ ] PostgreSQL 12+ (or MySQL 5.7+)
- [ ] Nginx web server
- [ ] SSL certificate (Let's Encrypt recommended)
- [ ] Domain name with DNS configured
- [ ] Minimum 2GB RAM, 2 CPU cores

### 3. Domain & SSL
- [ ] Domain purchased and configured
- [ ] DNS A record pointing to server IP
- [ ] SSL certificate installed (HTTPS required for PayMongo)

---

## 🔧 Step 1: Server Setup

### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev \
  postgresql postgresql-contrib nginx curl git -y
```

### 1.2 Create Application User
```bash
sudo adduser scout
sudo usermod -aG sudo scout
su - scout
```

### 1.3 Setup PostgreSQL Database
```bash
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE boyscout_db;
CREATE USER boyscout_user WITH PASSWORD 'your_secure_password';
ALTER ROLE boyscout_user SET client_encoding TO 'utf8';
ALTER ROLE boyscout_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE boyscout_user SET timezone TO 'Asia/Manila';
GRANT ALL PRIVILEGES ON DATABASE boyscout_db TO boyscout_user;
\q
```

---

## 📦 Step 2: Deploy Application

### 2.1 Clone Repository
```bash
cd /home/scout/
git clone https://github.com/0xShun/BoyScout-Registration-System.git
cd BoyScout-Registration-System
```

### 2.2 Setup Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 2.3 Configure Environment Variables
```bash
cp .env.example .env
nano .env
```

**Production `.env` Configuration:**
```bash
# Django Settings
SECRET_KEY=<generate-new-secret-key>  # Use: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=boyscout_db
DB_USER=boyscout_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# PayMongo LIVE Keys (IMPORTANT!)
PAYMONGO_PUBLIC_KEY=pk_live_YOUR_LIVE_PUBLIC_KEY
PAYMONGO_SECRET_KEY=sk_live_YOUR_LIVE_SECRET_KEY
PAYMONGO_WEBHOOK_SECRET=whsk_YOUR_LIVE_WEBHOOK_SECRET

# Security Settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True

# Static/Media Files
STATIC_ROOT=/home/scout/BoyScout-Registration-System/staticfiles
MEDIA_ROOT=/home/scout/BoyScout-Registration-System/media
```

### 2.4 Configure Django Settings
```bash
cp boyscout_system/settings.example.py boyscout_system/settings.py
nano boyscout_system/settings.py
```

**Important Production Settings:**
```python
# At the bottom of settings.py
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Static files
STATIC_ROOT = os.environ.get('STATIC_ROOT', BASE_DIR / 'staticfiles')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')
```

### 2.5 Run Migrations & Collect Static Files
```bash
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 2.6 Create Media Directories
```bash
mkdir -p media/event_qr_codes
mkdir -p media/event_receipts
mkdir -p media/payment_qr_codes
mkdir -p media/payment_receipts
mkdir -p media/registration_payment_receipts
mkdir -p media/registration_receipts
chmod -R 755 media/
```

---

## 🌐 Step 3: Nginx Configuration

### 3.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/boyscout
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Certificate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    client_max_body_size 10M;
    
    # Static files
    location /static/ {
        alias /home/scout/BoyScout-Registration-System/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/scout/BoyScout-Registration-System/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### 3.2 Enable Site & Test Configuration
```bash
sudo ln -s /etc/nginx/sites-available/boyscout /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 Step 4: SSL Certificate (Let's Encrypt)

### 4.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 4.2 Obtain Certificate
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow prompts and select option to redirect HTTP to HTTPS.

### 4.3 Test Auto-Renewal
```bash
sudo certbot renew --dry-run
```

---

## 🚀 Step 5: Setup Gunicorn as Systemd Service

### 5.1 Create Gunicorn Socket
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```

```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 5.2 Create Gunicorn Service
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=gunicorn daemon for BoyScout Registration System
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
User=scout
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=/home/scout/BoyScout-Registration-System
Environment="PATH=/home/scout/BoyScout-Registration-System/.venv/bin"
EnvironmentFile=/home/scout/BoyScout-Registration-System/.env
ExecStart=/home/scout/BoyScout-Registration-System/.venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8000 \
          --timeout 120 \
          --access-logfile /var/log/gunicorn/access.log \
          --error-logfile /var/log/gunicorn/error.log \
          boyscout_system.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 5.3 Create Log Directory
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown scout:www-data /var/log/gunicorn
```

### 5.4 Start Gunicorn Service
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl start gunicorn.service
sudo systemctl enable gunicorn.service
sudo systemctl status gunicorn.service
```

---

## 💳 Step 6: PayMongo Production Setup

### 6.1 Switch to LIVE API Keys

**CRITICAL: Test thoroughly in TEST mode before switching to LIVE!**

1. Go to PayMongo Dashboard: https://dashboard.paymongo.com
2. Navigate to **Developers** → **API Keys**
3. Switch from TEST to LIVE mode
4. Copy LIVE keys to `.env` file:

```bash
PAYMONGO_PUBLIC_KEY=pk_live_...
PAYMONGO_SECRET_KEY=sk_live_...
```

⚠️ **WARNING**: LIVE keys process real money! Triple-check configuration.

### 6.2 Configure Production Webhook

1. In PayMongo Dashboard → **Developers** → **Webhooks**
2. Click **Create Webhook**
3. Configure:
   - **URL**: `https://yourdomain.com/payments/webhook/`
   - **Events**: Select:
     - `source.chargeable`
     - `payment.paid`
     - `payment.failed`
   - **Description**: Production ScoutConnect Webhook
4. Save webhook
5. Copy **Webhook Secret** to `.env`:

```bash
PAYMONGO_WEBHOOK_SECRET=whsk_...
```

### 6.3 Test Webhook
```bash
# Test webhook endpoint is accessible
curl -X POST https://yourdomain.com/payments/webhook/
# Should return: {"error": "No signature in request"}

# Check logs
sudo tail -f /var/log/gunicorn/error.log
```

### 6.4 Make Small Test Transaction
1. Create test user account
2. Register with minimum amount (₱100)
3. Complete payment with real GCash/PayMaya
4. Verify:
   - Payment received in PayMongo dashboard
   - Webhook triggered successfully
   - User account activated
   - Email notification sent

---

## 📧 Step 7: Email Configuration

### Using Gmail (Recommended for Testing)
1. Enable 2-Factor Authentication on your Google account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password in `.env`:

```bash
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-digit-app-password
```

### Using SendGrid (Recommended for Production)
1. Sign up at https://sendgrid.com
2. Create API key
3. Configure in `.env`:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

### Test Email
```bash
source .venv/bin/activate
python manage.py shell

# Test sending email
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test email from ScoutConnect.',
    'noreply@yourdomain.com',
    ['your-email@example.com'],
    fail_silently=False,
)
```

---

## 🔐 Step 8: Security Hardening

### 8.1 Firewall Configuration
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

### 8.2 Secure File Permissions
```bash
cd /home/scout/BoyScout-Registration-System
chmod 600 .env
chmod -R 750 .
chmod -R 755 media/
chmod -R 755 staticfiles/
```

### 8.3 Setup Fail2Ban (Optional but Recommended)
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 8.4 Regular Backups

**Database Backup Script** (`/home/scout/backup_db.sh`):
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/scout/backups"
mkdir -p $BACKUP_DIR

# Backup database
PGPASSWORD=your_secure_password pg_dump -U boyscout_user -h localhost boyscout_db > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /home/scout/BoyScout-Registration-System/media

# Delete backups older than 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /home/scout/backup_db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
0 2 * * * /home/scout/backup_db.sh >> /home/scout/backups/backup.log 2>&1
```

---

## 📊 Step 9: Monitoring & Logging

### 9.1 Check Application Logs
```bash
# Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# System logs
sudo journalctl -u gunicorn.service -f
```

### 9.2 Monitor System Resources
```bash
# Install htop
sudo apt install htop -y
htop

# Check disk space
df -h

# Check memory
free -h
```

---

## 🧪 Step 10: Post-Deployment Testing

### Checklist
- [ ] Homepage loads correctly
- [ ] Admin panel accessible at `/admin/`
- [ ] User registration works
- [ ] PayMongo payment redirect works
- [ ] Webhook receives and processes events
- [ ] User account activated after payment
- [ ] Email notifications sent
- [ ] SSL certificate valid (check with https://www.ssllabs.com/ssltest/)
- [ ] Payment history displays correctly
- [ ] Admin can see all payments
- [ ] Export payments to CSV works
- [ ] Static files load correctly
- [ ] Media files (QR codes, receipts) upload and display

---

## 🔄 Step 11: Updating the Application

### For Code Updates
```bash
cd /home/scout/BoyScout-Registration-System
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

### For Configuration Changes
```bash
nano .env  # Update environment variables
sudo systemctl restart gunicorn
```

---

## 🆘 Troubleshooting

### Application Not Loading
1. Check Gunicorn status: `sudo systemctl status gunicorn`
2. Check Nginx status: `sudo systemctl status nginx`
3. Check logs: `sudo tail -f /var/log/gunicorn/error.log`

### Webhook Not Working
1. Verify webhook URL is accessible: `curl -X POST https://yourdomain.com/payments/webhook/`
2. Check PayMongo dashboard for webhook delivery status
3. Verify webhook secret matches in `.env`
4. Check application logs for webhook errors

### Payment Not Verifying
1. Check PayMongo dashboard for transaction status
2. Verify webhook secret is correct
3. Check logs: `sudo tail -f /var/log/gunicorn/error.log`
4. Ensure PayMongo LIVE keys are configured

### Static Files Not Loading
1. Run: `python manage.py collectstatic --noinput`
2. Check Nginx configuration for `/static/` location
3. Verify file permissions: `ls -la staticfiles/`

### Database Connection Issues
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Test database connection: `psql -U boyscout_user -h localhost -d boyscout_db`
3. Check `.env` database credentials

---

## 📞 Support & Resources

- **PayMongo Dashboard**: https://dashboard.paymongo.com
- **PayMongo API Docs**: https://developers.paymongo.com
- **Django Documentation**: https://docs.djangoproject.com
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org

---

## ✅ Production Go-Live Checklist

Final checks before going live:

- [ ] All TEST mode testing completed successfully
- [ ] LIVE API keys configured
- [ ] Production webhook created and tested
- [ ] SSL certificate installed and valid
- [ ] Email notifications working
- [ ] Database backups configured
- [ ] Monitoring and logging setup
- [ ] Security hardening complete
- [ ] Small test transaction completed successfully
- [ ] Documentation updated
- [ ] Admin trained on new system
- [ ] Support email configured
- [ ] Emergency rollback plan ready

---

**🎉 Congratulations! Your ScoutConnect system with PayMongo integration is now live in production!**

**Remember:** Monitor the system closely for the first few days and be ready to respond to any issues quickly. Keep your API keys secure and never share them publicly.
