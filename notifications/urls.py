from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_inbox, name='inbox'),
    path('read/<int:pk>/', views.mark_notification_read, name='mark_read'),
] 