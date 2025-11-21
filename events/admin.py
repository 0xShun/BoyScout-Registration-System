from django.contrib import admin
from .models import Event, EventRegistration, EventPayment, Attendance, EventPhoto, CertificateTemplate, EventCertificate

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'time', 'location', 'payment_amount', 'created_by', 'created_at']
    list_filter = ['date', 'created_at', 'payment_amount']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'date'

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'rsvp', 'payment_status', 'total_paid', 'amount_required', 'amount_remaining', 'registered_at']
    list_filter = ['rsvp', 'payment_status', 'registered_at', 'event']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'event__title']
    readonly_fields = ['registered_at', 'total_paid', 'amount_required', 'amount_remaining']
    
    def amount_remaining(self, obj):
        return f"₱{obj.amount_remaining}"
    amount_remaining.short_description = 'Remaining'

@admin.register(EventPayment)
class EventPaymentAdmin(admin.ModelAdmin):
    list_display = ['registration', 'amount', 'status', 'created_at', 'verified_by']
    list_filter = ['status', 'created_at', 'registration__event']
    search_fields = ['registration__user__first_name', 'registration__user__last_name', 'registration__event__title']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'status', 'marked_by', 'timestamp']
    list_filter = ['status', 'timestamp', 'event']
    search_fields = ['user__first_name', 'user__last_name', 'event__title']

@admin.register(EventPhoto)
class EventPhotoAdmin(admin.ModelAdmin):
    list_display = ['event', 'caption', 'uploaded_by', 'uploaded_at', 'is_featured']
    list_filter = ['is_featured', 'uploaded_at', 'event']
    search_fields = ['caption', 'event__title']


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    """Admin interface for managing certificate templates."""
    list_display = ['certificate_name', 'event', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at', 'event']
    search_fields = ['certificate_name', 'event__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'certificate_name', 'template_image', 'is_active')
        }),
        ('Scout Name Text Configuration', {
            'fields': ('name_x', 'name_y', 'name_font_size', 'name_color'),
            'description': 'Configure where and how the scout\'s name appears on the certificate.'
        }),
        ('Event Name Text Configuration', {
            'fields': ('event_x', 'event_y', 'event_font_size', 'event_color'),
            'description': 'Configure where and how the event name appears on the certificate.'
        }),
        ('Date Text Configuration', {
            'fields': ('date_x', 'date_y', 'date_font_size', 'date_color'),
            'description': 'Configure where and how the date appears on the certificate.'
        }),
        ('Certificate Number Text Configuration', {
            'fields': ('certificate_number_x', 'certificate_number_y', 'certificate_number_font_size', 'certificate_number_color'),
            'description': 'Optional: Configure where and how the certificate number appears on the certificate.',
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EventCertificate)
class EventCertificateAdmin(admin.ModelAdmin):
    """Admin interface for viewing generated certificates."""
    list_display = ['certificate_number', 'user_full_name', 'event', 'issued_date', 'download_count']
    list_filter = ['issued_date', 'event', 'event__date']
    search_fields = ['certificate_number', 'user__first_name', 'user__last_name', 'event__title']
    readonly_fields = ['certificate_number', 'issued_date', 'created_at', 'updated_at', 'certificate_image_preview']
    
    fieldsets = (
        ('Certificate Information', {
            'fields': ('certificate_number', 'event', 'user', 'issued_date')
        }),
        ('Certificate Content', {
            'fields': ('certificate_image_preview', 'certificate_image', 'certificate_template')
        }),
        ('Usage Statistics', {
            'fields': ('download_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Scout'
    
    def certificate_image_preview(self, obj):
        if obj.certificate_image:
            return f'<img src="{obj.certificate_image.url}" width="400" />'
        return 'No image'
    certificate_image_preview.allow_tags = True
    certificate_image_preview.short_description = 'Preview'
