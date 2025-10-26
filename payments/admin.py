from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json
from .models import Payment, PaymentQRCode
from .models import WebhookLog
from django.urls import path
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse


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


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    """Admin view for raw webhook logs."""
    list_display = ('id', 'received_at', 'source_ip', 'processed', 'short_body')
    list_filter = ('processed', 'received_at')
    search_fields = ('source_ip', 'body')
    readonly_fields = ('received_at', 'source_ip', 'headers_pretty', 'body', 'processing_error', 'processed')
    ordering = ('-received_at',)
    actions = ['mark_as_processed', 'mark_as_unprocessed']

    def short_body(self, obj):
        b = obj.body or ''
        if len(b) > 120:
            return b[:120] + '...'
        return b
    short_body.short_description = 'Body (truncated)'

    def headers_pretty(self, obj):
        try:
            import json
            return format_html('<pre style="max-height:300px; overflow:auto;">{}</pre>', json.dumps(obj.headers or {}, indent=2))
        except Exception:
            return obj.headers
    headers_pretty.short_description = 'Headers'

    def mark_as_processed(self, request, queryset):
        updated = queryset.update(processed=True)
        self.message_user(request, f'{updated} webhook(s) marked as processed.')
    mark_as_processed.short_description = 'Mark selected as processed'

    def mark_as_unprocessed(self, request, queryset):
        updated = queryset.update(processed=False)
        self.message_user(request, f'{updated} webhook(s) marked as unprocessed.')
    mark_as_unprocessed.short_description = 'Mark selected as unprocessed'

    def replay_webhooks(self, request, queryset):
        """Admin action: re-invoke the webhook handler for selected WebhookLog rows.

        This action constructs a Django test request with the original body and
        headers and calls the `payment_webhook` view directly. It marks each
        log `processed=True` on 2xx responses, and writes the response or
        exception into `processing_error` on failure.
        """
        from django.test import RequestFactory
        try:
            from .views import payment_webhook
        except Exception:
            # Avoid import-time circular import issues by importing locally
            from payments.views import payment_webhook

        rf = RequestFactory()
        results = []
        for log in queryset:
            try:
                meta = {}
                # Reconstruct HTTP_ META headers from stored headers
                if log.headers:
                    for k, v in (log.headers.items()):
                        # Normalize header name to HTTP_HEADER_NAME
                        meta_key = 'HTTP_' + k.upper().replace('-', '_')
                        meta[meta_key] = v
                if log.source_ip:
                    meta['REMOTE_ADDR'] = log.source_ip

                # Build a POST request using the original raw body
                body_bytes = (log.body or '').encode('utf-8')
                req = rf.post('/payments/webhook/', data=body_bytes, content_type='application/json', **meta)

                # Call the view and capture result
                resp = payment_webhook(req)
                status = getattr(resp, 'status_code', None)
                content = getattr(resp, 'content', b'')
                if isinstance(content, bytes):
                    try:
                        content = content.decode('utf-8')
                    except Exception:
                        content = str(content)

                if status and 200 <= int(status) < 300:
                    log.processed = True
                    log.processing_error = ''
                    log.save()
                    results.append((log.id, 'ok'))
                else:
                    log.processed = False
                    log.processing_error = f'Status {status}: {content}'
                    log.save()
                    results.append((log.id, f'error:{status}'))

            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                log.processed = False
                log.processing_error = tb
                log.save()
                results.append((log.id, 'exception'))

        summary = ', '.join(f'{r[0]}={r[1]}' for r in results)
        self.message_user(request, f'Replayed {len(queryset)} webhook(s): {summary}')
    replay_webhooks.short_description = 'Replay selected webhook logs (safe reprocess)'

    actions = ['mark_as_processed', 'mark_as_unprocessed', 'replay_webhooks']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/replay/', self.admin_site.admin_view(self.replay_view), name='payments_webhooklog_replay'),
        ]
        return custom_urls + urls

    def replay_view(self, request, pk):
        """Admin view to replay a single webhook log (invokes payment_webhook)."""
        log = get_object_or_404(WebhookLog, pk=pk)
        from django.test import RequestFactory
        try:
            from payments.views import payment_webhook
        except Exception:
            from .views import payment_webhook

        rf = RequestFactory()
        meta = {}
        if log.headers:
            for k, v in (log.headers.items()):
                meta_key = 'HTTP_' + k.upper().replace('-', '_')
                meta[meta_key] = v
        if log.source_ip:
            meta['REMOTE_ADDR'] = log.source_ip

        body_bytes = (log.body or '').encode('utf-8')
        req = rf.post('/payments/webhook/', data=body_bytes, content_type='application/json', **meta)

        try:
            resp = payment_webhook(req)
            status = getattr(resp, 'status_code', None)
            content = getattr(resp, 'content', b'')
            if isinstance(content, bytes):
                try:
                    content = content.decode('utf-8')
                except Exception:
                    content = str(content)

            if status and 200 <= int(status) < 300:
                log.processed = True
                log.processing_error = ''
                log.save()
                messages.success(request, f'Webhook {log.id} replayed successfully (status {status}).')
            else:
                log.processed = False
                log.processing_error = f'Status {status}: {content}'
                log.save()
                messages.error(request, f'Webhook {log.id} replay failed: status {status}.')

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.processed = False
            log.processing_error = tb
            log.save()
            messages.error(request, f'Webhook {log.id} replay raised exception. See processing_error for details.')

        return redirect(reverse('admin:payments_webhooklog_change', args=[log.id]))
