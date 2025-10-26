"""Fix events_event primary key.

Some databases (particularly when schema was manually altered) may have the
`id` column present but not declared as the table primary key. That causes
Django ORM to never receive an `id` value on save. This migration recreates
the `events_event` table with a proper integer primary key and copies data
over. The operation is guarded to only run on SQLite, since other backends
shouldn't need this workaround.
"""
from django.db import migrations


def fix_pk(apps, schema_editor):
    connection = schema_editor.connection
    if 'sqlite' not in connection.vendor:
        # Only apply the complex table rebuild for SQLite in this migration.
        return

    with connection.cursor() as cursor:
        # Check current schema to see if id is primary key
        cursor.execute("PRAGMA table_info(events_event);")
        cols = cursor.fetchall()
        id_col = None
        for col in cols:
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            if col[1] == 'id':
                id_col = col
                break

        if id_col and id_col[5] == 1:
            # already primary key
            return

        # Recreate table with proper primary key and copy data
        cursor.execute('''
            CREATE TABLE events_event_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                location TEXT NOT NULL,
                banner TEXT,
                payment_amount NUMERIC,
                created_by_id INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            );
        ''')

        # Copy existing data; use the old id values when present
        cursor.execute('''
            INSERT INTO events_event_new (id, title, description, date, time, location, banner, payment_amount, created_by_id, created_at, updated_at)
            SELECT id, title, description, date, time, location, banner, payment_amount, created_by_id, created_at, updated_at FROM events_event;
        ''')

        cursor.execute('DROP TABLE events_event;')
        cursor.execute('ALTER TABLE events_event_new RENAME TO events_event;')


def noop_reverse(apps, schema_editor):
    # Not reversing this destructive operation.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0012_remove_event_qr_code_eventpayment_payment_method_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_pk, reverse_code=noop_reverse),
    ]
