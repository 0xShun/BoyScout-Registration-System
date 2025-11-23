# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import DonationCampaign, Donation


@admin.register(DonationCampaign)
class DonationCampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'goal_amount', 'current_amount', 'progress_percentage', 'created_at']
    list_filter = ['status', 'goal_reached', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['current_amount', 'goal_reached', 'goal_reached_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('title', 'description', 'status')
        }),
        ('Media', {
            'fields': ('banner_image', 'qr_code_image', 'external_payment_details')
        }),
        ('Goal Settings', {
            'fields': ('goal_amount', 'current_amount', 'goal_reached', 'goal_reached_date')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['user', 'campaign', 'amount', 'status', 'payment_method', 'created_at', 'verified_at']
    list_filter = ['status', 'payment_method', 'is_anonymous', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'campaign__title']
    readonly_fields = ['created_at', 'verified_at', 'paymongo_source_id', 'paymongo_payment_id', 'gateway_response']
    
    fieldsets = (
        ('Donation Information', {
            'fields': ('campaign', 'user', 'amount', 'status', 'message', 'is_anonymous')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'paymongo_source_id', 'paymongo_payment_id', 'gateway_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'verified_at')
        }),
    )

