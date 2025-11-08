from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('calendar-data/', views.event_calendar_data, name='event_calendar_data'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/generate-attendance-qr/', views.generate_attendance_qr, name='generate_attendance_qr'),
    path('<int:pk>/attendance/qrcode/download/', views.download_attendance_qr, name='download_attendance_qr'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:event_pk>/photo/upload/', views.photo_upload, name='photo_upload'),
    path('photo/<int:photo_pk>/delete/', views.photo_delete, name='photo_delete'),
    path('photo/<int:photo_pk>/toggle-featured/', views.photo_toggle_featured, name='photo_toggle_featured'),
    path('<int:pk>/attendance/', views.event_attendance, name='event_attendance'),
    path('attendance/verify/', views.verify_attendance, name='verify_attendance'),
    path('attendance/qrcode/<uuid:token>.png', views.public_attendance_qr, name='public_attendance_qr'),
    path('<int:event_pk>/registration/<int:reg_pk>/verify/', views.verify_event_registration, name='verify_event_registration'),
    path('pending-payments/', views.pending_payments, name='pending_payments'),
    path('pending-payments/verify-ajax/', views.verify_event_registration_ajax, name='pending_payments_verify_ajax'),
    path('<int:pk>/send-payment-confirmation-ajax/', views.send_event_payment_confirmation_ajax, name='send_event_payment_confirmation_ajax'),
] 