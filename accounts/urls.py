from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('registration-payment/<int:user_id>/', views.registration_payment, name='registration_payment'),
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('logout/', views.MyLogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('scout-dashboard/', views.scout_dashboard, name='scout_dashboard'),
    path('quick-announcement/', views.quick_announcement, name='quick_announcement'),
    path('about/', views.about, name='about'),
    path('members/', views.member_list, name='member_list'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),
    
    # Registration payment management
    path('pending-registrations/', views.pending_registrations, name='pending_registrations'),
    path('verify-registration/<int:user_id>/', views.verify_registration_payment, name='verify_registration_payment'),
    
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Teacher registration and dashboard URLs
    path('register/teacher/', views.register_teacher, name='register_teacher'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/register-students/', views.teacher_register_students, name='teacher_register_students'),
    path('teacher/student/<int:student_id>/edit/', views.teacher_edit_student, name='teacher_edit_student'),
    path('teacher/student/<int:student_id>/delete/', views.teacher_delete_student, name='teacher_delete_student'),
    path('teacher/student/<int:student_id>/reset-password/', views.teacher_reset_student_password, name='teacher_reset_student_password'),
    path('teacher/student/<int:student_id>/toggle-active/', views.teacher_toggle_student_active, name='teacher_toggle_student_active'),
    path('teacher/student/<int:student_id>/payments/', views.teacher_view_student_payments, name='teacher_view_student_payments'),
    path('teacher/student/<int:student_id>/events/', views.teacher_view_student_events, name='teacher_view_student_events'),
]
