from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:event_pk>/photo/upload/', views.photo_upload, name='photo_upload'),
    path('photo/<int:photo_pk>/delete/', views.photo_delete, name='photo_delete'),
    path('photo/<int:photo_pk>/toggle-featured/', views.photo_toggle_featured, name='photo_toggle_featured'),
    path('<int:pk>/attendance/', views.event_attendance, name='event_attendance'),
    path('<int:event_pk>/registration/<int:reg_pk>/verify/', views.verify_event_registration, name='verify_event_registration'),
    
    # Teacher URLs
    path('teacher/register-students/', views.teacher_register_students_event, name='teacher_register_students_event'),
    path('teacher/mark-attendance/', views.teacher_mark_attendance, name='teacher_mark_attendance'),
    path('teacher-bulk-event-payment-status/<int:event_id>/', views.teacher_bulk_event_payment_status, name='teacher_bulk_event_payment_status'),
    path('teacher/bulk-download-certificates/', views.teacher_bulk_download_certificates, name='teacher_bulk_download_certificates'),
    
    # PayMongo Webhook & Payment Status
    path('webhooks/paymongo/', views.paymongo_webhook, name='paymongo_webhook'),
    path('payment-status/<int:registration_id>/<str:status>/', views.payment_status, name='payment_status'),
    path('clear-paymongo-session/', views.clear_paymongo_session, name='clear_paymongo_session'),
    
    # Attendance Session & Certificate URLs
    path('<int:event_id>/start-attendance/', views.start_attendance_session, name='start_attendance_session'),
    path('<int:event_id>/stop-attendance/', views.stop_attendance_session, name='stop_attendance_session'),
    path('<int:event_id>/attendance-status/', views.check_attendance_status, name='check_attendance_status'),
    path('<int:event_id>/mark-attendance/', views.mark_my_attendance, name='mark_my_attendance'),
    path('<int:event_id>/upload-certificate/', views.upload_certificate_template, name='upload_certificate_template'),
    path('<int:event_id>/preview-certificate/', views.preview_certificate_template, name='preview_certificate_template'),
    path('my-certificates/', views.my_certificates, name='my_certificates'),
    path('bulk-download-certificates/', views.bulk_download_certificates, name='bulk_download_certificates'),
] 