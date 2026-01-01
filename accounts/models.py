from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from phonenumber_field.modelfields import PhoneNumberField
from decimal import Decimal

# Create your models here.

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
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('paymongo_gcash', 'GCash via PayMongo'),
        ('paymongo_maya', 'Maya via PayMongo'),
        ('manual', 'Manual Upload'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='registration_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Payment Amount")
    
    # Legacy fields (for backward compatibility with manual uploads)
    receipt_image = models.ImageField(upload_to='registration_payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    reference_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Reference Number")
    
    # PayMongo fields
    paymongo_source_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="PayMongo Source ID")
    paymongo_payment_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="PayMongo Payment ID")
    paymongo_checkout_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="PayMongo Checkout URL")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paymongo_gcash', verbose_name="Payment Method")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, verbose_name="Rejection Reason")
    notes = models.TextField(blank=True, verbose_name="Payment Notes")
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

    RANK_CHOICES = (
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('scout', 'Scout'),
    )

    REGISTRATION_STATUS_CHOICES = [
        ('pending_payment', 'Pending Registration Payment'),
        ('payment_submitted', 'Registration Payment Submitted'),
        ('partial_payment', 'Partial Registration Payment'),
        ('payment_verified', 'Registration Payment Verified'),
        ('active', 'Active Member'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
        ('suspended', 'Suspended'),
    ]

    rank = models.CharField(max_length=30, choices=RANK_CHOICES, default='scout')
    # Legacy field for backward compatibility with old database schema
    role = models.CharField(max_length=30, choices=RANK_CHOICES, default='scout', null=True, blank=True)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    
    # Teacher-Student Relationship
    managed_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='managed_students',
        limit_choices_to={'rank': 'teacher'},
        verbose_name="Managed by Teacher",
        help_text="The teacher who manages this student account (if applicable)"
    )
    
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
    is_active = models.BooleanField(default=False)  # Changed to False by default
    groups_membership = models.ManyToManyField(Group, related_name='members', blank=True)
    
    # Registration payment fields
    registration_status = models.CharField(max_length=30, choices=REGISTRATION_STATUS_CHOICES, default='pending_payment')
    registration_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, verbose_name="Registration Fee")
    registration_receipt = models.ImageField(upload_to='registration_receipts/', null=True, blank=True, verbose_name="Registration Payment Receipt")
    registration_verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_registrations')
    registration_verification_date = models.DateTimeField(null=True, blank=True)
    registration_notes = models.TextField(blank=True, verbose_name="Registration Notes")
    # New fields for partial registration payments
    registration_total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Total Registration Paid")
    registration_amount_required = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'), verbose_name="Registration Amount Required")

    def is_admin(self):
        return self.rank == 'admin'

    def is_teacher(self):
        return self.rank == 'teacher'

    def is_scout(self):
        return self.rank == 'scout'
    
    def is_managed_student(self):
        """Check if this user is a student managed by a teacher"""
        return self.managed_by is not None

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
        # Admin users don't need payment verification
        if self.rank == 'admin':
            return True
        # Teachers and scouts need to complete payment
        return self.registration_total_paid >= self.registration_amount_required

    @property
    def is_registration_complete(self):
        """Check if user has completed registration payment"""
        # Admin users don't need payment verification
        if self.rank == 'admin':
            return True
        # Consider both legacy 'active' and current 'payment_verified' as complete
        return self.registration_status in ('active', 'payment_verified')

    def update_registration_status(self):
        """Update registration status and set registration_date/expiry when fully paid"""
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        if self.registration_amount_required == 0:
            self.registration_status = 'active'
            self.is_active = True
        elif self.registration_total_paid >= self.registration_amount_required:
            self.registration_status = 'payment_verified'
            self.is_active = True
            if not self.registration_date:
                self.registration_date = timezone.now()
            years = min(int(self.registration_total_paid // self.registration_amount_required), 2)
            self.membership_expiry = timezone.now() + relativedelta(years=years)
        elif self.registration_total_paid > 0:
            self.registration_status = 'partial_payment'
            self.is_active = False
        else:
            self.registration_status = 'pending_payment'
            self.is_active = False
        self.save()

    def save(self, *args, **kwargs):
        if not self.username:
            base_username = slugify(self.email.split('@')[0])
            unique_username = base_username
            num = 1
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}{num}"
                num += 1
            self.username = unique_username
        
        # Sync role with rank for backward compatibility
        self.role = self.rank
        
        # Admin users are automatically active and don't need payment verification
        # Teachers follow the same registration flow as scouts (pay fee, admin verifies)
        if self.rank == 'admin':
            self.is_active = True
            self.registration_status = 'active'
        
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
