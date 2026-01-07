#!/usr/bin/env python
"""
Quick script to check available PayMongo payment methods
Run: python check_paymongo_methods.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')
django.setup()

from events.paymongo_service import PayMongoService
from django.conf import settings

def check_payment_methods():
    print("=" * 60)
    print("PayMongo Configuration Check")
    print("=" * 60)
    
    # Show current keys (masked)
    public_key = settings.PAYMONGO_PUBLIC_KEY
    secret_key = settings.PAYMONGO_SECRET_KEY
    
    if public_key.startswith('pk_test_'):
        print("⚠️  Using TEST keys")
    elif public_key.startswith('pk_live_'):
        print("✅ Using LIVE keys")
    else:
        print("❌ Invalid public key format")
    
    print(f"Public Key: {public_key[:15]}...{public_key[-4:]}")
    print(f"Secret Key: {secret_key[:15]}...{secret_key[-4:]}")
    print()
    
    # Test creating a small source with different payment methods
    paymongo = PayMongoService()
    
    payment_methods = ['gcash', 'paymaya', 'grab_pay']
    
    print("Testing Payment Methods:")
    print("-" * 60)
    
    for method in payment_methods:
        print(f"\nTesting {method.upper()}...")
        
        # Try to create a ₱100 source (minimum amount)
        result = paymongo.create_source(
            amount=100,  # ₱100
            type=method,
            redirect_success='https://example.com/success',
            redirect_failed='https://example.com/failed',
            metadata={'test': 'true'}
        )
        
        if result and isinstance(result, dict):
            if result.get('error'):
                print(f"  ❌ {method.upper()}: NOT AVAILABLE")
                print(f"  Error: {result.get('message')}")
            elif 'id' in result:
                print(f"  ✅ {method.upper()}: AVAILABLE")
                print(f"  Source ID: {result['id']}")
        else:
            print(f"  ❌ {method.upper()}: FAILED")
    
    print("\n" + "=" * 60)
    print("\nRecommendations:")
    print("-" * 60)
    
    if public_key.startswith('pk_test_'):
        print("• You're using TEST keys - all payment methods should work")
        print("• Test payments won't process real money")
    elif public_key.startswith('pk_live_'):
        print("• You're using LIVE keys")
        print("• Enable payment methods in PayMongo Dashboard:")
        print("  https://dashboard.paymongo.com/settings/payment-methods")
        print("• Complete business verification if not done")
        print("• Wait 1-3 days for approval after applying")
    
    print("\n")

if __name__ == '__main__':
    check_payment_methods()
