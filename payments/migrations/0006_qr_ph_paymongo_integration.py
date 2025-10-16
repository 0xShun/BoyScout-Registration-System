# Generated migration for QR PH and PayMongo integration

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_payment_payments_pa_user_id_2ff331_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Update PaymentQRCode model
        migrations.AlterField(
            model_name='paymentqrcode',
            name='qr_code',
            field=models.ImageField(blank=True, null=True, upload_to='payment_qr_codes/', verbose_name='QR PH Code'),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='qr_ph_string',
            field=models.TextField(blank=True, help_text='EMVCo QR code data', verbose_name='QR PH Data String'),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='merchant_id',
            field=models.CharField(blank=True, max_length=100, verbose_name='Merchant ID'),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='merchant_name',
            field=models.CharField(blank=True, default='ScoutConnect', max_length=100, verbose_name='Merchant Name'),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='account_number',
            field=models.CharField(blank=True, max_length=50, verbose_name='Account Number'),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='gateway_provider',
            field=models.CharField(
                choices=[('paymongo', 'PayMongo'), ('manual', 'Manual QR PH')],
                default='paymongo',
                max_length=50,
                verbose_name='Payment Gateway'
            ),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='paymongo_public_key',
            field=models.CharField(blank=True, help_text='PayMongo Public Key', max_length=255),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='paymongo_secret_key',
            field=models.CharField(blank=True, help_text='PayMongo Secret Key (encrypted)', max_length=255),
        ),
        migrations.AddField(
            model_name='paymentqrcode',
            name='paymongo_webhook_secret',
            field=models.CharField(blank=True, help_text='PayMongo Webhook Secret', max_length=255),
        ),
        
        # Update Payment model
        migrations.RenameField(
            model_name='payment',
            old_name='gcash_receipt_image',
            new_name='receipt_image',
        ),
        migrations.AlterField(
            model_name='payment',
            name='receipt_image',
            field=models.ImageField(blank=True, null=True, upload_to='payment_receipts/', verbose_name='Payment Receipt'),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('qr_ph', 'QR PH'),
                    ('gcash', 'GCash (Legacy)'),
                    ('paymaya', 'PayMaya'),
                    ('bank_transfer', 'Bank Transfer'),
                    ('cash', 'Cash')
                ],
                default='qr_ph',
                max_length=50,
                verbose_name='Payment Method'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='qr_ph_reference',
            field=models.CharField(
                blank=True,
                help_text="Customer's payment reference number",
                max_length=100,
                verbose_name='QR PH Reference Number'
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='paymongo_payment_intent_id',
            field=models.CharField(blank=True, max_length=255, verbose_name='PayMongo Payment Intent ID'),
        ),
        migrations.AddField(
            model_name='payment',
            name='paymongo_payment_id',
            field=models.CharField(blank=True, max_length=255, verbose_name='PayMongo Payment ID'),
        ),
        migrations.AddField(
            model_name='payment',
            name='paymongo_source_id',
            field=models.CharField(blank=True, max_length=255, verbose_name='PayMongo Source ID'),
        ),
        migrations.AddField(
            model_name='payment',
            name='gateway_response',
            field=models.JSONField(
                blank=True,
                help_text='Full response from PayMongo API',
                null=True,
                verbose_name='Gateway Response Data'
            ),
        ),
    ]
