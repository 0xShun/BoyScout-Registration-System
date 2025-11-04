# -*- coding: utf-8 -*-
"""
Management command to create initial system settings
Run: python manage.py setup_system_settings
"""
from django.core.management.base import BaseCommand
from accounts.models import SystemSettings

class Command(BaseCommand):
    help = 'Create initial system settings'

    def handle(self, *args, **options):
        settings, created = SystemSettings.objects.get_or_create(
            id=1,
            defaults={
                'registration_fee': 500.00,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ System settings created successfully!'))
            self.stdout.write(f'   Registration Fee: ₱{settings.registration_fee}')
        else:
            self.stdout.write(self.style.WARNING('⚠️  System settings already exist'))
            self.stdout.write(f'   Current Registration Fee: ₱{settings.registration_fee}')
        
        self.stdout.write('')
        self.stdout.write('You can now change the registration fee in the admin panel:')
        self.stdout.write('http://localhost:8000/admin/accounts/systemsettings/1/change/')
