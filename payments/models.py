from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class PaymentQRCode(models.Model):
    """Model to store the general payment QR code for all scouts"""
    qr_code = models.ImageField(upload_to='payment_qr_codes/', verbose_name="Payment QR Code")
    title = models.CharField(max_length=100, default="General Payment QR Code", verbose_name="QR Code Title")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_qr_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

class SystemConfiguration(models.Model):
    """Model to store system-wide configuration including registration fee"""
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('paymaya', 'PayMaya'),
        ('grab_pay', 'GrabPay'),
    ]
    
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, verbose_name="Registration Fee")
    default_payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='paymaya',  # Changed from gcash to paymaya as fallback
        verbose_name="Default Payment Method",
        help_text="Payment method to use for PayMongo (ensure this is enabled in your PayMongo dashboard)"
    )
    # Legacy field - will be removed after PayMongo migration
    registration_qr_code = models.ImageField(upload_to='system_qr_codes/', null=True, blank=True, verbose_name="Registration QR Code (Legacy)")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='system_config_updates')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"
    
    def __str__(self):
        return "System Configuration"
    
    @classmethod
    def get_config(cls):
        """Get or create the system configuration singleton"""
        config, created = cls.objects.get_or_create(pk=1)
        return config

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    receipt_image = models.ImageField(upload_to='payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    reference_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Reference Number")
    payment_method = models.CharField(max_length=20, default='QR-PH', verbose_name="Payment Method")
    qr_ph_reference = models.CharField(max_length=100, blank=True, verbose_name="QR PH Reference")
    date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, verbose_name="Rejection Reason")
    notes = models.TextField(blank=True)
    payee_name = models.CharField(max_length=100, blank=True)
    payee_email = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=["user", "status", "date"]),
            models.Index(fields=["reference_number"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - ₱{self.amount} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
