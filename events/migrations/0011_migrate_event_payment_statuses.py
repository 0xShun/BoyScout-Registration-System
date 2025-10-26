"""No-op migration placeholder to satisfy historical dependency.

The repository has a migration `0012_remove_event_qr_code_eventpayment_payment_method_and_more`
that depends on `0011_migrate_event_payment_statuses`, but that file was missing in this
working copy. Adding this no-op migration restores the migration graph consistency.

If you have the original `0011` migration content from another branch or backup,
replace this file with the real migration. This placeholder intentionally performs
no operations.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_add_missing_event_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='qr_code',
            field=models.ImageField(blank=True, null=True, upload_to='event_qr_codes/'),
        ),
    ]
