from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = (
        ('scout', 'Scout'),
        ('admin', 'Administrator'),
        ('troop_leader', 'Troop Leader'),
        ('assistant_leader', 'Assistant Leader'),
        ('committee_member', 'Committee Member'),
        ('parent', 'Parent/Guardian'),
    )

    RANK_CHOICES = (
        ('none', 'No Rank'),
        ('scout', 'Scout'),
        ('senior_scout', 'Senior Scout'),
        ('patrol_leader', 'Patrol Leader'),
        ('assistant_patrol_leader', 'Assistant Patrol Leader'),
        ('second_class', 'Second Class'),
        ('first_class', 'First Class'),
        ('star', 'Star'),
        ('life', 'Life'),
        ('eagle', 'Eagle'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='scout')
    rank = models.CharField(max_length=30, choices=RANK_CHOICES, default='scout')
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def is_admin(self):
        return self.role == 'admin'

    def is_scout(self):
        return self.role == 'scout'

    def is_troop_leader(self):
        return self.role == 'troop_leader'

    def is_assistant_leader(self):
        return self.role == 'assistant_leader'

    def is_committee_member(self):
        return self.role == 'committee_member'

    def is_parent(self):
        return self.role == 'parent'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def join_date(self):
        return self.date_joined

    def has_role(self, *roles):
        return self.role in roles

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != 'admin':
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = [
            ("can_manage_scouts", "Can manage scouts"),
            ("can_manage_troop_leaders", "Can manage troop leaders"),
            ("can_manage_committee", "Can manage committee members"),
            ("can_manage_parents", "Can manage parents/guardians"),
        ]
