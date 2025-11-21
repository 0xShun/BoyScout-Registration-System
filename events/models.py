from django.db import models
from django.utils import timezone
import uuid
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
    # Payment field - QR PH integration generates dynamic QR codes
    payment_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Event Fee",
        help_text="Set event fee amount. Leave blank for free events."
    )
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


class AttendanceQRCode(models.Model):
    """One QR token per event (active for a configured period). Teachers/admins generate this and
    students scan the teacher's QR to mark attendance. Multiple students can scan the same token
    while it's active (expires_at) but the token can be invalidated by regenerating.
    """
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_qrcodes')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_attendance_qrcodes')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"QR {self.token} for {self.event.title} (active={self.active})"

    @property
    def is_valid(self):
        if not self.active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

class EventPayment(models.Model):
    """Model to track individual payments for event registrations with QR PH integration"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    registration = models.ForeignKey('EventRegistration', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Payment Amount")
    receipt_image = models.ImageField(upload_to='event_payment_receipts/', null=True, blank=True, verbose_name="Payment Receipt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, verbose_name="Payment Notes")
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_event_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # PayMongo QR PH integration fields
    paymongo_source_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="PayMongo Source ID",
        help_text="PayMongo source ID for QR PH payment"
    )
    paymongo_payment_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="PayMongo Payment ID",
        help_text="PayMongo payment ID after successful payment"
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        default='qr_ph',
        verbose_name="Payment Method",
        help_text="Method used for payment (qr_ph, manual, etc.)"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["registration", "status", "created_at"]),
            models.Index(fields=["paymongo_payment_id"]),
        ]

    def __str__(self):
        return f"{self.registration.user.get_full_name()} - {self.registration.event.title} - ₱{self.amount} ({self.get_status_display()})"

class EventRegistration(models.Model):
    RSVP_CHOICES = [
        ('yes', 'Attending'),
        ('no', 'Not Attending'),
        ('maybe', 'Maybe'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Payment Not Required'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
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
    # Payment fields - full payment required, no partial payments
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
        """Update payment status based on total paid vs required - full payment only"""
        if self.amount_required == 0:
            self.payment_status = 'not_required'
        elif self.total_paid >= self.amount_required:
            self.payment_status = 'paid'
        else:
            # Not fully paid yet — show explicit pending state so UI reflects
            # that payment is required and outstanding.
            self.payment_status = 'pending'
        self.save()

    def save(self, *args, **kwargs):
        # Auto-set payment status based on event requirements
        if not self.pk:  # Only on creation
            if self.event.has_payment_required:
                # For events that require payment, registrations start in
                # 'pending' until payment is fully confirmed.
                self.payment_status = 'pending'
                self.amount_required = self.event.payment_amount
            else:
                self.payment_status = 'not_required'
                self.amount_required = Decimal('0.00')
        super().save(*args, **kwargs)


class CertificateTemplate(models.Model):
    """
    Stores certificate template configuration for an event.
    Admin uploads a certificate design image and configures where text (name, date, etc.)
    should appear on the certificate.
    """
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name='certificate_template',
        help_text="Event this certificate template is for"
    )
    template_image = models.ImageField(
        upload_to='certificate_templates/',
        help_text="Background certificate design image (PNG or JPG recommended)"
    )
    certificate_name = models.CharField(
        max_length=200,
        default='Certificate of Participation',
        help_text="Title/name of the certificate"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_certificate_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Scout Name Text Configuration
    name_x = models.IntegerField(default=600, help_text="X pixel position for scout name")
    name_y = models.IntegerField(default=450, help_text="Y pixel position for scout name")
    name_font_size = models.IntegerField(default=48, help_text="Font size for scout name")
    name_color = models.CharField(
        max_length=7,
        default='#000000',
        help_text="Font color for name (hex format, e.g., #000000)"
    )

    # Event Name Text Configuration
    event_x = models.IntegerField(default=600, help_text="X pixel position for event name")
    event_y = models.IntegerField(default=520, help_text="Y pixel position for event name")
    event_font_size = models.IntegerField(default=32, help_text="Font size for event name")
    event_color = models.CharField(
        max_length=7,
        default='#333333',
        help_text="Font color for event name"
    )

    # Date Text Configuration
    date_x = models.IntegerField(default=600, help_text="X pixel position for date")
    date_y = models.IntegerField(default=590, help_text="Y pixel position for date")
    date_font_size = models.IntegerField(default=28, help_text="Font size for date")
    date_color = models.CharField(
        max_length=7,
        default='#666666',
        help_text="Font color for date"
    )

    # Certificate Number Text Configuration (Optional)
    certificate_number_x = models.IntegerField(
        null=True,
        blank=True,
        help_text="X pixel position for certificate number"
    )
    certificate_number_y = models.IntegerField(
        null=True,
        blank=True,
        help_text="Y pixel position for certificate number"
    )
    certificate_number_font_size = models.IntegerField(
        default=16,
        help_text="Font size for certificate number"
    )
    certificate_number_color = models.CharField(
        max_length=7,
        default='#999999',
        help_text="Font color for certificate number"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active for use"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Certificate Template for {self.event.title}"


class EventCertificate(models.Model):
    """
    Stores generated certificates for scouts who attended an event.
    Created automatically when a scout marks attendance via QR code scan.
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='certificates',
        help_text="Event this certificate is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_certificates',
        help_text="Scout receiving this certificate"
    )
    certificate_template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_certificates',
        help_text="Template used to generate this certificate"
    )
    certificate_image = models.ImageField(
        upload_to='certificates/%Y/%m/%d/',
        help_text="Generated certificate PNG image"
    )
    certificate_number = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique certificate number for tracking"
    )
    issued_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the certificate was generated"
    )
    download_count = models.IntegerField(
        default=0,
        help_text="Number of times certificate has been downloaded"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_date']
        unique_together = ('event', 'user')
        indexes = [
            models.Index(fields=['event', 'user']),
            models.Index(fields=['certificate_number']),
        ]

    def __str__(self):
        return f"Certificate for {self.user.get_full_name()} - {self.event.title}"
