app_name = 'announcements'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.announcement_list, name='announcement_list'),
    path('create/', views.announcement_create, name='announcement_create'),
    path('<int:pk>/read/', views.announcement_mark_read, name='announcement_mark_read'),
] 