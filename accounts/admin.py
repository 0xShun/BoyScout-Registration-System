from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Group, RegistrationPayment, SystemSettings
from django.utils.html import format_html


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for system-wide settings.
    Admins can change the platform registration fee here.
    """
    list_display = ['registration_fee_display']
    
    fieldsets = (
        ('Platform Registration Fee', {
            'fields': ('registration_fee',),
            'description': (
                '<p style="color: #666; font-size: 14px;">'
                '<strong>This is the default registration fee for ALL new users.</strong><br>'
                'All users will pay this amount when registering on the platform.<br><br>'
                '<strong>Note:</strong> This is different from event fees, which can be set per event.<br>'
                'Changes to this fee will apply to all NEW registrations immediately.<br>'
                'Existing pending payments will keep their original amount.'
                '</p>'
            )
        }),
    )
    
    def registration_fee_display(self, obj):
        return format_html('<strong style="font-size: 16px; color: #28a745;">₱{:.2f}</strong>', obj.registration_fee)
    registration_fee_display.short_description = 'Current Registration Fee'
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False



@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'paid_by_teacher_display', 'amount', 'status', 'created_at', 'verified_by']
    list_filter = ['status', 'created_at', 'paid_by_teacher']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def paid_by_teacher_display(self, obj):
        if obj.paid_by_teacher:
            return format_html(
                '<span class="badge bg-info">Teacher: {}</span>',
                obj.paid_by_teacher.get_full_name()
            )
        return '-'
    paid_by_teacher_display.short_description = 'Paid By'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'registered_by_teacher_display', 'registration_status', 'is_active', 'date_joined']
    list_filter = ['role', 'registration_status', 'is_active', 'registered_by_teacher', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'registered_by_teacher__email']
    ordering = ['-date_joined']
    
    actions = ['activate_users', 'deactivate_users']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role',),
            'description': 'Role determines system access level (Scout, Teacher, or Administrator).'
        }),
        ('Teacher Relationship', {
            'fields': ('registered_by_teacher',),
            'description': 'If this student was registered by a teacher, the teacher is shown here.'
        }),
        ('Scout Information', {
            'fields': ('date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies', 'groups_membership')
        }),
        ('Registration & Payment Status', {
            'fields': ('registration_status', 'registration_payment_amount', 'registration_total_paid', 'registration_amount_required', 'registration_receipt', 'registration_verified_by', 'registration_verification_date', 'registration_notes', 'membership_expiry'),
            'description': 'Admins and Leaders are auto-activated (no payment required). Scouts/Students must complete payment.'
        }),
    )
    
    def registered_by_teacher_display(self, obj):
        """Display teacher who registered this student"""
        if obj.registered_by_teacher:
            return format_html(
                '<span style="color: #0066cc;">👨‍🏫 {}</span>',
                obj.registered_by_teacher.get_full_name()
            )
        return '-'
    registered_by_teacher_display.short_description = 'Registered By'
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Information', {
            'fields': ('role', 'date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies')
        }),
    )
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users"""
        updated = queryset.update(is_active=True, registration_status='active')
        self.message_user(request, f'{updated} user(s) activated successfully.')
    activate_users.short_description = "✅ Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users (except admins and leaders)"""
        # Don't deactivate admin users or leaders
        queryset = queryset.exclude(role__in=['admin', 'leader'])
        updated = queryset.update(is_active=False, registration_status='inactive')
        self.message_user(request, f'{updated} user(s) deactivated successfully.')
    deactivate_users.short_description = "❌ Deactivate selected users"

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name', 'description']
