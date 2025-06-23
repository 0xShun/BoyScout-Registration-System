app_name = 'payments'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('submit/', views.payment_submit, name='payment_submit'),
    path('verify/<int:pk>/', views.payment_verify, name='payment_verify'),
    path('receipt/<int:pk>/', views.payment_receipt, name='payment_receipt'),
] 