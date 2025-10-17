"""
Management command to create student users from paid batch registrations.
Usage: python manage.py process_batch_registration <batch_id>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from accounts.models import BatchRegistration, User, RegistrationPayment
from notifications.services import NotificationService, send_realtime_notification
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Process paid batch registration and create student user accounts'

    def add_arguments(self, parser):
        parser.add_argument('batch_id', type=str, help='Batch Registration ID to process')
        parser.add_argument(
            '--student-data',
            type=str,
            help='JSON file containing student data (if not using session data)'
        )

    def handle(self, *args, **options):
        batch_id = options['batch_id']
        
        try:
            batch_reg = BatchRegistration.objects.get(batch_id=batch_id)
        except BatchRegistration.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Batch registration {batch_id} not found'))
            return

        if batch_reg.status not in ['paid', 'verified']:
            self.stdout.write(self.style.ERROR(f'Batch registration must be paid first. Current status: {batch_reg.status}'))
            return

        # Get student data from file if provided
        student_data_list = []
        if options['student_data']:
            with open(options['student_data'], 'r') as f:
                student_data_list = json.load(f)
        else:
            self.stdout.write(self.style.WARNING('No student data provided. Please provide student data via --student-data'))
            self.stdout.write('Expected JSON format:')
            self.stdout.write('''
[
    {
        "username": "student1",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+639123456789",
        "date_of_birth": "2010-01-01",
        "address": "123 Main St",
        "password": "password123"
    },
    ...
]
            ''')
            return

        if len(student_data_list) != batch_reg.number_of_students:
            self.stdout.write(self.style.ERROR(
                f'Student data count ({len(student_data_list)}) does not match batch registration ({batch_reg.number_of_students})'
            ))
            return

        self.stdout.write(f'Processing batch registration: {batch_id}')
        self.stdout.write(f'Registrar: {batch_reg.registrar_name}')
        self.stdout.write(f'Number of students: {batch_reg.number_of_students}')
        self.stdout.write(f'Total amount: ₱{batch_reg.total_amount}')

        created_users = []
        with transaction.atomic():
            for idx, student_data in enumerate(student_data_list, 1):
                self.stdout.write(f'\n[{idx}/{batch_reg.number_of_students}] Creating user: {student_data.get("email")}')
                
                # Check if user already exists
                if User.objects.filter(email=student_data['email']).exists():
                    self.stdout.write(self.style.WARNING(f'  User with email {student_data["email"]} already exists. Skipping.'))
                    continue
                
                if User.objects.filter(username=student_data['username']).exists():
                    self.stdout.write(self.style.WARNING(f'  Username {student_data["username"]} already exists. Skipping.'))
                    continue

                # Create user
                user = User.objects.create(
                    username=student_data['username'],
                    first_name=student_data['first_name'],
                    last_name=student_data['last_name'],
                    email=student_data['email'],
                    phone_number=student_data.get('phone_number', ''),
                    date_of_birth=student_data.get('date_of_birth'),
                    address=student_data.get('address', ''),
                    password=make_password(student_data['password']),
                    rank='scout',
                    is_active=True,
                    registration_status='active',
                )

                # Create RegistrationPayment record linked to batch
                reg_payment = RegistrationPayment.objects.create(
                    user=user,
                    batch_registration=batch_reg,
                    amount=batch_reg.amount_per_student,
                    status='verified'
                )

                created_users.append(user)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created user: {user.email}'))

                # Send welcome email
                try:
                    NotificationService.send_email(
                        subject='Welcome to ScoutConnect!',
                        message=f'''
Hello {user.first_name} {user.last_name},

Your account has been created as part of a batch registration by {batch_reg.registrar_name}.

Login credentials:
Email: {user.email}
Password: {student_data['password']}

Please login and change your password: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}

Welcome to ScoutConnect!
                        ''',
                        recipient_list=[user.email]
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Could not send email: {str(e)}'))

            # Update batch registration status
            batch_reg.status = 'verified'
            batch_reg.save()

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {len(created_users)} student accounts'))
        self.stdout.write(f'Batch registration {batch_id} marked as verified')

        # Notify registrar
        try:
            NotificationService.send_email(
                subject='Batch Registration Complete - ScoutConnect',
                message=f'''
Dear {batch_reg.registrar_name},

Your batch registration has been processed successfully!

Number of students: {batch_reg.number_of_students}
Students created: {len(created_users)}
Total paid: ₱{batch_reg.total_amount}

All students have been emailed their login credentials.

Thank you for using ScoutConnect!
                ''',
                recipient_list=[batch_reg.registrar_email]
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not send notification email: {str(e)}'))

        # Notify admins
        admin_users = User.objects.filter(rank='admin', is_active=True)
        for admin in admin_users:
            try:
                send_realtime_notification(
                    user_id=admin.id,
                    message=f'Batch registration processed: {batch_reg.registrar_name} - {len(created_users)} students created',
                    notification_type='batch_registration_verified'
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not send notification: {str(e)}'))
