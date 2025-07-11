from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

# Create your models here.

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    # Override the username field from AbstractUser to make it not unique and nullable
    username = models.CharField(_("username"), max_length=150, unique=True, null=True, blank=True)

    # Set email as unique and the USERNAME_FIELD
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name'] # Fields prompted for when creating a superuser

    RANK_CHOICES = (
        ('admin', 'Administrator'),
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
    groups_membership = models.ManyToManyField(Group, related_name='members', blank=True)

    def is_admin(self):
        return self.rank == 'admin'

    def is_scout(self):
        return self.rank == 'scout'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def join_date(self):
        return self.date_joined

    def save(self, *args, **kwargs):
        if not self.username:
            base_username = slugify(self.email.split('@')[0])
            unique_username = base_username
            num = 1
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}{num}"
                num += 1
            self.username = unique_username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rank_display()})"

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = [
            ("can_manage_scouts", "Can manage scouts"),
            ("can_manage_troop_leaders", "Can manage troop leaders"),
            ("can_manage_committee", "Can manage committee members"),
            ("can_manage_parents", "Can manage parents/guardians"),
        ]

class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='user_badges')
    date_awarded = models.DateField(null=True, blank=True)
    percent_complete = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    awarded = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.badge.name}"
