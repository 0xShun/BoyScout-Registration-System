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
    # New fields for payment flow
    qr_code = models.ImageField(upload_to='event_qr_codes/', null=True, blank=True, verbose_name="Payment QR Code")
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

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["registration", "status", "created_at"]),
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
            # Not paid yet - no partial payments allowed
            self.payment_status = 'not_required'
        self.save()

    def save(self, *args, **kwargs):
        # Auto-set payment status based on event requirements
        if not self.pk:  # Only on creation
            if self.event.has_payment_required:
                self.payment_status = 'not_required'  # Until full payment confirmed
                self.amount_required = self.event.payment_amount
            else:
                self.payment_status = 'not_required'
                self.amount_required = Decimal('0.00')
        super().save(*args, **kwargs)
