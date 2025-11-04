#!/usr/bin/env python
"""List all users in the database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from accounts.models import User

print('=' * 120)
print('DATABASE USER ACCOUNTS')
print('=' * 120)

users = User.objects.all().order_by('rank', 'id')
print(f'\nTotal Users: {users.count()}\n')

for u in users:
    print(f'ID: {u.id:3d} | Username: {u.username:20s} | Email: {u.email:40s}')
    print(f'       Name: {u.get_full_name():30s} | Rank: {u.role:10s}')
    print(f'       Active: {str(u.is_active):5s} | Reg Complete: {str(u.is_registration_complete):5s} | Status: {u.registration_status}')
    print('-' * 120)

print('\n=== ADMIN ACCOUNTS ===')
admins = users.filter(role='admin')
for admin in admins:
    print(f'  - {admin.username} ({admin.email})')

print('\n=== SCOUT ACCOUNTS ===')
scouts = users.filter(role='scout')
for scout in scouts:
    status = "✓ Active" if scout.is_active and scout.is_registration_complete else "✗ Inactive/Pending"
    print(f'  - {scout.username} ({scout.email}) - {status}')
