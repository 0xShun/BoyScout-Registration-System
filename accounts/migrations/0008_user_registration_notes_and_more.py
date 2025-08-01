# Generated by Django 5.1.2 on 2025-07-30 16:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_badge_userbadge'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='registration_notes',
            field=models.TextField(blank=True, verbose_name='Registration Notes'),
        ),
        migrations.AddField(
            model_name='user',
            name='registration_payment_amount',
            field=models.DecimalField(decimal_places=2, default=500.0, max_digits=10, verbose_name='Registration Fee'),
        ),
        migrations.AddField(
            model_name='user',
            name='registration_receipt',
            field=models.ImageField(blank=True, null=True, upload_to='registration_receipts/', verbose_name='Registration Payment Receipt'),
        ),
        migrations.AddField(
            model_name='user',
            name='registration_status',
            field=models.CharField(choices=[('pending_payment', 'Pending Registration Payment'), ('payment_submitted', 'Registration Payment Submitted'), ('payment_verified', 'Registration Payment Verified'), ('active', 'Active Member'), ('inactive', 'Inactive')], default='pending_payment', max_length=30),
        ),
        migrations.AddField(
            model_name='user',
            name='registration_verification_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='registration_verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_registrations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
