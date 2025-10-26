"""Add missing Event fields that may not exist in older DBs.

This migration is defensive: it checks whether each column exists and only
adds it when missing. That makes applying the migration safe for databases
that were manually patched earlier.
"""
from django.db import migrations


def add_event_columns_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    table = 'events_event'
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(%s);" % table)
        existing = [row[1] for row in cursor.fetchall()]

        # created_by_id (FK to users) - integer column
        if 'created_by_id' not in existing:
            cursor.execute("ALTER TABLE %s ADD COLUMN created_by_id INTEGER;" % table)
            # Set to default user id 1 for existing rows when possible
            try:
                cursor.execute("UPDATE %s SET created_by_id = 1 WHERE created_by_id IS NULL;" % table)
            except Exception:
                pass

        # created_at and updated_at
        if 'created_at' not in existing:
            cursor.execute("ALTER TABLE %s ADD COLUMN created_at DATETIME;" % table)
            try:
                cursor.execute("UPDATE %s SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;" % table)
            except Exception:
                pass

        if 'updated_at' not in existing:
            cursor.execute("ALTER TABLE %s ADD COLUMN updated_at DATETIME;" % table)
            try:
                cursor.execute("UPDATE %s SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;" % table)
            except Exception:
                pass


def noop_reverse(apps, schema_editor):
    # Not removing columns on reverse to avoid destructive changes in SQLite
    return


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_add_banner_field'),
    ]

    operations = [
        migrations.RunPython(add_event_columns_if_missing, reverse_code=noop_reverse),
    ]
