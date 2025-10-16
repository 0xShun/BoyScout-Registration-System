from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class PaymentQRCode(models.Model):
    """Model to store QR PH payment codes"""
    qr_code = models.ImageField(upload_to='payment_qr_codes/', verbose_name="QR PH Code", blank=True, null=True)
    title = models.CharField(max_length=100, default="General Payment QR Code", verbose_name="QR Code Title")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_qr_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # QR PH specific fields
    qr_ph_string = models.TextField(verbose_name="QR PH Data String", blank=True, help_text="EMVCo QR code data")
    merchant_id = models.CharField(max_length=100, blank=True, verbose_name="Merchant ID")
    merchant_name = models.CharField(max_length=100, blank=True, verbose_name="Merchant Name", default="ScoutConnect")
    account_number = models.CharField(max_length=50, blank=True, verbose_name="Account Number")
    
    # PayMongo integration fields
    gateway_provider = models.CharField(
        max_length=50, 
        choices=[
            ('paymongo', 'PayMongo'),
            ('manual', 'Manual QR PH')
        ], 
        default='paymongo',
        verbose_name="Payment Gateway"
    )
    paymongo_public_key = models.CharField(max_length=255, blank=True, help_text="PayMongo Public Key")
    paymongo_secret_key = models.CharField(max_length=255, blank=True, help_text="PayMongo Secret Key (encrypted)")
    paymongo_webhook_secret = models.CharField(max_length=255, blank=True, help_text="PayMongo Webhook Secret")

    class Meta:
        verbose_name = "Payment QR Code"
        verbose_name_plural = "Payment QR Codes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {'Active' if self.is_active else 'Inactive'}"

    @classmethod
    def get_active_qr_code(cls):
        """Get the currently active QR code"""
        return cls.objects.filter(is_active=True).first()

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('qr_ph', 'QR PH'),
        ('gcash', 'GCash (Legacy)'),
        ('paymaya', 'PayMaya'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=30, choices=[('registration', 'Registration'), ('other', 'Other')], default='other')
    
    # Renamed from gcash_receipt_image to be more generic
    receipt_image = models.ImageField(upload_to='payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    
    date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    payee_name = models.CharField(max_length=100, blank=True)
    payee_email = models.CharField(max_length=100, blank=True)
    
    # QR PH and PayMongo integration fields
    payment_method = models.CharField(
        max_length=50, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='qr_ph',
        verbose_name="Payment Method"
    )
    qr_ph_reference = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="QR PH Reference Number",
        help_text="Customer's payment reference number"
    )
    paymongo_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="PayMongo Payment Intent ID"
    )
    paymongo_payment_id = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="PayMongo Payment ID"
    )
    paymongo_source_id = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="PayMongo Source ID"
    )
    gateway_response = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Gateway Response Data",
        help_text="Full response from PayMongo API"
    )

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=["user", "status", "date"]),
            models.Index(fields=["payment_type", "status"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - ₱{self.amount} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
