from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, Group
from events.models import Event, Attendance
from announcements.models import Announcement
from payments.models import Payment
from notifications.models import Notification
from decimal import Decimal
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seed the database with demo data for testing and demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')
        
        # Create demo users if they don't exist
        admin, created = User.objects.get_or_create(
            email='demo_admin@scoutconnect.com',
            defaults={
                'username': 'demo_admin',
                'first_name': 'Demo',
                'last_name': 'Administrator',
                'rank': 'admin',
                'phone_number': '09123456789',
                'address': '123 Admin Street, City',
                'emergency_contact': 'Emergency Contact',
                'emergency_phone': '09123456788',
            }
        )
        if created:
            admin.set_password('demo123')
            admin.save()
            self.stdout.write(f'Created demo admin: {admin.get_full_name()}')
        
        scout1, created = User.objects.get_or_create(
            email='demo_scout1@scoutconnect.com',
            defaults={
                'username': 'demo_scout1',
                'first_name': 'John',
                'last_name': 'Scout',
                'rank': 'scout',
                'phone_number': '09123456790',
                'address': '456 Scout Street, City',
                'emergency_contact': 'Parent Contact',
                'emergency_phone': '09123456791',
            }
        )
        if created:
            scout1.set_password('demo123')
            scout1.save()
            self.stdout.write(f'Created demo scout 1: {scout1.get_full_name()}')
        
        scout2, created = User.objects.get_or_create(
            email='demo_scout2@scoutconnect.com',
            defaults={
                'username': 'demo_scout2',
                'first_name': 'Jane',
                'last_name': 'Scout',
                'rank': 'scout',
                'phone_number': '09123456792',
                'address': '789 Scout Street, City',
                'emergency_contact': 'Parent Contact',
                'emergency_phone': '09123456793',
            }
        )
        if created:
            scout2.set_password('demo123')
            scout2.save()
            self.stdout.write(f'Created demo scout 2: {scout2.get_full_name()}')
        
        # Create demo groups
        group1, created = Group.objects.get_or_create(
            name='Eagle Patrol',
            defaults={'description': 'Advanced scouts working towards Eagle rank'}
        )
        if created:
            group1.members.add(scout1, scout2)
            self.stdout.write(f'Created demo group: {group1.name}')
        
        group2, created = Group.objects.get_or_create(
            name='Wolf Patrol',
            defaults={'description': 'Junior scouts in Wolf patrol'}
        )
        if created:
            group2.members.add(scout1)
            self.stdout.write(f'Created demo group: {group2.name}')
        
        # Create demo events
        event1, created = Event.objects.get_or_create(
            title='Camping Trip to Mount Apo',
            defaults={
                'description': 'A 3-day camping trip to Mount Apo. Scouts will learn survival skills, navigation, and team building.',
                'date': timezone.now().date() + timedelta(days=7),
                'time': '08:00',
                'location': 'Mount Apo Base Camp',
                'created_by': admin,
            }
        )
        if created:
            self.stdout.write(f'Created demo event: {event1.title}')
        
        event2, created = Event.objects.get_or_create(
            title='First Aid Training Workshop',
            defaults={
                'description': 'Learn essential first aid skills including CPR, bandaging, and emergency response.',
                'date': timezone.now().date() + timedelta(days=3),
                'time': '14:00',
                'location': 'Scout Hall',
                'created_by': admin,
            }
        )
        if created:
            self.stdout.write(f'Created demo event: {event2.title}')
        
        event3, created = Event.objects.get_or_create(
            title='Community Service Day',
            defaults={
                'description': 'Help clean up the local park and plant trees. Earn community service hours.',
                'date': timezone.now().date() + timedelta(days=1),
                'time': '09:00',
                'location': 'City Park',
                'created_by': admin,
            }
        )
        if created:
            self.stdout.write(f'Created demo event: {event3.title}')
        
        # Create demo announcements
        announcement1, created = Announcement.objects.get_or_create(
            title='Important: Upcoming Camping Trip',
            defaults={
                'message': 'The camping trip to Mount Apo is scheduled for next week. Please bring your camping gear and ensure all forms are submitted by Friday.',
                'date_posted': timezone.now() - timedelta(days=1),
            }
        )
        if created:
            announcement1.recipients.add(scout1, scout2)
            self.stdout.write(f'Created demo announcement: {announcement1.title}')
        
        announcement2, created = Announcement.objects.get_or_create(
            title='First Aid Training Registration Open',
            defaults={
                'message': 'Registration for the First Aid Training Workshop is now open. Limited slots available. Contact your patrol leader to register.',
                'date_posted': timezone.now() - timedelta(hours=6),
            }
        )
        if created:
            announcement2.recipients.add(scout1, scout2)
            self.stdout.write(f'Created demo announcement: {announcement2.title}')
        
        announcement3, created = Announcement.objects.get_or_create(
            title='Community Service Day - This Saturday',
            defaults={
                'message': 'Join us this Saturday for community service day. We will be cleaning up the local park and planting trees. Bring work gloves and water bottles.',
                'date_posted': timezone.now() - timedelta(hours=2),
            }
        )
        if created:
            announcement3.recipients.add(scout1, scout2)
            self.stdout.write(f'Created demo announcement: {announcement3.title}')
        
        # Create demo payments
        payment1, created = Payment.objects.get_or_create(
            user=scout1,
            amount=Decimal('500.00'),
            defaults={
                'payee_name': scout1.get_full_name(),
                'payee_email': scout1.email,
                'status': 'verified',
                'verified_by': admin,
                'verification_date': timezone.now() - timedelta(days=2),
                'notes': 'Monthly dues payment',
            }
        )
        if created:
            self.stdout.write(f'Created demo payment: {payment1.amount} for {payment1.user.get_full_name()}')
        
        payment2, created = Payment.objects.get_or_create(
            user=scout2,
            amount=Decimal('500.00'),
            defaults={
                'payee_name': scout2.get_full_name(),
                'payee_email': scout2.email,
                'status': 'pending',
                'notes': 'Monthly dues payment - pending verification',
            }
        )
        if created:
            self.stdout.write(f'Created demo payment: {payment2.amount} for {payment2.user.get_full_name()}')
        
        # Create demo attendance records
        attendance1, created = Attendance.objects.get_or_create(
            event=event1,
            user=scout1,
            defaults={'status': 'present'}
        )
        if created:
            self.stdout.write(f'Created demo attendance: {scout1.get_full_name()} - {event1.title}')
        
        attendance2, created = Attendance.objects.get_or_create(
            event=event2,
            user=scout1,
            defaults={'status': 'present'}
        )
        if created:
            self.stdout.write(f'Created demo attendance: {scout1.get_full_name()} - {event2.title}')
        
        attendance3, created = Attendance.objects.get_or_create(
            event=event2,
            user=scout2,
            defaults={'status': 'absent'}
        )
        if created:
            self.stdout.write(f'Created demo attendance: {scout2.get_full_name()} - {event2.title}')
        
        # Create demo notifications
        notification1, created = Notification.objects.get_or_create(
            user=scout1,
            message='Your payment has been verified. Thank you!',
            defaults={'type': 'payment'}
        )
        if created:
            self.stdout.write(f'Created demo notification for {scout1.get_full_name()}')
        
        notification2, created = Notification.objects.get_or_create(
            user=scout2,
            message='New announcement: Important: Upcoming Camping Trip',
            defaults={'type': 'announcement'}
        )
        if created:
            self.stdout.write(f'Created demo notification for {scout2.get_full_name()}')
        
        self.stdout.write(
            self.style.SUCCESS(
                'Demo data created successfully!\n'
                'Demo Admin: demo_admin@scoutconnect.com / demo123\n'
                'Demo Scout 1: demo_scout1@scoutconnect.com / demo123\n'
                'Demo Scout 2: demo_scout2@scoutconnect.com / demo123'
            )
        ) 