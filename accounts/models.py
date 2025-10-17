from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from phonenumber_field.modelfields import PhoneNumberField
from decimal import Decimal
import uuid

# Create your models here.

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BatchRegistration(models.Model):
    """Model to track batch registrations (for teachers registering multiple students)"""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Payment Successful'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    registrar = models.ForeignKey('User', on_delete=models.CASCADE, related_name='batch_registrations_created', null=True, blank=True)
    registrar_name = models.CharField(max_length=200, verbose_name="Teacher/Registrar Name")
    registrar_email = models.EmailField(verbose_name="Teacher/Registrar Email")
    registrar_phone = PhoneNumberField(blank=True, region="PH", verbose_name="Teacher/Registrar Phone")
    
    number_of_students = models.PositiveIntegerField(default=1, verbose_name="Number of Students")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Amount")
    amount_per_student = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, verbose_name="Amount per Student")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # PayMongo fields
    paymongo_source_id = models.CharField(max_length=255, blank=True, null=True)
    paymongo_payment_id = models.CharField(max_length=255, blank=True, null=True)
    
    verified_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_batch_registrations')
    verification_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["batch_id"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Batch {self.batch_id} - {self.registrar_name} - {self.number_of_students} students - ₱{self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total amount
        if self.number_of_students and self.amount_per_student:
            self.total_amount = self.number_of_students * self.amount_per_student
        super().save(*args, **kwargs)


class RegistrationPayment(models.Model):
    """Model to track individual registration payments"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='registration_payments')
    batch_registration = models.ForeignKey(BatchRegistration, on_delete=models.CASCADE, related_name='student_payments', null=True, blank=True, verbose_name="Part of Batch Registration")
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

    REGISTRATION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    rank = models.CharField(max_length=30, choices=RANK_CHOICES, default='scout')
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
    is_active = models.BooleanField(default=False)  # Changed to False by default
    groups_membership = models.ManyToManyField(Group, related_name='members', blank=True)
    
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
        return self.rank == 'admin'

    def is_scout(self):
        return self.rank == 'scout'

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
        return self.registration_total_paid >= self.registration_amount_required

    @property
    def is_registration_complete(self):
        """Check if user has completed registration and is active"""
        # Admin users are always active
        if self.rank == 'admin':
            return True
        # User is complete if status is active and account is active
        return self.registration_status == 'active' and self.is_active

    def update_registration_status(self):
        """Update registration status based on payment"""
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        
        # This method is kept for backward compatibility
        # With automatic PayMongo payments, status is managed by webhook
        # Admin users are always active
        if self.rank == 'admin':
            self.registration_status = 'active'
            self.is_active = True
        elif self.registration_total_paid >= self.registration_amount_required:
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
        if not self.username:
            base_username = slugify(self.email.split('@')[0])
            unique_username = base_username
            num = 1
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}{num}"
                num += 1
            self.username = unique_username
        
        # Admin users are automatically active and don't need payment verification
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
        User,
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
