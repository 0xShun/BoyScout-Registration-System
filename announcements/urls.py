app_name = 'announcements'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.announcement_list, name='announcement_list'),
    path('create/', views.announcement_create, name='announcement_create'),
    path('<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('<int:pk>/read/', views.announcement_mark_read, name='announcement_mark_read'),
    path('<int:pk>/toggle-visibility/', views.announcement_toggle_visibility, name='announcement_toggle_visibility'),
    path('<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
] 