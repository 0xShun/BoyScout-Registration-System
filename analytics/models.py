from django.db import models
from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from ipware import get_client_ip
import json

class AnalyticsEvent(models.Model):
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('action', 'User Action'),
        ('registration', 'Registration'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    page_url = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f'{self.timestamp} - {self.action} by {self.user}'

    class Meta:
        ordering = ['-timestamp'] 