"""Rebuild events_eventregistration with a proper INTEGER PRIMARY KEY on `id`.

This migration is targeted at SQLite where the existing `id` column exists but
is not declared as the table primary key (causing Django model instances to
have `pk=None` after save). The migration recreates the table with the proper
PRIMARY KEY and copies rows across. It's guarded to run only on SQLite.
"""
from django.db import migrations


def fix_eventregistration_pk(apps, schema_editor):
    connection = schema_editor.connection
    if 'sqlite' not in connection.vendor:
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(events_eventregistration);")
        cols = cursor.fetchall()
        id_col = None
        for col in cols:
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            if col[1] == 'id':
                id_col = col
                break

        if id_col and id_col[5] == 1:
            # already correct
            return

        # Create new table with proper primary key
        cursor.execute('''
            CREATE TABLE events_eventregistration_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rsvp TEXT NOT NULL,
                receipt_image TEXT,
                registered_at DATETIME,
                verified BOOLEAN,
                verification_date DATETIME,
                event_id INTEGER,
                user_id INTEGER,
                verified_by_id INTEGER,
                payment_notes TEXT,
                payment_status TEXT,
                amount_required NUMERIC,
                total_paid NUMERIC
            );
        ''')

        # Copy existing data
        cursor.execute('''
            INSERT INTO events_eventregistration_new (id, rsvp, receipt_image, registered_at, verified, verification_date, event_id, user_id, verified_by_id, payment_notes, payment_status, amount_required, total_paid)
            SELECT id, rsvp, receipt_image, registered_at, verified, verification_date, event_id, user_id, verified_by_id, payment_notes, payment_status, amount_required, total_paid FROM events_eventregistration;
        ''')

        cursor.execute('DROP TABLE events_eventregistration;')
        cursor.execute('ALTER TABLE events_eventregistration_new RENAME TO events_eventregistration;')


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0013_fix_event_pk'),
    ]

    operations = [
        migrations.RunPython(fix_eventregistration_pk, reverse_code=noop_reverse),
    ]
