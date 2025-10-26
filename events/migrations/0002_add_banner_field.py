"""Migration to ensure the `banner` column exists on `events_event`.

We add a guarded RunPython operation so applying this migration is safe even
if the column was manually added to the SQLite database (or already present
for other reasons). The forward step will add the column only when it's
missing. The reverse step is a no-op because removing a column in SQLite is
non-trivial and not necessary for this fix.
"""
from django.db import migrations


def add_banner_if_missing(apps, schema_editor):
    # Use raw SQL to check for column presence and add if missing.
    connection = schema_editor.connection
    table_name = 'events_event'
    column_name = 'banner'

    with connection.cursor() as cursor:
        # Check existing columns
        cursor.execute("PRAGMA table_info(%s);" % table_name)
        columns = [row[1] for row in cursor.fetchall()]
        if column_name in columns:
            return  # already present

        # Add the column (TEXT will hold the image file path). Keep it nullable.
        cursor.execute("ALTER TABLE %s ADD COLUMN %s TEXT;" % (table_name, column_name))


def noop_reverse(apps, schema_editor):
    # Intentionally do nothing on reverse; dropping columns in SQLite is complex.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_banner_if_missing, reverse_code=noop_reverse),
    ]
