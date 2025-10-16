from django.contrib import admin
from .models import Payment, PaymentQRCode


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'payment_method', 'status', 'payment_type', 'qr_ph_reference', 'date')
    list_filter = ('status', 'payment_method', 'payment_type', 'date')
    search_fields = ('user__username', 'user__email', 'qr_ph_reference', 'paymongo_payment_id', 'paymongo_source_id')
    readonly_fields = ('date', 'gateway_response', 'paymongo_payment_id', 'paymongo_source_id', 'paymongo_payment_intent_id')
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'amount', 'payment_method', 'payment_type', 'status')
        }),
        ('QR PH Details', {
            'fields': ('qr_ph_reference', 'receipt_image')
        }),
        ('PayMongo Integration', {
            'fields': ('paymongo_source_id', 'paymongo_payment_id', 'paymongo_payment_intent_id', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_by', 'verification_date', 'notes')
        }),
        ('Metadata', {
            'fields': ('payee_name', 'payee_email', 'date', 'expiry_date')
        })
    )


@admin.register(PaymentQRCode)
class PaymentQRCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'gateway_provider', 'is_active', 'created_at')
    list_filter = ('is_active', 'gateway_provider', 'created_at')
    search_fields = ('title', 'merchant_name', 'merchant_id', 'account_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('QR Code Information', {
            'fields': ('title', 'description', 'qr_code', 'is_active', 'created_by')
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
