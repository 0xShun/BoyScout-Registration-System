#!/usr/bin/env python
"""
Fix admin2@test.com role from 'scout' to 'admin'
Run this script on PythonAnywhere after pulling the latest code.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from accounts.models import User

def fix_admin2_role():
    try:
        user = User.objects.get(email='admin2@test.com')
        print(f"\nFound user: {user.username} ({user.email})")
        print(f"Current role: {user.role}")
        print(f"Current rank (deprecated): {user.rank}")
        print(f"Is superuser: {user.is_superuser}")
        print(f"Is staff: {user.is_staff}")
        
        if user.role != 'admin':
            print(f"\n✅ Updating role from '{user.role}' to 'admin'...")
            user.role = 'admin'
            user.is_staff = True  # Admins should have staff access
            user.is_superuser = True  # Admins should be superusers
            user.save()
            print("✅ Role updated successfully!")
            print(f"New role: {user.role}")
            print(f"New rank (auto-synced): {user.rank}")
        else:
            print("\n✅ User already has 'admin' role - no changes needed.")
            
    except User.DoesNotExist:
        print("❌ Error: User with email 'admin2@test.com' not found.")
        print("\nAvailable users:")
        for u in User.objects.filter(email__icontains='admin').order_by('email'):
            print(f"  - {u.email}: role={u.role}, is_superuser={u.is_superuser}")

if __name__ == '__main__':
    fix_admin2_role()
