from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Group, Badge, UserBadge, RegistrationPayment

@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'created_at', 'verified_by']
    list_filter = ['status', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'rank', 'registration_status', 'is_active', 'date_joined']
    list_filter = ['rank', 'registration_status', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Scout Information', {
            'fields': ('rank', 'date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies', 'groups_membership')
        }),
        ('Registration Payment', {
            'fields': ('registration_status', 'registration_payment_amount', 'registration_total_paid', 'registration_amount_required', 'registration_receipt', 'registration_verified_by', 'registration_verification_date', 'registration_notes')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Scout Information', {
            'fields': ('rank', 'date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies')
        }),
    )

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name', 'description']

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name', 'description']

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'awarded', 'percent_complete', 'date_awarded']
    list_filter = ['awarded', 'date_awarded', 'badge']
    search_fields = ['user__first_name', 'user__last_name', 'badge__name']
