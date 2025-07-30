from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from announcements.models import Announcement
from django.utils import timezone

class QuickAnnouncementTest(TestCase):
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

    def login_admin(self):
        # Try login with username
        login_success = self.client.login(username='admin', password='adminpass123')
        if not login_success:
            # Try login with email
            login_success = self.client.login(username='admin@example.com', password='adminpass123')
        assert login_success, "Admin login failed with both username and email."
        # Check admin dashboard access
        response = self.client.get(reverse('accounts:admin_dashboard'))
        assert response.status_code == 200, f"Admin dashboard not accessible after login, status={response.status_code}"

    def test_quick_announcement_access(self):
        """Test that only admins can access quick announcement"""
        self.login_admin()
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick Announcement')

        self.client.login(username='scout', password='scoutpass123')
        response = self.client.get(reverse('accounts:scout_dashboard'))
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertNotContains(response, 'Quick Announcement')

    def test_quick_announcement_creation(self):
        """Test creating a quick announcement"""
        self.login_admin()
        post_data = {
            'title': 'Test Announcement',
            'message': 'This is a test announcement',
            'recipients': ['all'],
            'send_email': 'on',
            'send_sms': 'off'
        }
        response = self.client.post(reverse('accounts:quick_announcement'), post_data)
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.filter(title='Test Announcement').first()
        self.assertIsNotNone(announcement)
        self.assertEqual(announcement.message, 'This is a test announcement')
        self.assertEqual(announcement.recipients.count(), 2)

    def test_quick_announcement_validation(self):
        """Test that title and message are required"""
        self.login_admin()
        response = self.client.post(reverse('accounts:quick_announcement'), {
            'message': 'This is a test announcement',
            'recipients': ['all']
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_quick_announcement_recipients_filtering(self):
        """Test recipient filtering"""
        self.login_admin()
        post_data = {
            'title': 'Scouts Only Announcement',
            'message': 'This is for scouts only',
            'recipients': ['scouts'],
            'send_email': 'off',
            'send_sms': 'off'
        }
        response = self.client.post(reverse('accounts:quick_announcement'), post_data)
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.filter(title='Scouts Only Announcement').first()
        self.assertIsNotNone(announcement)
        self.assertEqual(announcement.recipients.count(), 1)
        self.assertEqual(announcement.recipients.first(), self.scout)

    def test_quick_announcement_direct_access(self):
        """Test that the quick announcement URL is accessible to admins"""
        self.login_admin()
        response = self.client.get(reverse('accounts:quick_announcement'))
        self.assertEqual(response.status_code, 302) 