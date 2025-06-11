from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = (
        ('scout', 'Scout'),
        ('admin', 'Administrator'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='scout')

    def is_admin(self):
        return self.role == 'admin'

    def is_scout(self):
        return self.role == 'scout'
