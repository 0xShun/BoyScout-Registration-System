from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_inbox, name='inbox'),
    path('read/<int:pk>/', views.mark_notification_read, name='mark_read'),
    path('api/get/', views.get_notifications, name='get_notifications'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/mark-read/<int:pk>/', views.mark_as_read, name='mark_as_read'),
] 