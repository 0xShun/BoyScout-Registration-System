"""
Unit tests for attendance session and certificate functionality.
Tests models, views, and certificate generation service.
"""
import os
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import date, time
from decimal import Decimal
from PIL import Image
from io import BytesIO

from events.models import (
    Event, EventRegistration, Attendance, 
    AttendanceSession, CertificateTemplate, EventCertificate
)
from events.services.certificate_service import CertificateService

User = get_user_model()


class AttendanceSessionModelTest(TestCase):
    """Test AttendanceSession model functionality"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            rank='admin'
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
    
    def test_create_attendance_session(self):
        """Test creating an attendance session"""
        session = AttendanceSession.objects.create(event=self.event)
        
        self.assertFalse(session.is_active)
        self.assertIsNone(session.started_at)
        self.assertIsNone(session.started_by)
        self.assertEqual(session.auto_stop_minutes, 0)
        self.assertEqual(str(session), f"{self.event.title} - Attendance Session (Inactive)")
    
    def test_start_attendance_session(self):
        """Test starting an attendance session"""
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.started_at)
        self.assertEqual(session.started_by, self.admin_user)
        self.assertIsNone(session.stopped_at)
    
    def test_stop_attendance_session(self):
        """Test stopping an attendance session"""
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        session.stop()
        
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.stopped_at)
    
    def test_one_to_one_relationship(self):
        """Test that only one session per event is allowed"""
        AttendanceSession.objects.create(event=self.event)
        
        with self.assertRaises(Exception):
            AttendanceSession.objects.create(event=self.event)


class CertificateTemplateModelTest(TestCase):
    """Test CertificateTemplate model functionality"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            rank='admin'
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
    
    def test_create_certificate_template(self):
        """Test creating a certificate template"""
        # Create a simple test image
        image = Image.new('RGB', (100, 100), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile(
            'test_template.png',
            image_io.getvalue(),
            content_type='image/png'
        )
        
        template = CertificateTemplate.objects.create(
            event=self.event,
            template_image=image_file,
            name_x=500,
            name_y=400,
            name_font_size=60
        )
        
        self.assertEqual(template.event, self.event)
        self.assertEqual(template.name_x, 500)
        self.assertEqual(template.name_y, 400)
        self.assertEqual(template.name_font_size, 60)
        self.assertEqual(template.name_color, '#000000')
        self.assertEqual(str(template), f"Certificate Template - {self.event.title}")
    
    def test_default_values(self):
        """Test default positioning values"""
        image = Image.new('RGB', (100, 100), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile('test.png', image_io.getvalue())
        
        template = CertificateTemplate.objects.create(
            event=self.event,
            template_image=image_file
        )
        
        # Check defaults
        self.assertEqual(template.name_x, 500)
        self.assertEqual(template.event_font_size, 40)
        self.assertEqual(template.date_font_size, 30)
        self.assertEqual(template.cert_number_color, '#666666')


class EventCertificateModelTest(TestCase):
    """Test EventCertificate model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            rank='admin'
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
    
    def test_generate_certificate_number(self):
        """Test certificate number generation"""
        cert_number = EventCertificate.generate_certificate_number(
            event_id=1,
            user_id=1
        )
        
        self.assertIn('CERT-1-1-', cert_number)
        self.assertEqual(len(cert_number), 23)  # CERT-1-1-YYYYMMDDHHMMSS
    
    def test_create_certificate(self):
        """Test creating a certificate"""
        # Create test image
        image = Image.new('RGB', (100, 100), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile('cert.png', image_io.getvalue())
        
        cert_number = EventCertificate.generate_certificate_number(
            self.event.id,
            self.user.id
        )
        
        certificate = EventCertificate.objects.create(
            user=self.user,
            event=self.event,
            certificate_number=cert_number,
            certificate_file=image_file
        )
        
        self.assertEqual(certificate.user, self.user)
        self.assertEqual(certificate.event, self.event)
        self.assertIn('CERT-', certificate.certificate_number)
        self.assertTrue(str(certificate).startswith('Certificate #CERT-'))
    
    def test_unique_certificate_number(self):
        """Test that certificate numbers must be unique"""
        image = Image.new('RGB', (100, 100), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        
        cert_number = 'CERT-TEST-12345'
        
        EventCertificate.objects.create(
            user=self.user,
            event=self.event,
            certificate_number=cert_number,
            certificate_file=SimpleUploadedFile('cert1.png', image_io.getvalue())
        )
        
        with self.assertRaises(Exception):
            EventCertificate.objects.create(
                user=self.user,
                event=self.event,
                certificate_number=cert_number,
                certificate_file=SimpleUploadedFile('cert2.png', image_io.getvalue())
            )


class CertificateServiceTest(TestCase):
    """Test CertificateService functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            rank='admin'
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
        
        # Create template image
        image = Image.new('RGB', (1920, 1080), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile('template.png', image_io.getvalue())
        
        self.template = CertificateTemplate.objects.create(
            event=self.event,
            template_image=image_file
        )
        
        # Create attendance
        registration = EventRegistration.objects.create(
            event=self.event,
            user=self.user
        )
        self.attendance = Attendance.objects.create(
            event=self.event,
            user=self.user
        )
    
    def test_hex_to_rgb(self):
        """Test hex color conversion to RGB"""
        rgb = CertificateService._hex_to_rgb('#FF0000')
        self.assertEqual(rgb, (255, 0, 0))
        
        rgb_black = CertificateService._hex_to_rgb('#000000')
        self.assertEqual(rgb_black, (0, 0, 0))
        
        rgb_white = CertificateService._hex_to_rgb('#FFFFFF')
        self.assertEqual(rgb_white, (255, 255, 255))
    
    def test_get_font_path(self):
        """Test font path discovery"""
        font_path = CertificateService._get_font_path()
        self.assertIsNotNone(font_path)
        self.assertIsInstance(font_path, str)
    
    def test_preview_certificate(self):
        """Test certificate preview generation"""
        preview_image = CertificateService.preview_certificate(
            template=self.template,
            preview_name="Test Name",
            preview_event="Test Event Name"
        )
        
        self.assertIsNotNone(preview_image)
        self.assertIsInstance(preview_image, Image.Image)
        self.assertEqual(preview_image.mode, 'RGB')
        self.assertEqual(preview_image.size, (1920, 1080))
    
    def test_generate_certificate(self):
        """Test full certificate generation"""
        certificate = CertificateService.generate_certificate(
            user=self.user,
            event=self.event,
            attendance=self.attendance
        )
        
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.user, self.user)
        self.assertEqual(certificate.event, self.event)
        self.assertEqual(certificate.attendance, self.attendance)
        self.assertIn('CERT-', certificate.certificate_number)
        self.assertTrue(certificate.certificate_file.name.endswith('.png'))
    
    def test_generate_certificate_without_template(self):
        """Test that generation fails without template"""
        # Delete template
        self.template.delete()
        
        # Refresh event from database
        self.event.refresh_from_db()
        
        with self.assertRaises(ValueError) as context:
            CertificateService.generate_certificate(
                user=self.user,
                event=self.event,
                attendance=self.attendance
            )
        
        self.assertIn('No certificate template found', str(context.exception))


class AttendanceSessionViewsTest(TestCase):
    """Test attendance session views"""
    
    def setUp(self):
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            rank='admin',
            is_active=True
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            rank='scout',
            registration_status='payment_verified',
            is_active=True
        )
        
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
        
        # Create registration for student
        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.student_user,
            payment_status='not_required'
        )
    
    def test_start_attendance_session_admin(self):
        """Test admin can start attendance session"""
        self.client.login(email='admin@test.com', password='testpass123')
        
        url = reverse('events:start_attendance_session', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        # Should redirect back to event detail
        self.assertEqual(response.status_code, 302)
        
        # Session should be created and active
        session = AttendanceSession.objects.get(event=self.event)
        self.assertTrue(session.is_active)
        self.assertEqual(session.started_by, self.admin_user)
    
    def test_start_attendance_session_non_admin(self):
        """Test non-admin cannot start attendance session"""
        self.client.login(email='student@test.com', password='testpass123')
        
        url = reverse('events:start_attendance_session', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        # Should be forbidden or redirect
        self.assertIn(response.status_code, [302, 403])
    
    def test_stop_attendance_session(self):
        """Test admin can stop attendance session"""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Start session first
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        
        # Stop session
        url = reverse('events:stop_attendance_session', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.stopped_at)
    
    def test_check_attendance_status_ajax(self):
        """Test AJAX attendance status endpoint"""
        self.client.login(email='student@test.com', password='testpass123')
        
        # Create active session
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        
        url = reverse('events:check_attendance_status', kwargs={'event_id': self.event.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['is_active'])
        self.assertFalse(data['has_attended'])
        self.assertTrue(data['is_eligible'])
    
    def test_mark_attendance_when_active(self):
        """Test student can mark attendance when session is active"""
        self.client.login(email='student@test.com', password='testpass123')
        
        # Create active session
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        
        url = reverse('events:mark_my_attendance', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify attendance was created
        attendance = Attendance.objects.filter(
            event=self.event,
            user=self.student_user
        ).exists()
        self.assertTrue(attendance)
    
    def test_mark_attendance_when_inactive(self):
        """Test student cannot mark attendance when session is inactive"""
        self.client.login(email='student@test.com', password='testpass123')
        
        url = reverse('events:mark_my_attendance', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('error', data)
    
    def test_mark_attendance_duplicate(self):
        """Test student cannot mark attendance twice"""
        self.client.login(email='student@test.com', password='testpass123')
        
        # Create active session
        session = AttendanceSession.objects.create(event=self.event)
        session.start(self.admin_user)
        
        # Mark attendance first time
        Attendance.objects.create(
            event=self.event,
            user=self.student_user
        )
        
        # Try to mark again
        url = reverse('events:mark_my_attendance', kwargs={'event_id': self.event.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('already marked', data['error'])


class CertificateViewsTest(TestCase):
    """Test certificate-related views"""
    
    def setUp(self):
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            rank='admin',
            is_active=True
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            rank='scout',
            registration_status='payment_verified',
            is_active=True
        )
        
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
    
    def test_upload_certificate_template_get(self):
        """Test GET request to upload certificate template page"""
        self.client.login(email='admin@test.com', password='testpass123')
        
        url = reverse('events:upload_certificate_template', kwargs={'event_id': self.event.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Certificate Template')
    
    def test_upload_certificate_template_post(self):
        """Test POST request to upload certificate template"""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Create test image
        image = Image.new('RGB', (1920, 1080), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_io.seek(0)
        image_file = SimpleUploadedFile('template.png', image_io.read(), content_type='image/png')
        
        url = reverse('events:upload_certificate_template', kwargs={'event_id': self.event.id})
        response = self.client.post(url, {
            'template_image': image_file,
            'name_x': 960,
            'name_y': 400,
            'name_font_size': 60,
            'name_color': '#000000',
            'event_name_x': 960,
            'event_name_y': 550,
            'event_font_size': 40,
            'event_color': '#000000',
            'date_x': 960,
            'date_y': 650,
            'date_font_size': 30,
            'date_color': '#000000',
            'cert_number_x': 100,
            'cert_number_y': 100,
            'cert_number_font_size': 20,
            'cert_number_color': '#666666',
        })
        
        # Should redirect to event detail
        self.assertEqual(response.status_code, 302)
        
        # Template should be created
        template = CertificateTemplate.objects.get(event=self.event)
        self.assertEqual(template.name_x, 960)
        self.assertEqual(template.name_font_size, 60)
    
    def test_my_certificates_view(self):
        """Test my certificates page"""
        self.client.login(email='student@test.com', password='testpass123')
        
        # Create a certificate
        image = Image.new('RGB', (100, 100), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile('cert.png', image_io.getvalue())
        
        EventCertificate.objects.create(
            user=self.student_user,
            event=self.event,
            certificate_number='CERT-TEST-123',
            certificate_file=image_file
        )
        
        url = reverse('events:my_certificates')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Certificates')
        self.assertContains(response, 'CERT-TEST-123')
    
    def test_my_certificates_empty(self):
        """Test my certificates page with no certificates"""
        self.client.login(email='student@test.com', password='testpass123')
        
        url = reverse('events:my_certificates')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Certificates Yet')


class IntegrationTest(TestCase):
    """Integration tests for complete workflow"""
    
    def setUp(self):
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            rank='admin',
            is_active=True
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            rank='scout',
            registration_status='payment_verified',
            is_active=True
        )
        
        self.event = Event.objects.create(
            title='Integration Test Event',
            description='Test Description',
            date=date.today(),
            time=time(14, 0),
            location='Test Location',
            created_by=self.admin_user
        )
        
        EventRegistration.objects.create(
            event=self.event,
            user=self.student_user,
            payment_status='not_required'
        )
        
        # Create template
        image = Image.new('RGB', (1920, 1080), color='white')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = SimpleUploadedFile('template.png', image_io.getvalue())
        
        CertificateTemplate.objects.create(
            event=self.event,
            template_image=image_file
        )
    
    def test_complete_attendance_workflow(self):
        """Test complete workflow: start session -> mark attendance -> certificate generated"""
        # Step 1: Admin starts session
        self.client.login(email='admin@test.com', password='testpass123')
        start_url = reverse('events:start_attendance_session', kwargs={'event_id': self.event.id})
        self.client.post(start_url)
        
        session = AttendanceSession.objects.get(event=self.event)
        self.assertTrue(session.is_active)
        
        # Step 2: Student marks attendance
        self.client.login(email='student@test.com', password='testpass123')
        mark_url = reverse('events:mark_my_attendance', kwargs={'event_id': self.event.id})
        response = self.client.post(mark_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Step 3: Verify attendance was created
        attendance = Attendance.objects.get(event=self.event, user=self.student_user)
        self.assertIsNotNone(attendance)
        
        # Step 4: Verify certificate was generated
        certificate = EventCertificate.objects.get(user=self.student_user, event=self.event)
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.attendance, attendance)
        self.assertIn('CERT-', certificate.certificate_number)
        
        # Step 5: Admin stops session
        self.client.login(email='admin@test.com', password='testpass123')
        stop_url = reverse('events:stop_attendance_session', kwargs={'event_id': self.event.id})
        self.client.post(stop_url)
        
        session.refresh_from_db()
        self.assertFalse(session.is_active)
