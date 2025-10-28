"""

PayMongo Payment Gateway Service
Handles integration with PayMongo API for QR PH payments
Documentation: https://developers.paymongo.com/
"""

import requests
import hmac
import hashlib
import base64
from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PayMongoService:
    """Service for integrating with PayMongo payment gateway"""
    
    BASE_URL = "https://api.paymongo.com/v1"
    
    def __init__(self, secret_key: str = None, public_key: str = None):
        """
        Initialize PayMongo service with API keys
        
        Args:
            secret_key: PayMongo secret key (defaults to settings)
            public_key: PayMongo public key (defaults to settings)
        """
        self.secret_key = secret_key or getattr(settings, 'PAYMONGO_SECRET_KEY', '')
        self.public_key = public_key or getattr(settings, 'PAYMONGO_PUBLIC_KEY', '')
        
        if not self.secret_key:
            logger.warning("PayMongo secret key not configured")
    
    def _get_auth_header(self, use_secret: bool = True) -> Dict[str, str]:
        """Generate authorization header for PayMongo API"""
        key = self.secret_key if use_secret else self.public_key
        encoded = base64.b64encode(f"{key}:".encode()).decode()
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }
    
    def create_source(self, amount: Decimal, description: str, 
                     redirect_success: str, redirect_failed: str,
                     metadata: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """
        Create a payment source for GCash/PayMaya/GrabPay
        
        Args:
            amount: Payment amount in PHP
            description: Payment description
            redirect_success: URL to redirect after successful payment
            redirect_failed: URL to redirect after failed payment
            metadata: Additional metadata
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            # In test mode we avoid calling the real PayMongo API and return a
            # deterministic fake source to keep tests hermetic and avoid external
            # network calls or browser interactions.
            from django.conf import settings as _dj_settings
            if getattr(_dj_settings, 'TESTING', False):
                fake_response = {
                    'data': {
                        'id': 'src_test_123',
                        'attributes': {
                            'redirect': {'checkout_url': redirect_success},
                            'amount': int(amount * 100),
                        }
                    }
                }
                return True, fake_response
            url = f"{self.BASE_URL}/sources"
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": int(amount * 100),  # Convert to centavos
                        "redirect": {
                            "success": redirect_success,
                            "failed": redirect_failed
                        },
                        "type": "gcash",  # Can be 'gcash', 'grab_pay', or 'paymaya'
                        "currency": "PHP",
                        "description": description,
                        "statement_descriptor": "ScoutConnect",
                        "metadata": metadata or {}
                    }
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"PayMongo source created successfully")
                return True, response.json()
            else:
                logger.error(f"PayMongo source creation failed: {response.text}")
                return False, response.json()
                
        except Exception as e:
            logger.error(f"PayMongo source creation error: {str(e)}")
            return False, {"error": str(e)}
    
    def create_payment(self, source_id: str, amount: Decimal, 
                      description: str, metadata: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """
        Create a payment using a source
        
        Args:
            source_id: ID of the created source
            amount: Payment amount in PHP
            description: Payment description
            metadata: Additional metadata
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            url = f"{self.BASE_URL}/payments"
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": int(amount * 100),  # Convert to centavos
                        "source": {
                            "id": source_id,
                            "type": "source"
                        },
                        "currency": "PHP",
                        "description": description,
                        "statement_descriptor": "ScoutConnect",
                        "metadata": metadata or {}
                    }
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"PayMongo payment created successfully")
                return True, response.json()
            else:
                logger.error(f"PayMongo payment creation failed: {response.text}")
                return False, response.json()
                
        except Exception as e:
            logger.error(f"PayMongo payment creation error: {str(e)}")
            return False, {"error": str(e)}
    
    def retrieve_payment(self, payment_id: str) -> Tuple[bool, Dict]:
        """
        Retrieve payment details
        
        Args:
            payment_id: PayMongo payment ID
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            url = f"{self.BASE_URL}/payments/{payment_id}"
            
            response = requests.get(
                url,
                headers=self._get_auth_header(),
                timeout=30
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"PayMongo payment retrieval failed: {response.text}")
                return False, response.json()
                
        except Exception as e:
            logger.error(f"PayMongo payment retrieval error: {str(e)}")
            return False, {"error": str(e)}

    def find_payment_by_source(self, source_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Find a payment object that references the given source_id.

        This performs a best-effort lookup by listing payments and matching
        the payment's source id. For small dev/testing workloads this is
        acceptable; production usage should use a more efficient server-side
        lookup if available from the gateway.

        Returns (True, payment_dict) when found, or (False, None) when not.
        """
        try:
            url = f"{self.BASE_URL}/payments"
            response = requests.get(url, headers=self._get_auth_header(), timeout=30)

            if response.status_code != 200:
                logger.error(f"PayMongo payments list failed: {response.text}")
                return False, None

            data = response.json()
            payments = data.get('data', [])

            for p in payments:
                try:
                    src = p.get('attributes', {}).get('source', {})
                    if src and src.get('id') == source_id:
                        return True, p
                except Exception:
                    continue

            # Not found in the current page
            return False, None

        except Exception as e:
            logger.error(f"Error finding payment by source: {str(e)}")
            return False, None
    
    def create_payment_intent(self, amount: Decimal, description: str,
                             payment_method_allowed: list = None,
                             metadata: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """
        Create a payment intent (for future use with PayMongo Checkout)
        
        Args:
            amount: Payment amount in PHP
            description: Payment description
            payment_method_allowed: List of allowed payment methods
            metadata: Additional metadata
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            url = f"{self.BASE_URL}/payment_intents"
            
            if payment_method_allowed is None:
                payment_method_allowed = ["gcash", "paymaya", "grab_pay"]
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": int(amount * 100),  # Convert to centavos
                        "payment_method_allowed": payment_method_allowed,
                        "currency": "PHP",
                        "description": description,
                        "statement_descriptor": "ScoutConnect",
                        "metadata": metadata or {}
                    }
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"PayMongo payment intent created successfully")
                return True, response.json()
            else:
                logger.error(f"PayMongo payment intent creation failed: {response.text}")
                return False, response.json()
                
        except Exception as e:
            logger.error(f"PayMongo payment intent creation error: {str(e)}")
            return False, {"error": str(e)}
    
    @staticmethod
    def verify_webhook_signature(payload: str, signature: str, 
                                 webhook_secret: str = None) -> bool:
        """
        Verify webhook signature from PayMongo
        
        Args:
            payload: Raw request body as string
            signature: Paymongo-Signature header value
            webhook_secret: Webhook secret key
            
        Returns:
            Boolean indicating if signature is valid
        """
        webhook_secret = webhook_secret or getattr(settings, 'PAYMONGO_WEBHOOK_SECRET', '')
        
        if not webhook_secret:
            logger.warning("PayMongo webhook secret not configured")
            return False
        
        try:
            # Extract timestamp and signatures from header
            parts = dict(part.split('=') for part in signature.split(','))
            timestamp = parts.get('t')
            signatures = parts.get('li') or parts.get('test_li')
            
            if not timestamp or not signatures:
                return False
            
            # Compute expected signature
            signed_payload = f"{timestamp}.{payload}"
            expected_signature = hmac.new(
                webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant-time comparison)
            return hmac.compare_digest(expected_signature, signatures)
            
        except Exception as e:
            logger.error(f"Webhook signature verification error: {str(e)}")
            return False
    
    def create_webhook(self, url: str, events: list = None) -> Tuple[bool, Dict]:
        """
        Create a webhook endpoint
        
        Args:
            url: Your webhook URL
            events: List of events to listen to
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            api_url = f"{self.BASE_URL}/webhooks"
            
            if events is None:
                events = [
                    "source.chargeable",
                    "payment.paid",
                    "payment.failed"
                ]
            
            payload = {
                "data": {
                    "attributes": {
                        "url": url,
                        "events": events
                    }
                }
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"PayMongo webhook created successfully")
                return True, response.json()
            else:
                logger.error(f"PayMongo webhook creation failed: {response.text}")
                return False, response.json()
                
        except Exception as e:
            logger.error(f"PayMongo webhook creation error: {str(e)}")
            return False, {"error": str(e)}
