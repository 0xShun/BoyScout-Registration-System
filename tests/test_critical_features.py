from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import User
from payments.models import Payment
from announcements.models import Announcement

class CriticalFeaturesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='scout'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )

    def test_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123',
            'role': 'scout'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful login

    def test_payment_submission(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('payments:payment_submit'), {
            'amount': 100,
            'proof': 'test_proof.jpg'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(user=self.user).exists())

    def test_announcement_creation(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('announcements:announcement_create'), {
            'title': 'Test Announcement',
            'message': 'This is a test announcement',
            'recipients': [self.user.id]
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Announcement.objects.filter(title='Test Announcement').exists())

    def test_member_management(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('member_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_analytics_export(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('analytics:export_analytics', args=['csv']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_password_reset(self):
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful request

    def test_notification_system(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('announcements:announcement_create'), {
            'title': 'Test Notification',
            'message': 'This is a test notification',
            'recipients': [self.user.id],
            'send_email': True,
            'send_sms': False
        })
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.get(title='Test Notification')
        self.assertTrue(announcement.recipients.filter(id=self.user.id).exists()) 