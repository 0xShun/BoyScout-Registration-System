#!/usr/bin/env python
"""Fix the superuser account"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from accounts.models import User

# Get the user
user = User.objects.get(email='admin@test.com')

# Fix all the issues
user.is_active = True
user.rank = 'admin'
user.registration_status = 'active'
user.save()

print('✅ Superuser account fixed!')
print('=' * 60)
print(f'Username: {user.username}')
print(f'Email: {user.email}')
print(f'Is active: {user.is_active}')
print(f'Rank: {user.rank}')
print(f'Is superuser: {user.is_superuser}')
print(f'Registration complete: {user.is_registration_complete}')
print(f'Registration status: {user.registration_status}')
print('=' * 60)
print('\n✅ You can now login with:')
print(f'   Username: {user.username}')
print(f'   Password: [the password you entered]')
print(f'\n🔗 Login URL: http://localhost:8000/accounts/login/')
