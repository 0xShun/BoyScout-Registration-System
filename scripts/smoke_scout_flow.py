#!/usr/bin/env python3
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

django.setup()

from django.test import Client
from accounts.models import User
from events.models import Event
from django.utils import timezone
from decimal import Decimal


def run():
    print('Starting scout smoke test: zhang access to events')

    # Ensure scout user exists and is properly set
    scout_email = 'zhang@test.com'
    scout, created = User.objects.get_or_create(email=scout_email, defaults={
        'username': 'zhang',
        'first_name': 'Zhang',
        'last_name': 'Tester',
        'rank': 'scout',
        'is_active': True,
    'registration_status': 'active',
        'registration_total_paid': Decimal('500.00'),
        'registration_amount_required': Decimal('500.00'),
    })

    if not created:
        # Update to ensure correct state
        changed = False
        if scout.username != 'zhang':
            scout.username = 'zhang'
            changed = True
        if scout.rank != 'scout':
            scout.rank = 'scout'
            changed = True
        if not scout.is_active:
            scout.is_active = True
            changed = True
        if scout.registration_status != 'active':
            scout.registration_status = 'active'
            changed = True
        if scout.registration_total_paid < scout.registration_amount_required:
            scout.registration_total_paid = scout.registration_amount_required
            changed = True
        if changed:
            scout.save()
            print('Updated scout user state')

    print(f'Scout user id={scout.pk}, status={scout.registration_status}, paid={scout.registration_total_paid}')

    # Ensure at least one event exists
    event = Event.objects.order_by('-created_at').first()
    if not event:
        # Use an admin as creator if exists, else use the scout as fallback
        admin = User.objects.filter(rank='admin').first() or scout
        event = Event.objects.create(
            title='Public Smoke Event',
            description='Auto-created event for smoke test',
            date=timezone.now().date(),
            time=timezone.now().time(),
            location='Test Venue',
            created_by=admin,
        )
        print(f'Created event id={event.pk}')
    else:
        print(f'Using existing event id={event.pk}')

    # Use test client to login as scout
    client = Client()
    client.force_login(scout)

    # Access event list
    resp = client.get('/events/', HTTP_HOST='127.0.0.1')
    print('/events/ status', resp.status_code)
    if resp.status_code != 200:
        print('Failed to access events list, response body (first 400 chars):')
        print(resp.content.decode('utf-8')[:400])
        sys.exit(2)

    # Access calendar data
    resp2 = client.get('/events/calendar-data/', HTTP_HOST='127.0.0.1')
    print('/events/calendar-data/ status', resp2.status_code)
    if resp2.status_code != 200:
        print('Failed to access calendar data, response body (first 400 chars):')
        print(resp2.content.decode('utf-8')[:400])
        sys.exit(3)

    print('SCOUT SMOKE TEST PASSED: zhang can access events list and calendar data')
    sys.exit(0)


if __name__ == '__main__':
    run()
