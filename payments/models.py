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

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gcash_receipt_image = models.ImageField(upload_to='payment_receipts/', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    payee_name = models.CharField(max_length=100, blank=True)
    payee_email = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.get_full_name()} - ₱{self.amount} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
