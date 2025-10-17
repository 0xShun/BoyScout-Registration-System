from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json
from .models import Payment, PaymentQRCode


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'amount_display', 'payment_method_badge', 'status_badge', 'payment_type', 'paymongo_status', 'date')
    list_filter = ('status', 'payment_method', 'payment_type', 'date', 'verification_date')
    search_fields = ('user__username', 'user__email', 'qr_ph_reference', 'paymongo_payment_id', 'paymongo_source_id')
    readonly_fields = ('date', 'gateway_response_display', 'paymongo_payment_id', 'paymongo_source_id', 'paymongo_payment_intent_id', 'receipt_image_preview')
    date_hierarchy = 'date'
    list_per_page = 25
    actions = ['mark_as_verified', 'mark_as_pending', 'export_payment_report']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'amount', 'payment_method', 'payment_type', 'status')
        }),
        ('QR PH Details', {
            'fields': ('qr_ph_reference', 'receipt_image', 'receipt_image_preview')
        }),
        ('PayMongo Integration', {
            'fields': ('paymongo_source_id', 'paymongo_payment_id', 'paymongo_payment_intent_id', 'gateway_response_display'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_by', 'verification_date', 'notes')
        }),
        ('Metadata', {
            'fields': ('payee_name', 'payee_email', 'date', 'expiry_date')
        })
    )
    
    def user_link(self, obj):
        """Display user as clickable link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
    user_link.short_description = 'User'
    
    def amount_display(self, obj):
        """Display amount with currency"""
        return format_html('<strong>₱{:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def payment_method_badge(self, obj):
        """Display payment method with badge"""
        colors = {
            'gcash': 'primary',
            'paymaya': 'success',
            'bank': 'info',
            'cash': 'secondary',
            'qr_ph': 'warning'
        }
        color = colors.get(obj.payment_method, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Payment Method'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'pending': 'warning',
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
    
    def paymongo_status(self, obj):
        """Show if payment was processed via PayMongo"""
        if obj.paymongo_payment_id:
            return format_html(
                '<span class="badge bg-success"><i class="fas fa-check"></i> PayMongo</span>'
            )
        elif obj.paymongo_source_id:
            return format_html(
                '<span class="badge bg-warning"><i class="fas fa-clock"></i> Pending</span>'
            )
        else:
            return format_html(
                '<span class="badge bg-secondary">Manual</span>'
            )
    paymongo_status.short_description = 'Gateway'
    
    def gateway_response_display(self, obj):
        """Display formatted gateway response"""
        if obj.gateway_response:
            try:
                if isinstance(obj.gateway_response, str):
                    data = json.loads(obj.gateway_response)
                else:
                    data = obj.gateway_response
                formatted = json.dumps(data, indent=2)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
            except:
                return obj.gateway_response
        return '-'
    gateway_response_display.short_description = 'Gateway Response'
    
    def receipt_image_preview(self, obj):
        """Display receipt image preview"""
        if obj.receipt_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 200px; max-width: 300px;" /></a>',
                obj.receipt_image.url,
                obj.receipt_image.url
            )
        return '-'
    receipt_image_preview.short_description = 'Receipt Preview'
    
    def mark_as_verified(self, request, queryset):
        """Admin action to mark payments as verified"""
        from django.utils import timezone
        updated = queryset.update(
            status='verified',
            verified_by=request.user,
            verification_date=timezone.now()
        )
        self.message_user(request, f'{updated} payment(s) marked as verified.')
    mark_as_verified.short_description = 'Mark selected as Verified'
    
    def mark_as_pending(self, request, queryset):
        """Admin action to mark payments as pending"""
        updated = queryset.update(status='pending', verified_by=None, verification_date=None)
        self.message_user(request, f'{updated} payment(s) marked as pending.')
    mark_as_pending.short_description = 'Mark selected as Pending'
    
    def export_payment_report(self, request, queryset):
        """Export selected payments to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payment_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Email', 'Amount', 'Payment Method', 'Status', 'Date', 'PayMongo ID'])
        
        for payment in queryset:
            writer.writerow([
                payment.id,
                payment.user.get_full_name(),
                payment.user.email,
                payment.amount,
                payment.get_payment_method_display(),
                payment.get_status_display(),
                payment.date.strftime('%Y-%m-%d %H:%M:%S'),
                payment.paymongo_payment_id or '-'
            ])
        
        return response
    export_payment_report.short_description = 'Export selected to CSV'


@admin.register(PaymentQRCode)
class PaymentQRCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'gateway_provider', 'is_active_badge', 'created_at')
    list_filter = ('is_active', 'gateway_provider', 'created_at')
    search_fields = ('title', 'merchant_name', 'merchant_id', 'account_number')
    readonly_fields = ('created_at', 'updated_at', 'qr_code_preview')
    
    fieldsets = (
        ('QR Code Information', {
            'fields': ('title', 'description', 'qr_code', 'qr_code_preview', 'is_active', 'created_by')
        }),
        ('QR PH Details', {
            'fields': ('qr_ph_string', 'merchant_id', 'merchant_name', 'account_number')
        }),
        ('PayMongo Integration', {
            'fields': ('gateway_provider', 'paymongo_public_key', 'paymongo_secret_key', 'paymongo_webhook_secret'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def is_active_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-secondary">Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def qr_code_preview(self, obj):
        """Display QR code preview"""
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="max-height: 300px;" />',
                obj.qr_code.url
            )
        return '-'
    qr_code_preview.short_description = 'QR Code Preview'
