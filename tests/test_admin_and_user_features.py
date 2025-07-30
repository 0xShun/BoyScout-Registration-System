from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Group
from events.models import Event, Attendance
from announcements.models import Announcement
from payments.models import Payment
from notifications.models import Notification
from django.utils import timezone
from decimal import Decimal

class AdminAndUserFeatureTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            rank='admin',
            first_name='Admin',
            last_name='User'
        )
        self.user = User.objects.create_user(
            username='scout',
            email='scout@example.com',
            password='scoutpass123',
            rank='scout',
            first_name='Scout',
            last_name='User'
        )
        self.group = Group.objects.create(name='Test Group')
        self.group.members.add(self.user)

    def login_admin(self):
        login_success = self.client.login(username='admin', password='adminpass123')
        if not login_success:
            login_success = self.client.login(username='admin@example.com', password='adminpass123')
        assert login_success
        response = self.client.get(reverse('accounts:admin_dashboard'))
        assert response.status_code == 200

    def login_user(self):
        login_success = self.client.login(username='scout', password='scoutpass123')
        if not login_success:
            login_success = self.client.login(username='scout@example.com', password='scoutpass123')
        assert login_success
        response = self.client.get(reverse('accounts:scout_dashboard'))
        assert response.status_code == 200

    # --- Admin Feature Tests ---
    def test_admin_can_create_event(self):
        self.login_admin()
        post_data = {
            'title': 'Test Event',
            'description': 'Event for testing',
            'date': timezone.now().date(),
            'time': '10:00',
            'location': 'Test Location',
        }
        response = self.client.post(reverse('events:event_create'), post_data)
        self.assertEqual(response.status_code, 302)
        event = Event.objects.filter(title='Test Event').first()
        self.assertIsNotNone(event)

    def test_admin_can_create_announcement(self):
        self.login_admin()
        post_data = {
            'title': 'Admin Announcement',
            'message': 'This is an admin announcement',
        }
        response = self.client.post(reverse('announcements:announcement_create'), post_data)
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.filter(title='Admin Announcement').first()
        self.assertIsNotNone(announcement)

    def test_admin_can_create_notification(self):
        self.login_admin()
        notification = Notification.objects.create(user=self.user, message='Test notification', type='info')
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.user, self.user)

    def test_admin_can_mark_attendance(self):
        self.login_admin()
        event = Event.objects.create(title='Attendance Event', description='desc', date=timezone.now().date(), time='10:00', location='loc')
        attendance = Attendance.objects.create(event=event, user=self.user, status='present')
        self.assertEqual(attendance.status, 'present')
        self.assertEqual(attendance.user, self.user)

    def test_admin_can_verify_payment(self):
        self.login_admin()
        payment = Payment.objects.create(user=self.user, amount=Decimal('100.00'), status='pending')
        response = self.client.post(reverse('payments:payment_verify', args=[payment.id]), {'action': 'verify', 'notes': 'Verified'})
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'verified')

    def test_admin_can_create_group_and_assign_members(self):
        self.login_admin()
        response = self.client.post(reverse('accounts:group_create'), {'name': 'New Group', 'description': 'desc'})
        self.assertEqual(response.status_code, 302)
        group = Group.objects.filter(name='New Group').first()
        self.assertIsNotNone(group)
        group.members.add(self.user)
        self.assertIn(self.user, group.members.all())

    # --- User Feature Tests ---
    def test_user_can_rsvp_event(self):
        self.login_user()
        event = Event.objects.create(title='RSVP Event', description='desc', date=timezone.now().date(), time='10:00', location='loc')
        # Simulate RSVP (assume form field is 'rsvp')
        response = self.client.post(reverse('events:event_detail', args=[event.id]), {'rsvp': 'yes'})
        self.assertIn(response.status_code, [200, 302])

    def test_user_can_submit_payment(self):
        self.login_user()
        post_data = {
            'payee_name': 'Test User',  # This will be overridden by the view
            'payee_email': 'test@example.com',  # This will be overridden by the view
            'amount': '150.00',
            # Note: gcash_receipt_image is optional (null=True, blank=True)
        }
        response = self.client.post(reverse('payments:payment_submit'), post_data)
        self.assertIn(response.status_code, [200, 302])
        payment = Payment.objects.filter(user=self.user).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('150.00'))
        # The view overrides these with user's actual data
        self.assertEqual(payment.payee_name, 'Scout User')
        self.assertEqual(payment.payee_email, 'scout@example.com')

    def test_user_can_view_and_mark_announcement_read(self):
        self.login_user()
        announcement = Announcement.objects.create(title='User Announcement', message='msg')
        response = self.client.get(reverse('announcements:announcement_list'))
        self.assertEqual(response.status_code, 200)
        # Mark as read
        response = self.client.get(reverse('announcements:announcement_mark_read', args=[announcement.id]))
        self.assertIn(response.status_code, [200, 302])
        announcement.refresh_from_db()
        self.assertIn(self.user, announcement.read_by.all())

    def test_user_can_edit_profile(self):
        self.login_user()
        response = self.client.post(reverse('accounts:profile_edit'), {
            'username': 'scout',
            'email': 'scout@example.com',
            'first_name': 'Scouty',
            'last_name': 'McScoutface',
            'rank': 'scout',
            'phone_number': '1234567890',
            'address': 'Test Address'
        })
        self.assertIn(response.status_code, [200, 302])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Scouty')

    def test_user_can_view_notifications(self):
        self.login_user()
        Notification.objects.create(user=self.user, message='Notif', type='info')
        response = self.client.get(reverse('notifications:inbox'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notif') 