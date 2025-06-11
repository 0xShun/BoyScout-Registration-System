from django.db import models
from accounts.models import User

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payee_name = models.CharField(max_length=255, verbose_name="Payee Name")
    payee_email = models.EmailField(verbose_name="Payee Email Address")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    gcash_receipt_image = models.ImageField(upload_to='gcash_receipts/', blank=True, null=True, verbose_name="GCash Receipt Image")

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"
