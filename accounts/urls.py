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
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('scout-dashboard/', views.scout_dashboard, name='scout_dashboard'),
    path('quick-announcement/', views.quick_announcement, name='quick_announcement'),
    
    # BSP History page (public access)
    path('bsp-history/', views.bsp_history, name='bsp_history'),
    
    # Teacher student management URLs
    path('teacher/students/', views.teacher_student_list, name='teacher_student_list'),
    path('teacher/students/create/', views.teacher_create_student, name='teacher_create_student'),
    path('teacher/students/<int:student_id>/', views.teacher_student_detail, name='teacher_student_detail'),
    path('teacher/students/<int:student_id>/edit/', views.teacher_edit_student, name='teacher_edit_student'),
    path('teacher/students/<int:student_id>/delete/', views.teacher_delete_student, name='teacher_delete_student'),
    path('teacher/students/<int:student_id>/payment/', views.teacher_student_payment, name='teacher_student_payment'),
    path('teacher/bulk-payment/', views.teacher_bulk_payment, name='teacher_bulk_payment'),
    path('teacher/bulk-payment-status/', views.teacher_bulk_payment_status, name='teacher_bulk_payment_status'),
    path('teacher/bulk-student-payment/', views.teacher_bulk_student_payment, name='teacher_bulk_student_payment'),
    path('teacher/bulk-student-payment-status/', views.teacher_bulk_student_payment_status, name='teacher_bulk_student_payment_status'),
    
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
    path('badges/', views.badge_list, name='badge_list'),
    path('badges/<int:pk>/manage/', views.badge_manage, name='badge_manage'),
    
    # Registration payment management
    path('pending-registrations/', views.pending_registrations, name='pending_registrations'),
    path('verify-registration/<int:user_id>/', views.verify_registration_payment, name='verify_registration_payment'),
    
    # Admin teacher management URLs
    path('admin/teachers/create/', views.admin_create_teacher, name='admin_create_teacher'),
    path('admin/teachers/', views.admin_teacher_list, name='admin_teacher_list'),
    path('admin/teachers/hierarchy/', views.admin_teacher_hierarchy, name='admin_teacher_hierarchy'),
    
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
] 