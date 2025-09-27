from django.db import migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_registrationpayment_accounts_re_user_id_00803b_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, region='PH', max_length=128),
        ),
        migrations.AlterField(
            model_name='user',
            name='emergency_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, region='PH', max_length=128),
        ),
    ]
