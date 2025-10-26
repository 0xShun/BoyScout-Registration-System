#!/usr/bin/env python3
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
# Ensure project root is on PYTHONPATH so Django can import settings
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

django.setup()

from django.test import Client
from accounts.models import User
from events.models import Event
from django.utils import timezone


def run():
    print('Starting smoke test: create event and fetch detail')

    # Ensure admin user exists
    admin, created = User.objects.get_or_create(username='smoke_admin', defaults={
        'email': 'smoke_admin@test.com',
        'first_name': 'Smoke',
        'last_name': 'Tester',
        'rank': 'admin',
        'is_active': True,
    })
    if created:
        # Set an unusable password and mark superuser flags for safety
        admin.set_password('password')
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()
        print('Created admin user smoke_admin')
    else:
        print('Admin user exists')

    # Create an event via ORM
    try:
        event = Event.objects.create(
            title='Smoke Test Event',
            description='Event created by smoke test',
            date=timezone.now().date(),
            time=timezone.now().time(),
            location='Test Location',
            created_by=admin,
        )
        print(f'Event object returned, pk={event.pk}')
        if not event.pk:
            print('ERROR: event.pk is None after save')
            # Dump table info for debugging
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA table_info(events_event);")
                print('events_event schema:')
                for row in cursor.fetchall():
                    print(row)
                cursor.execute('SELECT COUNT(*) FROM events_event;')
                print('rows in events_event:', cursor.fetchone()[0])
            sys.exit(2)
    except Exception as e:
        import traceback
        print('Exception while creating event:')
        traceback.print_exc()
        sys.exit(4)

    # Use test client and force_login to fetch event detail
    client = Client()
    client.force_login(admin)
    # Use HTTP_HOST to avoid DisallowedHost when test client uses 'testserver'
    resp = client.get(f'/events/{event.pk}/', HTTP_HOST='127.0.0.1')
    print('GET /events/<pk>/ returned status', resp.status_code)
    if resp.status_code == 200:
        print('SMOKE TEST PASSED: event detail is reachable')
        sys.exit(0)
    else:
        print('SMOKE TEST FAILED: status', resp.status_code)
        print(resp.content.decode('utf-8')[:2000])
        sys.exit(3)


if __name__ == '__main__':
    run()
