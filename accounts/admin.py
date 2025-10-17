from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Group, Badge, UserBadge, RegistrationPayment, BatchRegistration, BatchStudentData
from django.utils.html import format_html

@admin.register(BatchRegistration)
class BatchRegistrationAdmin(admin.ModelAdmin):
    list_display = ['batch_id_display', 'registrar_name', 'registrar_email', 'number_of_students', 'total_amount_display', 'status_badge', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['batch_id', 'registrar_name', 'registrar_email', 'registrar_phone']
    readonly_fields = ['batch_id', 'created_at', 'updated_at', 'paymongo_source_id', 'paymongo_payment_id']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_id', 'registrar', 'registrar_name', 'registrar_email', 'registrar_phone')
        }),
        ('Payment Details', {
            'fields': ('number_of_students', 'amount_per_student', 'total_amount', 'status')
        }),
        ('PayMongo Integration', {
            'fields': ('paymongo_source_id', 'paymongo_payment_id'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_by', 'verification_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def batch_id_display(self, obj):
        return str(obj.batch_id)[:8] + "..."
    batch_id_display.short_description = 'Batch ID'
    
    def total_amount_display(self, obj):
        return format_html('<strong>₱{:.2f}</strong>', obj.total_amount)
    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'paid': 'info',
            'verified': 'success',
            'rejected': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    actions = ['mark_as_verified', 'mark_as_rejected']
    
    def mark_as_verified(self, request, queryset):
        queryset.update(status='verified', verified_by=request.user)
        self.message_user(request, f'{queryset.count()} batch registration(s) marked as verified.')
    mark_as_verified.short_description = 'Mark selected as verified'
    
    def mark_as_rejected(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} batch registration(s) marked as rejected.')
    mark_as_rejected.short_description = 'Mark selected as rejected'


@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'batch_registration_display', 'amount', 'status', 'created_at', 'verified_by']
    list_filter = ['status', 'created_at', 'batch_registration']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def batch_registration_display(self, obj):
        if obj.batch_registration:
            return format_html(
                '<span class="badge bg-info">Batch: {}</span>',
                str(obj.batch_registration.batch_id)[:8]
            )
        return '-'
    batch_registration_display.short_description = 'Batch'


@admin.register(BatchStudentData)
class BatchStudentDataAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'email', 'batch_display', 'user_created_display', 'created_at']
    list_filter = ['created_at', 'batch_registration__status']
    search_fields = ['first_name', 'last_name', 'email', 'username']
    readonly_fields = ['batch_registration', 'created_at', 'created_user']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('first_name', 'last_name', 'username', 'email', 'phone_number', 'date_of_birth', 'address')
        }),
        ('Batch Registration', {
            'fields': ('batch_registration',)
        }),
        ('Account Creation', {
            'fields': ('created_user', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def student_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    student_name.short_description = 'Student Name'
    
    def batch_display(self, obj):
        return format_html(
            '<a href="/admin/accounts/batchregistration/{}/change/">{}</a>',
            obj.batch_registration.id,
            str(obj.batch_registration.batch_id)[:12] + "..."
        )
    batch_display.short_description = 'Batch ID'
    
    def user_created_display(self, obj):
        if obj.created_user:
            return format_html(
                '<span class="badge bg-success">✓ Created</span>'
            )
        return format_html(
            '<span class="badge bg-warning">Pending</span>'
        )
    user_created_display.short_description = 'Status'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'rank', 'registration_status', 'is_active', 'date_joined']
    list_filter = ['rank', 'registration_status', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    actions = ['activate_users', 'deactivate_users']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Scout Information', {
            'fields': ('rank', 'date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies', 'groups_membership')
        }),
        ('Registration & Status', {
            'fields': ('registration_status', 'registration_payment_amount', 'registration_total_paid', 'registration_amount_required', 'registration_receipt', 'registration_verified_by', 'registration_verification_date', 'registration_notes', 'membership_expiry')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Scout Information', {
            'fields': ('rank', 'date_of_birth', 'address', 'phone_number', 'emergency_contact', 'emergency_phone', 'medical_conditions', 'allergies')
        }),
    )
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users"""
        updated = queryset.update(is_active=True, registration_status='active')
        self.message_user(request, f'{updated} user(s) activated successfully.')
    activate_users.short_description = "✅ Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users (except admins)"""
        # Don't deactivate admin users
        queryset = queryset.exclude(rank='admin')
        updated = queryset.update(is_active=False, registration_status='inactive')
        self.message_user(request, f'{updated} user(s) deactivated successfully.')
    deactivate_users.short_description = "❌ Deactivate selected users"

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
