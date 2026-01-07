# Generated manually on 2026-01-07
# Data migration to update existing SystemConfiguration to use gcash

from django.db import migrations


def update_payment_method_to_gcash(apps, schema_editor):
    """Update any existing SystemConfiguration records to use gcash instead of paymaya"""
    SystemConfiguration = apps.get_model('payments', 'SystemConfiguration')
    SystemConfiguration.objects.filter(default_payment_method='paymaya').update(default_payment_method='gcash')
    # Also update the singleton config if it exists
    try:
        config = SystemConfiguration.objects.get(pk=1)
        if config.default_payment_method == 'paymaya':
            config.default_payment_method = 'gcash'
            config.save()
    except SystemConfiguration.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0009_alter_systemconfiguration_default_payment_method'),
    ]

    operations = [
        migrations.RunPython(update_payment_method_to_gcash, reverse_code=migrations.RunPython.noop),
    ]
