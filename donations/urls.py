# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'donations'

urlpatterns = [
    # Public/Scout/Teacher views
    path('', views.campaign_list, name='campaign_list'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaign/<int:pk>/donate/', views.initiate_donation, name='initiate_donation'),
    path('donation/<int:donation_id>/payment/', views.donation_payment, name='donation_payment'),
    path('history/', views.donation_history, name='donation_history'),
    
    # Admin views
    path('admin/campaigns/', views.admin_campaign_list, name='admin_campaign_list'),
    path('admin/campaigns/create/', views.admin_campaign_create, name='admin_campaign_create'),
    path('admin/campaigns/<int:pk>/edit/', views.admin_campaign_edit, name='admin_campaign_edit'),
    path('admin/campaigns/<int:pk>/delete/', views.admin_campaign_delete, name='admin_campaign_delete'),
    path('admin/campaigns/<int:pk>/donations/', views.admin_campaign_donations, name='admin_campaign_donations'),
    path('admin/donations/', views.admin_all_donations, name='admin_all_donations'),
    path('admin/donations/report/', views.admin_donations_report, name='admin_donations_report'),
    path('admin/campaigns/<int:pk>/report/', views.admin_campaign_report, name='admin_campaign_report'),
    
    # Webhook
    path('webhook/paymongo/', views.donation_webhook, name='donation_webhook'),
]
