# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class DonationCampaign(models.Model):
    """
    Model to represent donation campaigns/causes.
    Admins create campaigns that scouts and teachers can donate to.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Campaign Title")
    description = models.TextField(verbose_name="Campaign Description")
    banner_image = models.ImageField(
        upload_to='donation_banners/', 
        null=True, 
        blank=True, 
        verbose_name="Banner Image"
    )
    qr_code_image = models.ImageField(
        upload_to='donation_qr_codes/',
        null=True,
        blank=True,
        verbose_name="QR Code Image",
        help_text="Optional static QR code for display (actual payment uses dynamic QR codes)"
    )
    external_payment_details = models.TextField(
        blank=True,
        verbose_name="External Payment Details",
        help_text="Additional payment information or instructions"
    )
    
    # Goal tracking
    goal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Goal Amount",
        help_text="Target amount to raise. Leave blank for no goal."
    )
    current_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Current Amount Raised",
        help_text="Automatically calculated from verified donations"
    )
    
    # Dates
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Start Date",
        help_text="Campaign start date (optional)"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="End Date",
        help_text="Campaign end date (optional)"
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Campaign Status"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_campaigns',
        verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Goal reached flag
    goal_reached = models.BooleanField(
        default=False,
        verbose_name="Goal Reached",
        help_text="Automatically set when current_amount >= goal_amount"
    )
    goal_reached_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Goal Reached Date"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Donation Campaign"
        verbose_name_plural = "Donation Campaigns"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def progress_percentage(self):
        """Calculate the percentage of goal reached"""
        if not self.goal_amount or self.goal_amount <= 0:
            return 0
        percentage = (self.current_amount / self.goal_amount) * 100
        return min(percentage, 100)  # Cap at 100%

    @property
    def is_active(self):
        """Check if campaign is currently active"""
        if self.status != 'active':
            return False
        
        now = timezone.now().date()
        
        # Check start date
        if self.start_date and now < self.start_date:
            return False
        
        # Check end date
        if self.end_date and now > self.end_date:
            return False
        
        return True

    @property
    def days_remaining(self):
        """Calculate days remaining until end date"""
        if not self.end_date:
            return None
        
        now = timezone.now().date()
        delta = self.end_date - now
        return max(delta.days, 0)

    def update_current_amount(self):
        """Recalculate current_amount from verified donations"""
        from django.db.models import Sum
        total = self.donations.filter(status='verified').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        old_amount = self.current_amount
        self.current_amount = total
        
        # Check if goal was just reached
        if (self.goal_amount and 
            self.current_amount >= self.goal_amount and 
            not self.goal_reached):
            self.goal_reached = True
            self.goal_reached_date = timezone.now()
        
        self.save()
        
        # Return True if goal was just reached
        return (self.goal_reached and 
                old_amount < self.goal_amount and 
                self.current_amount >= self.goal_amount)


class Donation(models.Model):
    """
    Model to track individual donations made to campaigns.
    Uses PayMongo for payment processing with auto-verification.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]
    
    campaign = models.ForeignKey(
        DonationCampaign,
        on_delete=models.CASCADE,
        related_name='donations',
        verbose_name="Campaign"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations',
        verbose_name="Donor"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Donation Amount"
    )
    
    # Payment tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    
    # PayMongo integration fields
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
        default='gcash',
        verbose_name="Payment Method"
    )
    gateway_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Gateway Response Data",
        help_text="Full response from PayMongo API"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verified At"
    )
    
    # Optional message from donor
    message = models.TextField(
        blank=True,
        verbose_name="Donor Message",
        help_text="Optional message from the donor"
    )
    
    # Anonymous donation option
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name="Anonymous Donation",
        help_text="Hide donor name from public donor list"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', 'status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['paymongo_payment_id']),
        ]
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def __str__(self):
        donor_name = "Anonymous" if self.is_anonymous else self.user.get_full_name()
        return f"{donor_name} - {self.campaign.title} - ₱{self.amount}"

    def save(self, *args, **kwargs):
        """Override save to update campaign amount when donation is verified"""
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            old_status = Donation.objects.get(pk=self.pk).status
        
        super().save(*args, **kwargs)
        
        # Update campaign amount if status changed to verified
        if old_status != 'verified' and self.status == 'verified':
            self.verified_at = timezone.now()
            super().save(update_fields=['verified_at'])
            goal_reached = self.campaign.update_current_amount()
            
            # Send goal reached notification if needed
            if goal_reached:
                from .services import send_goal_reached_notification
                send_goal_reached_notification(self.campaign)
