"""
Model to store student data for batch registrations before account creation.
"""
from django.db import models
from accounts.models import BatchRegistration


class BatchStudentData(models.Model):
    """Stores student information for batch registration before user creation"""
    batch_registration = models.ForeignKey(
        BatchRegistration,
        on_delete=models.CASCADE,
        related_name='student_data'
    )
    username = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField()
    address = models.TextField()
    password_hash = models.CharField(max_length=128)
    
    created_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batch_student_data'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['batch_registration', 'email']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
