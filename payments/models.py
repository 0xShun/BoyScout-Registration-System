from django.db import models
from accounts.models import User
from django.utils import timezone

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payee_name = models.CharField(max_length=255, verbose_name="Payee Name")
    payee_email = models.EmailField(max_length=254, verbose_name="Payee Email Address")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gcash_receipt_image = models.ImageField(
        upload_to='gcash_receipts/',
        verbose_name="GCash Receipt Image",
        null=True,
        blank=True
    )
    expiry_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_payments'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} ({self.status})"

    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now()
