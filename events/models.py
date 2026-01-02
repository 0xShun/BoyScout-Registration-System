from django.db import models
from django.utils import timezone
from accounts.models import User
from decimal import Decimal

def get_current_time():
    return timezone.now().time()

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField(default=get_current_time)
    location = models.CharField(max_length=200)
    banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    # Payment amount - used by PayMongo to generate unique QR codes per registration
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Event Fee")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def has_payment_required(self):
        """Check if this event requires payment"""
        return self.payment_amount and self.payment_amount > 0

class EventPhoto(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='event_photos/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo for {self.event.title} - {self.caption}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_marked')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['event', 'user']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title} ({self.status})"

class EventPayment(models.Model):
    """Model to track individual payments for event registrations"""
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
    
    registration = models.ForeignKey('EventRegistration', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Payment Amount")
    
    # Legacy fields (for backward compatibility with manual uploads)
    receipt_image = models.ImageField(upload_to='event_payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    reference_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Reference Number")
    
    # PayMongo fields
    paymongo_source_id = models.CharField(max_length=100, null=True, blank=True, unique=True, verbose_name="PayMongo Source ID")
    paymongo_payment_id = models.CharField(max_length=100, null=True, blank=True, unique=True, verbose_name="PayMongo Payment ID")
    paymongo_checkout_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="PayMongo Checkout URL")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paymongo_gcash')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Payment Expiration")
    is_expired = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, verbose_name="Rejection Reason")
    notes = models.TextField(blank=True, verbose_name="Payment Notes")
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_event_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["registration", "status", "created_at"]),
            models.Index(fields=["paymongo_source_id"]),
            models.Index(fields=["paymongo_payment_id"]),
        ]

    def __str__(self):
        return f"{self.registration.user.get_full_name()} - {self.registration.event.title} - ₱{self.amount} ({self.get_status_display()})"
    
    def mark_as_expired(self):
        """Mark payment as expired"""
        self.is_expired = True
        self.status = 'expired'
        self.save()

class EventRegistration(models.Model):
    RSVP_CHOICES = [
        ('yes', 'Attending'),
        ('no', 'Not Attending'),
        ('maybe', 'Maybe'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Payment Not Required'),
        ('pending', 'Payment Pending'),
        ('partial', 'Partial Payment'),
        ('paid', 'Payment Complete'),
        ('rejected', 'Payment Rejected'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    rsvp = models.CharField(max_length=10, choices=RSVP_CHOICES, default='yes')
    receipt_image = models.ImageField(upload_to='event_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    registered_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_event_registrations')
    verification_date = models.DateTimeField(null=True, blank=True)
    # Updated fields for payment flow
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='not_required')
    payment_notes = models.TextField(blank=True, verbose_name="Payment Notes")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Total Amount Paid")
    amount_required = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Amount Required")

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title} ({self.rsvp})"

    @property
    def amount_remaining(self):
        """Calculate remaining amount to be paid"""
        return max(Decimal('0.00'), self.amount_required - self.total_paid)

    @property
    def is_fully_paid(self):
        """Check if registration is fully paid"""
        return self.total_paid >= self.amount_required

    def update_payment_status(self):
        """Update payment status based on total paid vs required"""
        if self.amount_required == 0:
            self.payment_status = 'not_required'
        elif self.total_paid >= self.amount_required:
            self.payment_status = 'paid'
        elif self.total_paid > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'pending'
        self.save()

    def save(self, *args, **kwargs):
        # Auto-set payment status based on event requirements
        if not self.pk:  # Only on creation
            if self.event.has_payment_required:
                self.payment_status = 'pending'
                self.amount_required = self.event.payment_amount
            else:
                self.payment_status = 'not_required'
                self.amount_required = Decimal('0.00')
        super().save(*args, **kwargs)


class AttendanceSession(models.Model):
    """Controls when students can mark their attendance for an event"""
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='attendance_session')
    is_active = models.BooleanField(default=False, verbose_name="Session Active")
    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='started_attendance_sessions')
    stopped_at = models.DateTimeField(null=True, blank=True)
    auto_stop_minutes = models.IntegerField(default=0, help_text="Auto-stop after X minutes (0 = manual only)")
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.event.title} - Attendance Session ({status})"
    
    def start(self, admin_user):
        """Start the attendance session"""
        self.is_active = True
        self.started_at = timezone.now()
        self.started_by = admin_user
        self.stopped_at = None
        self.save()
    
    def stop(self):
        """Stop the attendance session"""
        self.is_active = False
        self.stopped_at = timezone.now()
        self.save()


class CertificateTemplate(models.Model):
    """Stores certificate template image and text positioning for an event"""
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='certificate_template')
    template_image = models.ImageField(upload_to='certificate_templates/', help_text="Upload certificate template image")
    
    # Name positioning
    name_x = models.IntegerField(default=500, help_text="X coordinate for participant name")
    name_y = models.IntegerField(default=400, help_text="Y coordinate for participant name")
    name_font_size = models.IntegerField(default=60, help_text="Font size for participant name")
    name_color = models.CharField(max_length=7, default="#000000", help_text="Hex color for name (e.g., #000000)")
    
    # Event name positioning
    event_name_x = models.IntegerField(default=500, help_text="X coordinate for event name")
    event_name_y = models.IntegerField(default=550, help_text="Y coordinate for event name")
    event_font_size = models.IntegerField(default=40, help_text="Font size for event name")
    event_color = models.CharField(max_length=7, default="#000000", help_text="Hex color for event name")
    
    # Date positioning
    date_x = models.IntegerField(default=500, help_text="X coordinate for date")
    date_y = models.IntegerField(default=650, help_text="Y coordinate for date")
    date_font_size = models.IntegerField(default=30, help_text="Font size for date")
    date_color = models.CharField(max_length=7, default="#000000", help_text="Hex color for date")
    
    # Certificate number positioning
    cert_number_x = models.IntegerField(default=100, help_text="X coordinate for certificate number")
    cert_number_y = models.IntegerField(default=100, help_text="Y coordinate for certificate number")
    cert_number_font_size = models.IntegerField(default=20, help_text="Font size for certificate number")
    cert_number_color = models.CharField(max_length=7, default="#666666", help_text="Hex color for cert number")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Certificate Template - {self.event.title}"


class EventCertificate(models.Model):
    """Generated certificates for event participants"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_certificates')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='certificates')
    attendance = models.OneToOneField(Attendance, on_delete=models.CASCADE, related_name='certificate', null=True, blank=True)
    certificate_number = models.CharField(max_length=50, unique=True, help_text="Unique certificate identifier")
    certificate_file = models.ImageField(upload_to='event_certificates/', help_text="Generated certificate PNG")
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
        unique_together = ('user', 'event')
    
    def __str__(self):
        return f"Certificate #{self.certificate_number} - {self.user.get_full_name()} - {self.event.title}"
    
    @staticmethod
    def generate_certificate_number(event_id, user_id):
        """Generate unique certificate number"""
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"CERT-{event_id}-{user_id}-{timestamp}"
