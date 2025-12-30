"""
Test suite for Phase 10: Admin Oversight Features
Tests admin teacher creation, teacher list, and teacher hierarchy views
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.forms import AdminCreateTeacherForm

User = get_user_model()


class AdminTeacherCreationTest(TestCase):
    """Test AdminCreateTeacherForm functionality"""
    
    def setUp(self):
        """Create admin user for testing"""
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            rank='admin'
        )
        self.client = Client()
    
    def test_form_has_required_fields(self):
        """Test that AdminCreateTeacherForm has all required fields"""
        form = AdminCreateTeacherForm()
        required_fields = ['username', 'email', 'first_name', 'last_name', 
                          'date_of_birth', 'address', 'phone_number', 'password1', 'password2']
        
        for field in required_fields:
            self.assertIn(field, form.fields, f"Field '{field}' is missing from form")
    
    def test_form_validates_with_correct_data(self):
        """Test form validation with valid data"""
        valid_data = {
            'username': 'test_teacher',
            'email': 'teacher@test.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'date_of_birth': '1980-01-01',
            'address': '123 Test Street',
            'phone_number': '+639123456789',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        form = AdminCreateTeacherForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Form should be valid: {form.errors}")
    
    def test_teacher_created_with_correct_attributes(self):
        """Test that created teacher has rank='teacher', is_active=True, registration_status='pending_payment'"""
        teacher_data = {
            'username': 'new_teacher',
            'email': 'newteacher@test.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'date_of_birth': '1985-05-15',
            'address': '456 Teacher Ave',
            'phone_number': '+639987654321',
            'password1': 'TeacherPass123!',
            'password2': 'TeacherPass123!',
        }
        
        form = AdminCreateTeacherForm(data=teacher_data)
        self.assertTrue(form.is_valid())
        teacher = form.save()
        
        self.assertEqual(teacher.rank, 'teacher', "Rank should be 'teacher'")
        self.assertTrue(teacher.is_active, "is_active should be True")
        self.assertEqual(teacher.registration_status, 'pending_payment', "registration_status should be 'pending_payment'")
        self.assertEqual(teacher.registration_amount_required, 500, "registration_amount_required should be 500")


class AdminTeacherViewsTest(TestCase):
    """Test admin teacher management views"""
    
    def setUp(self):
        """Create admin and teacher users for testing"""
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            rank='admin'
        )
        
        self.teacher1 = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            password='pass123',
            first_name='Teacher',
            last_name='One',
            rank='teacher',
            is_active=True,
            registration_status='active'
        )
        
        self.teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='pass123',
            first_name='Teacher',
            last_name='Two',
            rank='teacher',
            is_active=True,
            registration_status='active'
        )
        
        # Create students managed by teacher1
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='pass123',
            first_name='Student',
            last_name='One',
            rank='scout',
            managed_by=self.teacher1,
            registration_status='active'
        )
        
        self.client = Client()
    
    def test_urls_resolve_correctly(self):
        """Test that all admin teacher management URLs resolve"""
        urls_to_test = [
            ('accounts:admin_create_teacher', '/accounts/admin/teachers/create/'),
            ('accounts:admin_teacher_list', '/accounts/admin/teachers/'),
            ('accounts:admin_teacher_hierarchy', '/accounts/admin/teachers/hierarchy/'),
        ]
        
        for url_name, expected_path in urls_to_test:
            path = reverse(url_name)
            self.assertEqual(path, expected_path, f"{url_name} should resolve to {expected_path}")
    
    def test_unauthenticated_access_redirects(self):
        """Test that unauthenticated users are redirected to login"""
        urls = [
            reverse('accounts:admin_create_teacher'),
            reverse('accounts:admin_teacher_list'),
            reverse('accounts:admin_teacher_hierarchy'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"Unauthenticated access to {url} should redirect")
    
    def test_admin_can_access_create_teacher(self):
        """Test that admin can access teacher creation page"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_create_teacher'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Teacher Account')
    
    def test_admin_can_access_teacher_list(self):
        """Test that admin can access teacher list"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_teacher_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher Management')
        self.assertContains(response, 'Teacher One')
        self.assertContains(response, 'Teacher Two')
    
    def test_admin_can_access_hierarchy(self):
        """Test that admin can access teacher hierarchy"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_teacher_hierarchy'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher-Student Hierarchy')
        self.assertContains(response, 'Teacher One')
        self.assertContains(response, 'Student One')
    
    def test_teacher_list_shows_statistics(self):
        """Test that teacher list displays correct statistics"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_teacher_list'))
        
        # Check that context contains teacher stats
        self.assertIn('teacher_stats', response.context)
        teacher_stats = response.context['teacher_stats']
        self.assertEqual(len(teacher_stats), 2, "Should show 2 teachers")
        
        # Find teacher1's stats
        teacher1_stat = next((s for s in teacher_stats if s['teacher'] == self.teacher1), None)
        self.assertIsNotNone(teacher1_stat)
        self.assertEqual(teacher1_stat['total_students'], 1, "Teacher1 should have 1 student")
    
    def test_hierarchy_shows_teacher_student_structure(self):
        """Test that hierarchy view displays teacher-student relationships"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_teacher_hierarchy'))
        
        # Check context data
        self.assertIn('hierarchy', response.context)
        self.assertIn('total_teachers', response.context)
        self.assertIn('total_students', response.context)
        
        hierarchy = response.context['hierarchy']
        self.assertEqual(len(hierarchy), 2, "Should show 2 teachers in hierarchy")
        
        # Check teacher1's students
        teacher1_item = next((h for h in hierarchy if h['teacher'] == self.teacher1), None)
        self.assertIsNotNone(teacher1_item)
        self.assertEqual(teacher1_item['student_count'], 1)
        self.assertEqual(list(teacher1_item['students'])[0], self.student1)


class AdminTeacherCreationIntegrationTest(TestCase):
    """Integration test for complete teacher creation flow"""
    
    def setUp(self):
        """Create admin user"""
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            rank='admin'
        )
        self.client = Client()
        self.client.force_login(self.admin)
    
    def test_complete_teacher_creation_flow(self):
        """Test complete flow: create teacher via form submission"""
        teacher_data = {
            'username': 'integration_teacher',
            'email': 'integration@test.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'date_of_birth': '1990-01-01',
            'address': '789 Integration St',
            'phone_number': '+639111222333',
            'password1': 'VeryStrongP@ss123!',
            'password2': 'VeryStrongP@ss123!',
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:admin_create_teacher'), data=teacher_data)
        
        # Check if form had errors
        if response.status_code == 200:
            # Form has validation errors
            form = response.context['form']
            self.fail(f"Form validation failed with errors: {form.errors}")
        
        # Should redirect to teacher list
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:admin_teacher_list'))
        
        # Verify teacher was created
        teacher = User.objects.get(username='integration_teacher')
        self.assertEqual(teacher.rank, 'teacher')
        self.assertTrue(teacher.is_active)
        self.assertEqual(teacher.registration_status, 'pending_payment')
        self.assertEqual(teacher.email, 'integration@test.com')
        self.assertEqual(teacher.registration_amount_required, 500)
