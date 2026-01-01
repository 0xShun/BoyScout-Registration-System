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
    
    # PayMongo Webhook & Payment Status
    path('webhooks/paymongo/', views.paymongo_webhook, name='paymongo_webhook'),
    path('payment-status/<int:registration_id>/<str:status>/', views.payment_status, name='payment_status'),
    path('clear-paymongo-session/', views.clear_paymongo_session, name='clear_paymongo_session'),
] 