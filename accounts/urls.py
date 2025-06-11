from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('scout-dashboard/', views.scout_dashboard, name='scout_dashboard'),
    path('members/', views.member_list, name='member_list'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/', RedirectView.as_view(url=reverse_lazy('profile_edit')), name='profile_redirect'),
] 