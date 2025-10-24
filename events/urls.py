from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('calendar-data/', views.event_calendar_data, name='event_calendar_data'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:event_pk>/photo/upload/', views.photo_upload, name='photo_upload'),
    path('photo/<int:photo_pk>/delete/', views.photo_delete, name='photo_delete'),
    path('photo/<int:photo_pk>/toggle-featured/', views.photo_toggle_featured, name='photo_toggle_featured'),
    path('<int:pk>/attendance/', views.event_attendance, name='event_attendance'),
    path('<int:event_pk>/registration/<int:reg_pk>/verify/', views.verify_event_registration, name='verify_event_registration'),
    path('pending-payments/', views.pending_payments, name='pending_payments'),
] 