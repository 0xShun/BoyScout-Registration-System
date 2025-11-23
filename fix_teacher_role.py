#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix script to convert a scout account to a teacher account
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

def fix_teacher_role():
    """Convert a scout account with .edu email to teacher"""
    
    print("\n" + "="*80)
    print("FIX TEACHER ROLE - Convert Scout to Teacher")
    print("="*80)
    
    # Find scouts with .edu emails (likely teachers who used wrong form)
    scouts_with_edu = User.objects.filter(role='scout', email__icontains='.edu')
    
    if not scouts_with_edu.exists():
        print("\n✓ No scouts with .edu emails found.")
        print("  All accounts appear to be correctly classified.")
        return
    
    print(f"\n Found {scouts_with_edu.count()} scout account(s) with .edu email:\n")
    
    for i, user in enumerate(scouts_with_edu, 1):
        print(f"{i}. {user.get_full_name()} ({user.email})")
        print(f"   ID: {user.id}")
        print(f"   Current Role: {user.role}")
        print(f"   Date Joined: {user.date_joined}")
        print()
    
    # Auto-fix if only one account
    if scouts_with_edu.count() == 1:
        user = scouts_with_edu.first()
        print(f"Converting user {user.get_full_name()} from scout to teacher...")
        
        user.role = 'teacher'
        user.rank = 'teacher'  # Sync deprecated field
        user.save()
        
        print(f"\n✓ SUCCESS! User {user.get_full_name()} is now a teacher.")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
        print(f"  You can now login and access teacher features.")
        
    else:
        # Multiple accounts - ask which one to fix
        print("Multiple accounts found. Please specify which one to convert.")
        print("Run this script with the email as argument:")
        print(f"  python fix_teacher_role.py <email>")
        
        if len(sys.argv) > 1:
            email = sys.argv[1]
            user = scouts_with_edu.filter(email=email).first()
            
            if user:
                print(f"\nConverting {user.get_full_name()} ({email}) to teacher...")
                user.role = 'teacher'
                user.rank = 'teacher'
                user.save()
                print(f"✓ SUCCESS! {user.get_full_name()} is now a teacher.")
            else:
                print(f"✗ No scout account found with email: {email}")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    fix_teacher_role()
