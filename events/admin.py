from django.contrib import admin
from .models import Event, EventRegistration, EventPayment, Attendance, EventPhoto, AttendanceSession, CertificateTemplate, EventCertificate

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


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['event', 'is_active', 'started_at', 'started_by', 'stopped_at', 'auto_stop_minutes']
    list_filter = ['is_active', 'started_at', 'event']
    search_fields = ['event__title', 'started_by__first_name', 'started_by__last_name']
    readonly_fields = ['started_at', 'stopped_at']


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['event', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['event__title']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'template_image')
        }),
        ('Name Positioning', {
            'fields': ('name_x', 'name_y', 'name_font_size', 'name_color')
        }),
        ('Event Name Positioning', {
            'fields': ('event_name_x', 'event_name_y', 'event_font_size', 'event_color')
        }),
        ('Date Positioning', {
            'fields': ('date_x', 'date_y', 'date_font_size', 'date_color')
        }),
        ('Certificate Number Positioning', {
            'fields': ('cert_number_x', 'cert_number_y', 'cert_number_font_size', 'cert_number_color')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(EventCertificate)
class EventCertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'user', 'event', 'generated_at']
    list_filter = ['generated_at', 'event']
    search_fields = ['certificate_number', 'user__first_name', 'user__last_name', 'event__title']
    readonly_fields = ['certificate_number', 'generated_at']

