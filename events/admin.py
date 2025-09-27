from django.contrib import admin
from .models import Event, EventRegistration, EventPayment, Attendance, EventPhoto

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
