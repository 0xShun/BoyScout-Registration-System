from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='dashboard'),
    path('export/<str:format>/', views.export_analytics, name='export_analytics'),
    path('financial-dashboard/', views.financial_dashboard, name='financial_dashboard'),
    path('engagement-dashboard/', views.engagement_dashboard, name='engagement_dashboard'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
] 