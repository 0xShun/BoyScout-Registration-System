from django.db import models
from accounts.models import User

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"
