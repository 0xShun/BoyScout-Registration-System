from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from payments.models import Payment
from announcements.models import Announcement
from django.utils import timezone
from decimal import Decimal

class CriticalFeaturesTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test users
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            rank='admin'
        )
        self.scout = User.objects.create_user(
            username='scout',
            email='scout@example.com',
            password='scoutpass123',
            rank='scout'
        )

    def test_user_registration(self):
        """Test that users can register successfully"""
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'date_of_birth': '2000-01-01',
            'address': 'Test Address'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_admin_login_and_dashboard_access(self):
        """Test that admins can login and access admin dashboard"""
        # Login as admin
        self.client.login(username='admin', password='adminpass123')
        
        # Access admin dashboard
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_scout_login_and_dashboard_access(self):
        """Test that scouts can login and access scout dashboard"""
        # Login as scout
        self.client.login(username='scout', password='scoutpass123')
        
        # Access scout dashboard
        response = self.client.get(reverse('accounts:scout_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scout Dashboard')

    def test_payment_submission(self):
        """Test that users can submit payments"""
        self.client.login(username='scout', password='scoutpass123')
        
        response = self.client.post(reverse('payments:payment_submit'), {
            'amount': '500.00',
            'gcash_receipt_image': '',  # Would need actual file in real test
        })
        self.assertEqual(response.status_code, 302)  # Redirect after submission
        self.assertTrue(Payment.objects.filter(user=self.scout).exists())

    def test_payment_verification_by_admin(self):
        """Test that admins can verify payments"""
        # Create a payment
        payment = Payment.objects.create(
            user=self.scout,
            amount=Decimal('500.00'),
            status='pending'
        )
        
        # Login as admin
        self.client.login(username='admin', password='adminpass123')
        
        # Verify payment
        response = self.client.post(reverse('payments:payment_verify', args=[payment.id]), {
            'action': 'verify',
            'notes': 'Payment verified'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after verification
        
        # Check payment was verified
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'verified')

    def test_announcement_creation_by_admin(self):
        """Test that admins can create announcements"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.post(reverse('announcements:announcement_create'), {
            'title': 'Test Announcement',
            'message': 'This is a test announcement'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        self.assertTrue(Announcement.objects.filter(title='Test Announcement').exists())

    def test_role_based_access_control(self):
        """Test that users can only access appropriate areas"""
        # Scout trying to access admin dashboard
        self.client.login(username='scout', password='scoutpass123')
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Admin trying to access scout dashboard
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('accounts:scout_dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_user_profile_management(self):
        """Test that users can edit their profiles"""
        self.client.login(username='scout', password='scoutpass123')
        
        response = self.client.post(reverse('accounts:profile_edit'), {
            'username': 'scout',
            'email': 'scout@example.com',
            'first_name': 'Updated',
            'last_name': 'Scout',
            'rank': 'scout',
            'phone_number': '9876543210',
            'address': 'Updated Address'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after update
        
        # Check profile was updated
        self.scout.refresh_from_db()
        self.assertEqual(self.scout.first_name, 'Updated') 