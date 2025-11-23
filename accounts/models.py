from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from phonenumber_field.modelfields import PhoneNumberField
from decimal import Decimal
import uuid

# Create your models here.

class SystemSettings(models.Model):
    """
    System-wide settings that admins can change from the admin panel.
    Only one instance should exist (singleton pattern).
    """
    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        verbose_name="Platform Registration Fee",
        help_text="Default fee for new user registrations. All users pay this amount to register."
    )
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return f"System Settings (Registration Fee: ₱{self.registration_fee})"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton)
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the system settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    @classmethod
    def get_registration_fee(cls):
        """Quick method to get the current registration fee"""
        return cls.get_settings().registration_fee


class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RegistrationPayment(models.Model):
    """Model to track individual registration payments"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='registration_payments')
    paid_by_teacher = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_paid_registrations',
        limit_choices_to={'role': 'teacher'},
        verbose_name="Paid by Teacher",
        help_text="If this registration was paid by a teacher during bulk registration"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Payment Amount")
    receipt_image = models.ImageField(upload_to='registration_payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, verbose_name="Payment Notes")
    
    # PayMongo fields
    paymongo_source_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="PayMongo Source ID")
    paymongo_payment_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="PayMongo Payment ID")
    
    verified_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_registration_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - Registration Payment - ₱{self.amount} ({self.get_status_display()})"

class User(AbstractUser):
    # Override the username field from AbstractUser to make it not unique and nullable
    username = models.CharField(_("username"), max_length=150, unique=True, null=True, blank=True)

    # Set email as unique and the USERNAME_FIELD
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name'] # Fields prompted for when creating a superuser

    # User role (system access level)
    ROLE_CHOICES = (
        ('scout', 'Scout'),                # Regular member
        ('teacher', 'Teacher'),            # Teacher who can register and manage students
        ('admin', 'Administrator'),        # Full system admin
    )
    
    # Backward compatibility: RANK_CHOICES maps to ROLE_CHOICES
    RANK_CHOICES = ROLE_CHOICES

    REGISTRATION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    # System role (determines permissions)
    role = models.CharField(
        max_length=30, 
        choices=ROLE_CHOICES, 
        default='scout',
        verbose_name="User Role",
        help_text="Scout (member), Teacher, or Administrator"
    )
    
    # Keep old 'rank' field temporarily for migration compatibility
    rank = models.CharField(
        max_length=30, 
        choices=ROLE_CHOICES,  # Now only role choices
        default='scout',
        help_text="DEPRECATED: Use 'role' field instead"
    )
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    phone_number = PhoneNumberField(blank=True, region="PH")
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = PhoneNumberField(blank=True, region="PH")
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    registration_date = models.DateTimeField(null=True, blank=True)
    membership_expiry = models.DateTimeField(null=True, blank=True)
    # Make newly created users active by default to match test expectations
    # (this can be revisited if a different registration flow is desired)
    is_active = models.BooleanField(default=True)
    groups_membership = models.ManyToManyField(Group, related_name='members', blank=True)
    
    # Teacher-Student relationship
    registered_by_teacher = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_students',
        limit_choices_to={'role': 'teacher'},
        verbose_name="Registered by Teacher",
        help_text="The teacher who registered this student (if applicable)"
    )
    
    # Registration payment fields
    registration_status = models.CharField(max_length=30, choices=REGISTRATION_STATUS_CHOICES, default='inactive')
    registration_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, verbose_name="Registration Fee")
    registration_receipt = models.ImageField(upload_to='registration_receipts/', null=True, blank=True, verbose_name="Registration Payment Receipt")
    registration_verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_registrations')
    registration_verification_date = models.DateTimeField(null=True, blank=True)
    registration_notes = models.TextField(blank=True, verbose_name="Registration Notes")
    # New fields for partial registration payments
    registration_total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Total Registration Paid")
    registration_amount_required = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'), verbose_name="Registration Amount Required")

    def is_admin(self):
        """Check if user is a system administrator (callable from Python code)"""
        return self.role == 'admin'

    def is_teacher(self):
        """Check if user is a teacher (callable from Python code)"""
        return self.role == 'teacher'

    def is_leader(self):
        """Check if user is a scout leader (callable from Python code)"""
        return self.role == 'leader'

    def is_scout(self):
        """Check if user is a regular scout member (callable from Python code)"""
        return self.role == 'scout'
    
    def has_leader_permissions(self):
        """Check if user has at least leader-level permissions (callable from Python code)"""
        return self.role in ('leader', 'admin')
    
    def can_manage_events(self):
        """Check if user can create/manage events (callable from Python code)"""
        return self.has_leader_permissions()
    
    def can_verify_payments(self):
        """Check if user can verify payments (callable from Python code)"""
        return self.is_admin()
    
    def can_change_settings(self):
        """Check if user can change system settings (callable from Python code)"""
        return self.is_admin()
    
    # Template-accessible properties (no parentheses needed in templates)
    @property
    def is_admin_user(self):
        """Template-friendly property to check if user is admin"""
        return self.role == 'admin'
    
    @property
    def is_leader_user(self):
        """Template-friendly property to check if user is leader"""
        return self.role == 'leader'
    
    @property
    def is_scout_user(self):
        """Template-friendly property to check if user is scout"""
        return self.role == 'scout'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def join_date(self):
        # Only set join_date if registration payment is complete
        if self.is_registration_fully_paid:
            return self.date_joined
        return None

    @property
    def registration_amount_remaining(self):
        """Calculate remaining registration amount to be paid"""
        return max(Decimal('0.00'), self.registration_amount_required - self.registration_total_paid)

    @property
    def is_registration_fully_paid(self):
        """Check if user has completed registration payment"""
        # Admins and leaders don't need payment verification
        if self.role in ('admin', 'leader'):
            return True
        return self.registration_total_paid >= self.registration_amount_required

    @property
    def is_registration_complete(self):
        """Check if user has completed registration and is active"""
        # Admins and leaders are always active
        if self.role in ('admin', 'leader'):
            return True
        # Accept both legacy 'Active Member' and newer lowercase 'active'
        return (self.registration_status in ('Active Member', 'active')) and self.is_active

    def update_registration_status(self):
        """Update registration status based on payment"""
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        
        # This method is kept for backward compatibility
        # With automatic PayMongo payments, status is managed by webhook
        # Admins and leaders are always active (no payment required)
        if self.role in ('admin', 'leader'):
            self.registration_status = 'active'
            self.is_active = True
        elif self.registration_total_paid >= self.registration_amount_required:
            # Normalize to canonical value 'active'
            self.registration_status = 'active'
            self.is_active = True
            if not self.registration_date:
                self.registration_date = timezone.now()
            years = min(int(self.registration_total_paid // self.registration_amount_required), 2)
            self.membership_expiry = timezone.now() + relativedelta(years=years)
        else:
            # Payment not complete - keep inactive
            self.registration_status = 'inactive'
            self.is_active = False
        self.save()

    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username:
            base_username = slugify(self.email.split('@')[0])
            unique_username = base_username
            num = 1
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}{num}"
                num += 1
            self.username = unique_username
        
        # Sync 'rank' with 'role' for backward compatibility during migration
        if not self.rank or self.rank in dict(self.ROLE_CHOICES).keys():
            self.rank = self.role
        
        # Admins and leaders are automatically active (no payment required)
        if self.role in ('admin', 'leader'):
            self.is_active = True
            self.registration_status = 'active'
            self.registration_total_paid = self.registration_amount_required
        
        super().save(*args, **kwargs)

    def __str__(self):
        role_display = self.get_role_display()
        return f"{self.get_full_name()} ({role_display})"

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = [
            ("can_manage_scouts", "Can manage scouts"),
            ("can_manage_troop_leaders", "Can manage troop leaders"),
            ("can_manage_committee", "Can manage committee members"),
            ("can_manage_parents", "Can manage parents/guardians"),
        ]
