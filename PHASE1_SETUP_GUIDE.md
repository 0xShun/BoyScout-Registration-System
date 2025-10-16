# QR PH and PayMongo Integration - Phase 1 Setup Guide

## Overview
This guide covers the implementation of Phase 1: Database schema changes and PayMongo integration setup for QR PH payments.

## What Was Implemented

### 1. Database Schema Updates

#### PaymentQRCode Model
New fields added:
- `qr_ph_string`: Stores the EMVCo-compliant QR code data string
- `merchant_id`: Merchant identification code
- `merchant_name`: Business/merchant name (default: "ScoutConnect")
- `account_number`: Bank account or mobile number for payments
- `gateway_provider`: Payment gateway selection ('paymongo' or 'manual')
- `paymongo_public_key`: PayMongo public API key
- `paymongo_secret_key`: PayMongo secret API key (should be encrypted)
- `paymongo_webhook_secret`: Secret for verifying webhook signatures

#### Payment Model
New fields added:
- `payment_method`: Type of payment (qr_ph, gcash, paymaya, bank_transfer, cash)
- `qr_ph_reference`: Customer's payment reference number
- `paymongo_payment_intent_id`: PayMongo payment intent ID
- `paymongo_payment_id`: PayMongo payment ID
- `paymongo_source_id`: PayMongo source ID (for GCash/PayMaya/GrabPay)
- `gateway_response`: JSON field storing full PayMongo API response

Field renamed:
- `gcash_receipt_image` → `receipt_image` (more generic name)

### 2. Service Layer

#### PayMongoService (`payments/services/paymongo_service.py`)
Handles all PayMongo API interactions:
- `create_source()`: Create payment source for GCash/PayMaya/GrabPay
- `create_payment()`: Create payment using a source
- `retrieve_payment()`: Get payment details
- `create_payment_intent()`: Create payment intent (for future checkout)
- `verify_webhook_signature()`: Verify PayMongo webhook signatures
- `create_webhook()`: Register webhook endpoint with PayMongo

#### QRPHService (`payments/services/qr_ph_service.py`)
Generates QR PH compliant QR codes:
- `generate_emvco_qr_string()`: Generate EMVCo-compliant QR string
- `generate_qr_code_image()`: Create QR code image from string
- `create_payment_qr_code()`: Complete QR code generation (string + image)
- `_calculate_crc16_ccitt()`: Calculate CRC checksum for QR codes
- `_format_tlv()`: Format Tag-Length-Value data

### 3. Configuration Updates

#### Settings (`boyscout_system/settings.py`)
New settings added:
```python
# PayMongo Payment Gateway
PAYMONGO_PUBLIC_KEY = os.environ.get('PAYMONGO_PUBLIC_KEY', '')
PAYMONGO_SECRET_KEY = os.environ.get('PAYMONGO_SECRET_KEY', '')
PAYMONGO_WEBHOOK_SECRET = os.environ.get('PAYMONGO_WEBHOOK_SECRET', '')

# QR PH Payment Settings
QRPH_MERCHANT_ID = os.environ.get('QRPH_MERCHANT_ID', '')
QRPH_MERCHANT_NAME = os.environ.get('QRPH_MERCHANT_NAME', 'ScoutConnect')
QRPH_ACCOUNT_NUMBER = os.environ.get('QRPH_ACCOUNT_NUMBER', '')
QRPH_MERCHANT_CITY = os.environ.get('QRPH_MERCHANT_CITY', 'Manila')
```

#### Environment Variables (`.env.example`)
New variables added:
```bash
# PayMongo Payment Gateway
PAYMONGO_PUBLIC_KEY=pk_test_your_public_key_here
PAYMONGO_SECRET_KEY=sk_test_your_secret_key_here
PAYMONGO_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# QR PH Settings
QRPH_MERCHANT_ID=your_merchant_id
QRPH_MERCHANT_NAME=ScoutConnect
QRPH_ACCOUNT_NUMBER=your_account_number
QRPH_MERCHANT_CITY=Manila
```

#### Requirements (`requirements.txt`)
New dependency added:
```
qrcode[pil]>=7.4.2
```

## Next Steps to Complete Phase 1

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Set Up PayMongo Account

#### Create Account
1. Go to https://dashboard.paymongo.com/signup
2. Sign up for a PayMongo account
3. Complete business verification (required for production)

#### Get API Keys
1. Log in to PayMongo Dashboard
2. Go to **Developers** → **API Keys**
3. Copy your test keys:
   - Public Key (starts with `pk_test_`)
   - Secret Key (starts with `sk_test_`)

