# Generated manually on 2026-01-07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_systemconfiguration_registration_fee_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfiguration',
            name='default_payment_method',
            field=models.CharField(
                choices=[('gcash', 'GCash'), ('paymaya', 'PayMaya'), ('grab_pay', 'GrabPay')],
                default='paymaya',
                help_text='Payment method to use for PayMongo (ensure this is enabled in your PayMongo dashboard)',
                max_length=20,
                verbose_name='Default Payment Method'
            ),
        ),
    ]
