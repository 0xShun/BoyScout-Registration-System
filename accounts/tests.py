from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


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
