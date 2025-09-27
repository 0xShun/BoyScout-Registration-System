from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('submit/', views.payment_submit, name='payment_submit'),
    path('verify/<int:payment_id>/', views.payment_verify, name='payment_verify'),
    
    # QR Code Management URLs
    path('qr-codes/', views.qr_code_manage, name='qr_code_manage'),
    path('qr-codes/edit/<int:qr_code_id>/', views.qr_code_edit, name='qr_code_edit'),
    path('qr-codes/delete/<int:qr_code_id>/', views.qr_code_delete, name='qr_code_delete'),
    path('qr-codes/toggle/<int:qr_code_id>/', views.qr_code_toggle_active, name='qr_code_toggle_active'),
] 