#### Configure Webhooks
1. In PayMongo Dashboard, go to **Developers** → **Webhooks**
2. Create a new webhook endpoint
3. Set URL to: `https://yourdomain.com/payments/webhook/`
4. Subscribe to events:
   - `source.chargeable`
   - `payment.paid`
   - `payment.failed`
5. Copy the webhook secret (starts with `whsec_`)

### 4. Update Environment Variables

Create/update your `.env` file:
```bash
# Copy from example
cp .env.example .env

# Edit .env and add your PayMongo credentials
nano .env
```

Add your actual PayMongo keys:
```bash
PAYMONGO_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
PAYMONGO_SECRET_KEY=sk_test_xxxxxxxxxxxxx
PAYMONGO_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

QRPH_MERCHANT_ID=YOUR_MERCHANT_ID
QRPH_MERCHANT_NAME=ScoutConnect
QRPH_ACCOUNT_NUMBER=09xxxxxxxxx
QRPH_MERCHANT_CITY=Manila
```

### 5. Test the Services

Create a test script to verify the services work:

```python
# test_paymongo_integration.py
from payments.services import PayMongoService, QRPHService
from decimal import Decimal

# Test QR PH generation
print("Testing QR PH generation...")
qr_string, qr_image = QRPHService.create_payment_qr_code(
    merchant_id="SCOUT001",
    merchant_name="ScoutConnect",
    account_number="09171234567",
    amount=Decimal("500.00"),
    reference="TEST001"
)
print(f"QR String generated: {qr_string[:50]}...")
print(f"QR Image size: {len(qr_image.read())} bytes")

# Test PayMongo connection
print("\nTesting PayMongo connection...")
paymongo = PayMongoService()
success, response = paymongo.create_source(
    amount=Decimal("500.00"),
    description="Test Payment",
    redirect_success="http://localhost:8000/payments/success/",
    redirect_failed="http://localhost:8000/payments/failed/",
    metadata={"test": True}
)
print(f"PayMongo API test: {'SUCCESS' if success else 'FAILED'}")
if success:
    print(f"Source ID: {response['data']['id']}")
else:
    print(f"Error: {response}")
```

Run the test:
```bash
python test_paymongo_integration.py
```

## Migration Notes

### Backward Compatibility
- Old `gcash_receipt_image` field renamed to `receipt_image`
- Existing data will be preserved during migration
- Legacy payments will still work with new schema

### Data Migration
The migration automatically:
1. Renames `gcash_receipt_image` to `receipt_image`
2. Adds new fields with blank/null defaults
3. Preserves all existing payment records

### Zero Downtime
- All new fields are optional (blank=True)
- No data loss during migration
- Existing functionality remains intact

## Security Considerations

### API Key Storage
⚠️ **IMPORTANT**: Never commit API keys to version control
- Use environment variables for all keys
- The `.env` file should be in `.gitignore`
- Consider encrypting `paymongo_secret_key` in database

### Webhook Security
- Always verify webhook signatures before processing
- Use HTTPS for webhook endpoints in production
- Implement rate limiting on webhook endpoint

### Database Security
- PayMongo keys in database should be encrypted
- Limit admin access to sensitive payment fields
- Log all payment gateway interactions for audit trail

## Testing Checklist

- [ ] Dependencies installed successfully
- [ ] Migrations applied without errors
- [ ] PayMongo account created
- [ ] Test API keys obtained
- [ ] Environment variables configured
- [ ] QR PH service generates valid QR codes
- [ ] PayMongo service connects successfully
- [ ] Webhook endpoint created in dashboard
- [ ] Webhook signature verification works

## Troubleshooting

### Migration Errors
If you encounter migration errors:
```bash
# Reset migrations (WARNING: Only in development!)
python manage.py migrate payments zero
python manage.py migrate payments
```

### API Connection Errors
- Verify API keys are correct
- Check internet connectivity
- Ensure you're using test keys for development
- Check PayMongo dashboard for API status

### QR Code Generation Errors
- Verify qrcode library is installed: `pip show qrcode`
- Check Pillow is installed: `pip show Pillow`
- Ensure merchant details are properly formatted

## What's Next

Phase 2 will cover:
- Updating forms to support new payment methods
- Modifying views for PayMongo integration
- Creating webhook handler endpoint
- Updating templates with QR PH branding
- Testing end-to-end payment flow

## Resources

- PayMongo Documentation: https://developers.paymongo.com/
- QR PH Standard: https://www.bsp.gov.ph/Regulations/Issuances/2019/c1055.pdf
- EMVCo QR Specification: https://www.emvco.com/emv-technologies/qrcodes/

## Support

For issues or questions:
1. Check PayMongo documentation
2. Review migration file for any conflicts
3. Test in development environment first
4. Contact PayMongo support for API issues
