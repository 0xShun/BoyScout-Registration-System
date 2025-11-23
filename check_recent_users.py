#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check recent user registrations to debug the teacher role issue
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def check_recent_users():
    """Check the most recent user registrations"""
    
    print("\n" + "="*80)
    print("RECENT USER REGISTRATIONS")
    print("="*80)
    
    # Get last 10 users
    users = User.objects.all().order_by('-date_joined')[:10]
    
    print(f"\nFound {users.count()} recent users:\n")
    
    for user in users:
        print(f"ID: {user.id}")
        print(f"  Name: {user.get_full_name()}")
        print(f"  Email: {user.email}")
        print(f"  Username: {user.username}")
        print(f"  Role: {user.role}")
        print(f"  Rank (deprecated): {user.rank}")
        print(f"  Is Active: {user.is_active}")
        print(f"  Registration Status: {user.registration_status}")
        print(f"  Is Staff: {user.is_staff}")
        print(f"  Is Superuser: {user.is_superuser}")
        print(f"  Date Joined: {user.date_joined}")
        print(f"  Has .edu email: {'.edu' in user.email.lower()}")
        print("-" * 80)
    
    # Check for teachers specifically
    teachers = User.objects.filter(role='teacher').order_by('-date_joined')
    print(f"\n\nTeachers in system: {teachers.count()}")
    for teacher in teachers:
        print(f"  - {teacher.get_full_name()} ({teacher.email}) - Joined: {teacher.date_joined}")
    
    # Check for scouts with .edu emails (might be misidentified teachers)
    scouts_with_edu = User.objects.filter(role='scout', email__icontains='.edu').order_by('-date_joined')
    if scouts_with_edu.exists():
        print(f"\n\n⚠️  POTENTIAL BUG: Scouts with .edu emails: {scouts_with_edu.count()}")
        for scout in scouts_with_edu:
            print(f"  - {scout.get_full_name()} ({scout.email}) - Role: {scout.role} - Joined: {scout.date_joined}")
            print(f"    This user has a .edu email but role is 'scout' instead of 'teacher'!")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    check_recent_users()
