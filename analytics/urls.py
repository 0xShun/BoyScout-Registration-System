from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='dashboard'),
    path('export/<str:format>/', views.export_analytics, name='export_analytics'),
] 