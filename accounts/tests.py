from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.conf import settings


User = get_user_model()


class PhoneValidationTests(TestCase):
	def test_registration_phone_normalizes_to_e164(self):
		url = reverse('accounts:register')
		email = 'newscout@example.com'
		payload = {
			'username': 'newscout',
			'first_name': 'New',
			'last_name': 'Scout',
			'email': email,
			'phone_number': '09171234567',  # PH mobile format
			'date_of_birth': '2000-01-01',
			'address': 'Test Address',
			'amount': '500',
			'password1': 'StrongPass123!',
			'password2': 'StrongPass123!',
		}
		resp = self.client.post(url, data=payload, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(User.objects.filter(email=email).exists())
		user = User.objects.get(email=email)
		# Accept either PhoneNumber obj or string; compare string
		self.assertEqual(str(user.phone_number), '+639171234567')

	def test_registration_rejects_invalid_phone(self):
		url = reverse('accounts:register')
		email = 'badphone@example.com'
		payload = {
			'username': 'badphone',
			'first_name': 'Bad',
			'last_name': 'Phone',
			'email': email,
			'phone_number': '12345',  # invalid
			'date_of_birth': '2000-01-01',
			'address': 'Test Address',
			'amount': '500',
			'password1': 'StrongPass123!',
			'password2': 'StrongPass123!',
		}
		resp = self.client.post(url, data=payload)
		# Form should render again with errors
		self.assertEqual(resp.status_code, 200)
		form = resp.context.get('form')
		self.assertIsNotNone(form)
		self.assertIn('phone_number', form.errors)
		self.assertFalse(User.objects.filter(email=email).exists())

	def test_profile_edit_normalizes_numbers(self):
		# Create and log in a scout
		user = User.objects.create_user(
			email='scout@example.com',
			username='scoutuser',
			password='StrongPass123!',
			first_name='Test',
			last_name='User',
			rank='scout',
			is_active=True,
		)
		self.client.force_login(user)
		url = reverse('accounts:profile_edit')
		payload = {
			'profile_image': '',
			'username': user.username,
			'email': user.email,
			'first_name': user.first_name,
			'last_name': user.last_name,
			'rank': user.rank,
			'date_of_birth': '2000-01-01',
			'phone_number': '09181234567',  # should become +639181234567
			'address': 'Somewhere',
			'emergency_contact': 'Parent',
			'emergency_phone': '9181234567',  # should become +639181234567
			'medical_conditions': '',
			'allergies': '',
		}
		resp = self.client.post(url, data=payload)
		# Expect redirect to dashboard
		self.assertEqual(resp.status_code, 302)
		user.refresh_from_db()
		self.assertEqual(str(user.phone_number), '+639181234567')
		self.assertEqual(str(user.emergency_phone), '+639181234567')


class RegisterTeacherIntegrationTests(TestCase):
    def _make_teacher_payload(self, email='teacher@school.edu'):
        return {
            'first_name': 'Test',
            'last_name': 'Teacher',
            'email': email,
            'phone_number': '+639171234567',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

    @patch('payments.services.paymongo_service.PayMongoService.create_source')
    def test_anonymous_teacher_auto_login(self, mock_create_source):
        """Anonymous registrant should be auto-logged-in after teacher creation."""
        # Mock PayMongo response: success but no external checkout URL (redirect to home)
        mock_create_source.return_value = {
            'success': True,
            'data': {
                'id': 'src_test_anon',
                'attributes': {
                    'redirect': {'checkout_url': ''}
                }
            }
        }

        url = reverse('accounts:register_teacher')
        email = 'anonteacher@university.edu'
        payload = self._make_teacher_payload(email=email)

        resp = self.client.post(url, data=payload, follow=True)
        # Should redirect (eventually) to home
        self.assertEqual(resp.status_code, 200)
        # User created
        self.assertTrue(User.objects.filter(email=email).exists())
        user = User.objects.get(email=email)
        # Client session should now be authenticated as the new user
        session = self.client.session
        self.assertIn('_auth_user_id', session)
        self.assertEqual(str(user.pk), str(session['_auth_user_id']))

    @patch('payments.services.paymongo_service.PayMongoService.create_source')
    def test_authenticated_creator_preserved(self, mock_create_source):
        """When an authenticated admin creates a teacher, the admin session must be preserved."""
        mock_create_source.return_value = {
            'success': True,
            'data': {
                'id': 'src_test_admin',
                'attributes': {
                    'redirect': {'checkout_url': ''}
                }
            }
        }

        # Create an admin user and log them in
        admin = User.objects.create_user(
            email='admin@example.com',
            username='adminuser',
            password='AdminPass123!',
            role='admin',
            is_active=True
        )
        self.client.force_login(admin)

        url = reverse('accounts:register_teacher')
        email = 'createdbyadmin@college.edu'
        payload = self._make_teacher_payload(email=email)

        resp = self.client.post(url, data=payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        # New teacher created
        self.assertTrue(User.objects.filter(email=email).exists())
        # Admin session preserved
        session = self.client.session
        self.assertIn('_auth_user_id', session)
        self.assertEqual(str(admin.pk), str(session['_auth_user_id']))
