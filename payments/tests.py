from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal
from accounts.models import User
from payments.models import Payment, PaymentQRCode
from payments.forms import TeacherPaymentForm
from io import BytesIO
from PIL import Image
from unittest.mock import patch


class TeacherPaymentManagementTests(TestCase):
    """Test suite for Phase 7: Payment Management by Teachers"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a teacher user
        self.teacher = User.objects.create_user(
            username='teacher_john',
            email='teacher@test.com',
            password='testpass123',
            first_name='John',
            last_name='Teacher',
            rank='teacher',
            registration_status='active'
        )
        
        # Create students managed by the teacher
        self.student1 = User.objects.create_user(
            username='student_alice',
            email='student1@test.com',
            password='testpass123',
            first_name='Alice',
            last_name='Student',
            rank='scout',
            registration_status='active',
            managed_by=self.teacher
        )
        
        self.student2 = User.objects.create_user(
            username='student_bob',
            email='student2@test.com',
            password='testpass123',
            first_name='Bob',
            last_name='Student',
            rank='scout',
            registration_status='active',
            managed_by=self.teacher
        )
        
        # Create an inactive student (should not appear in forms)
        self.inactive_student = User.objects.create_user(
            username='student_inactive',
            email='inactive@test.com',
            password='testpass123',
            first_name='Inactive',
            last_name='Student',
            rank='scout',
            registration_status='inactive',
            managed_by=self.teacher
        )
        
        # Create a student not managed by this teacher
        self.other_student = User.objects.create_user(
            username='student_other',
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='Student',
            rank='scout',
            registration_status='active'
        )
        
        # Create a regular scout (not a teacher)
        self.scout = User.objects.create_user(
            username='scout_regular',
            email='scout@test.com',
            password='testpass123',
            first_name='Regular',
            last_name='Scout',
            rank='scout',
            registration_status='active'
        )

    def create_test_image(self):
        """Helper method to create a test image file"""
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, format='JPEG')
        image_file.seek(0)
        return SimpleUploadedFile(
            name='test_receipt.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

    # ============================================
    # Form Tests
    # ============================================

    def test_teacher_payment_form_shows_only_active_students(self):
        """Test that TeacherPaymentForm only shows teacher's active students"""
        form = TeacherPaymentForm(teacher=self.teacher)
        
        # Get the queryset from the student field
        student_queryset = form.fields['student'].queryset
        
        # Should include active students
        self.assertIn(self.student1, student_queryset)
        self.assertIn(self.student2, student_queryset)
        
        # Should NOT include inactive student
        self.assertNotIn(self.inactive_student, student_queryset)
        
        # Should NOT include other teacher's students
        self.assertNotIn(self.other_student, student_queryset)
        
        # Should have exactly 2 students
        self.assertEqual(student_queryset.count(), 2)

    def test_teacher_payment_form_validation(self):
        """Test form validation for payment submission"""
        receipt = self.create_test_image()
        
        form_data = {
            'student': self.student1.id,
            'amount': '500.00',
            'reference_number': 'TEST123456789',
            'notes': 'Test payment'
        }
        
        form = TeacherPaymentForm(
            teacher=self.teacher,
            data=form_data,
            files={'receipt_image': receipt}
        )
        
        self.assertTrue(form.is_valid())

    # ============================================
    # View Access Tests
    # ============================================

    @patch('payments.views.NotificationService.send_email')
    def test_teacher_submit_payment_access_teacher(self, mock_email):
        """Test that teachers can access payment submission page"""
        self.client.login(username='teacher_john', password='testpass123')
        response = self.client.get(reverse('payments:teacher_submit_payment'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/teacher_submit_payment.html')

    def test_teacher_submit_payment_access_non_teacher(self):
        """Test that non-teachers cannot access payment submission page"""
        self.client.login(username='scout_regular', password='testpass123')
        response = self.client.get(reverse('payments:teacher_submit_payment'))
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)

    def test_teacher_submit_payment_requires_login(self):
        """Test that login is required to access payment submission"""
        response = self.client.get(reverse('payments:teacher_submit_payment'))
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    @patch('payments.views.NotificationService.send_email')
    def test_teacher_payment_history_access_teacher(self, mock_email):
        """Test that teachers can access payment history page"""
        self.client.login(username='teacher_john', password='testpass123')
        response = self.client.get(reverse('payments:teacher_payment_history'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/teacher_payment_history.html')

    # ============================================
    # Payment Submission Tests
    # ============================================

    @patch('payments.views.send_realtime_notification')
    @patch('payments.views.NotificationService.send_email')
    def test_submit_payment_for_student_success(self, mock_email, mock_realtime):
        """Test successful payment submission by teacher"""
        self.client.login(username='teacher_john', password='testpass123')
        
        receipt = self.create_test_image()
        
        post_data = {
            'student': self.student1.id,
            'amount': '500.00',
            'reference_number': 'TEST987654321',
            'notes': 'Monthly membership fee'
        }
        
        response = self.client.post(
            reverse('payments:teacher_submit_payment'),
            data=post_data,
            files={'receipt_image': receipt}
        )
        
        # Should redirect to payment history
        self.assertEqual(response.status_code, 302)
        
        # Check that payment was created
        payment = Payment.objects.filter(user=self.student1).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('500.00'))
        self.assertEqual(payment.notes, 'Monthly membership fee')
        
        # Check auto-approval
        self.assertEqual(payment.status, 'verified')
        self.assertEqual(payment.verified_by, self.teacher)
        self.assertIsNotNone(payment.verification_date)

    @patch('payments.views.send_realtime_notification')
    @patch('payments.views.NotificationService.send_email')
    def test_submit_payment_auto_approval(self, mock_email, mock_realtime):
        """Test that payments are automatically approved when submitted by teacher"""
        self.client.login(username='teacher_john', password='testpass123')
        
        receipt = self.create_test_image()
        
        post_data = {
            'student': self.student1.id,
            'amount': '750.00',
            'reference_number': 'AUTOTEST111',
            'notes': 'Test auto-approval'
        }
        
        self.client.post(
            reverse('payments:teacher_submit_payment'),
            data=post_data,
            files={'receipt_image': receipt}
        )
        
        payment = Payment.objects.filter(user=self.student1).first()
        
        # Verify auto-approval fields
        self.assertEqual(payment.status, 'verified')
        self.assertEqual(payment.verified_by, self.teacher)
        self.assertIsNotNone(payment.verification_date)
        self.assertTrue(payment.verification_date <= timezone.now())

    # ============================================
    # Payment History Tests
    # ============================================

    @patch('payments.views.NotificationService.send_email')
    def test_payment_history_shows_only_teacher_students_payments(self, mock_email):
        """Test that payment history only shows payments for teacher's students"""
        self.client.login(username='teacher_john', password='testpass123')
        
        # Create payments for teacher's students
        payment1 = Payment.objects.create(
            user=self.student1,
            amount=Decimal('500.00'),
            status='verified',
            verified_by=self.teacher
        )
        
        payment2 = Payment.objects.create(
            user=self.student2,
            amount=Decimal('300.00'),
            status='pending'
        )
        
        # Create payment for other student (should not appear)
        payment_other = Payment.objects.create(
            user=self.other_student,
            amount=Decimal('400.00'),
            status='verified'
        )
        
        response = self.client.get(reverse('payments:teacher_payment_history'))
        
        # Check that only teacher's students' payments appear
        payments = response.context['page_obj'].object_list
        self.assertIn(payment1, payments)
        self.assertIn(payment2, payments)
        self.assertNotIn(payment_other, payments)

    @patch('payments.views.NotificationService.send_email')
    def test_payment_history_filter_by_status(self, mock_email):
        """Test filtering payment history by status"""
        self.client.login(username='teacher_john', password='testpass123')
        
        # Create payments with different statuses
        Payment.objects.create(
            user=self.student1,
            amount=Decimal('500.00'),
            status='verified',
            verified_by=self.teacher
        )
        
        Payment.objects.create(
            user=self.student1,
            amount=Decimal('300.00'),
            status='pending'
        )
        
        Payment.objects.create(
            user=self.student2,
            amount=Decimal('400.00'),
            status='rejected'
        )
        
        # Filter by verified status
        response = self.client.get(
            reverse('payments:teacher_payment_history'),
            {'status': 'verified'}
        )
        
        payments = response.context['page_obj'].object_list
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].status, 'verified')

    @patch('payments.views.NotificationService.send_email')
    def test_payment_history_summary_statistics(self, mock_email):
        """Test that payment history shows correct summary statistics"""
        self.client.login(username='teacher_john', password='testpass123')
        
        # Create various payments
        Payment.objects.create(
            user=self.student1,
            amount=Decimal('500.00'),
            status='verified'
        )
        
        Payment.objects.create(
            user=self.student1,
            amount=Decimal('300.00'),
            status='verified'
        )
        
        Payment.objects.create(
            user=self.student2,
            amount=Decimal('200.00'),
            status='pending'
        )
        
        Payment.objects.create(
            user=self.student2,
            amount=Decimal('100.00'),
            status='rejected'
        )
        
        response = self.client.get(reverse('payments:teacher_payment_history'))
        
        summary = response.context['payment_summary']
        
        self.assertEqual(summary['total_payments'], 4)
        self.assertEqual(summary['verified_count'], 2)
        self.assertEqual(summary['pending_count'], 1)
        self.assertEqual(summary['rejected_count'], 1)
        self.assertEqual(summary['total_verified_amount'], Decimal('800.00'))
