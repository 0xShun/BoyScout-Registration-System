"""
PayMongo API Integration Service
Handles PayMongo Sources API for QR code payments (GCash, Maya, GrabPay)
"""
import requests
import base64
import hashlib
import hmac
import json
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal


class PayMongoService:
    BASE_URL = "https://api.paymongo.com/v1"
    
    def __init__(self):
        self.secret_key = settings.PAYMONGO_SECRET_KEY
        self.public_key = settings.PAYMONGO_PUBLIC_KEY
        self.webhook_secret = settings.PAYMONGO_WEBHOOK_SECRET
    
    def _get_auth_header(self):
        """Generate Basic Auth header for PayMongo API"""
        credentials = f"{self.secret_key}:"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }
    
    def create_source(self, amount, type='gcash', redirect_success=None, redirect_failed=None, metadata=None):
        """
        Create a PayMongo Source for QR code payment
        
        Args:
            amount (Decimal): Payment amount in pesos
            type (str): Payment method type (gcash, paymaya, grab_pay)
            redirect_success (str): Success redirect URL
            redirect_failed (str): Failed redirect URL
            metadata (dict): Additional metadata
        
        Returns:
            dict: PayMongo source response or None if failed
        """
        # Convert amount to centavos (PayMongo uses smallest currency unit)
        amount_centavos = int(amount * 100)
        
        # Source expires in 1 hour
        expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
        
        # Extract user info from metadata if provided
        user_email = metadata.get('user_email', '') if metadata else ''
        registration_id = metadata.get('registration_id', '') if metadata else ''
        
        payload = {
            "data": {
                "attributes": {
                    "type": type,  # gcash, grab_pay, or paymaya
                    "amount": amount_centavos,
                    "currency": "PHP",
                    "redirect": {
                        "success": redirect_success,
                        "failed": redirect_failed
                    },
                    "metadata": metadata or {}
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/sources",
                headers=self._get_auth_header(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"PayMongo create_source error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def create_payment(self, source_id, description):
        """
        Create a Payment from a chargeable Source
        Called when source.chargeable webhook is received
        
        Args:
            source_id (str): PayMongo source ID
            description (str): Payment description
        
        Returns:
            dict: PayMongo payment response or None if failed
        """
        payload = {
            "data": {
                "attributes": {
                    "amount": None,  # Will use the source amount
                    "source": {
                        "id": source_id,
                        "type": "source"
                    },
                    "currency": "PHP",
                    "description": description
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/payments",
                headers=self._get_auth_header(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"PayMongo create_payment error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def verify_webhook_signature(self, payload, signature):
        """
        Verify PayMongo webhook signature for security
        
        Args:
            payload (bytes): Raw request body
            signature (str): Signature from request headers
        
        Returns:
            bool: True if signature is valid
        """
        if not signature or not self.webhook_secret:
            return False
        
        # Extract timestamp and signatures from header
        # Format: t=timestamp,te=test_signature,li=live_signature
        parts = {}
        for part in signature.split(','):
            key, value = part.split('=', 1)
            parts[key] = value
        
        timestamp = parts.get('t', '')
        test_sig = parts.get('te', '')
        live_sig = parts.get('li', '')
        
        # Construct the signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        
        # Compute expected signature
        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare with provided signature (test or live)
        return hmac.compare_digest(expected_sig, test_sig) or hmac.compare_digest(expected_sig, live_sig)
    
    def get_source(self, source_id):
        """
        Retrieve a source by ID
        
        Args:
            source_id (str): PayMongo source ID
        
        Returns:
            dict: Source data or None
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/sources/{source_id}",
                headers=self._get_auth_header(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"PayMongo get_source error: {e}")
            return None
    
    def get_payment(self, payment_id):
        """
        Retrieve a payment by ID
        
        Args:
            payment_id (str): PayMongo payment ID
        
        Returns:
            dict: Payment data or None
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/payments/{payment_id}",
                headers=self._get_auth_header(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"PayMongo get_payment error: {e}")
            return None
