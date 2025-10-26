#!/usr/bin/env python3
"""Activate a user by email for testing.

Usage: python scripts/activate_user.py user@example.com
"""
import os
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')

import django
django.setup()

from accounts.models import User
from django.utils import timezone


def activate_user(email):
    qs = User.objects.filter(email=email)
    if not qs.exists():
        print(f"User with email {email} not found.")
        return 2

    u = qs.first()
    u.is_active = True
    u.registration_status = 'active'
    # If there are registration payment fields, update them
    try:
        # Some projects use registration verification fields - try to set them if present
        if hasattr(u, 'registration_verification_date'):
            setattr(u, 'registration_verification_date', timezone.now())
        if hasattr(u, 'registration_verified_by'):
            setattr(u, 'registration_verified_by', None)
    except Exception:
        pass
    u.save()
    print(f"Activated user id={u.pk} email={u.email}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/activate_user.py user@example.com')
        sys.exit(1)
    email = sys.argv[1]
    sys.exit(activate_user(email))
