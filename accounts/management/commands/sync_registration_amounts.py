"""
Management command to sync student registration_amount_required with system config
Usage: python manage.py sync_registration_amounts
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from decimal import Decimal
from accounts.models import User
from payments.models import SystemConfiguration


class Command(BaseCommand):
    help = 'Sync all student registration_amount_required with current system config'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Only update students with specific status (e.g., pending_payment, partial_payment)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        status_filter = options.get('status')
        
        # Get current system config
        system_config = SystemConfiguration.get_config()
        registration_fee = system_config.registration_fee if system_config else Decimal('500.00')
        
        self.stdout.write(f"\n📋 Current system registration fee: ₱{registration_fee}\n")
        
        # Get students (exclude admins)
        students = User.objects.filter(rank='scout')
        
        if status_filter:
            students = students.filter(registration_status=status_filter)
            self.stdout.write(f"🔍 Filtering by status: {status_filter}\n")
        
        # Filter students whose registration_amount_required differs from system config
        students_to_update = []
        for student in students:
            if student.registration_amount_required != registration_fee:
                students_to_update.append(student)
        
        if not students_to_update:
            self.stdout.write(self.style.SUCCESS('✅ All students already have correct registration amount!'))
            return
        
        self.stdout.write(f"\n📊 Found {len(students_to_update)} students to update:\n")
        
        updated_count = 0
        status_changed_count = 0
        
        for student in students_to_update:
            old_amount = student.registration_amount_required
            old_status = student.registration_status
            
            self.stdout.write(
                f"\n👤 {student.get_full_name()} ({student.email})"
            )
            self.stdout.write(
                f"   Current: Required=₱{old_amount}, Paid=₱{student.registration_total_paid}, Status={old_status}"
            )
            
            if not dry_run:
                # Update registration amount
                student.registration_amount_required = registration_fee
                student.save()
                
                # Recalculate status
                student.update_registration_status()
                student.refresh_from_db()
                
                new_status = student.registration_status
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Updated: Required=₱{registration_fee}, Paid=₱{student.registration_total_paid}, Status={new_status}"
                    )
                )
                
                updated_count += 1
                if old_status != new_status:
                    status_changed_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Status changed: {old_status} → {new_status}")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"   Would update to: Required=₱{registration_fee}"
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 DRY RUN: Would update {len(students_to_update)} students"
                )
            )
            self.stdout.write("Run without --dry-run to apply changes\n")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Successfully updated {updated_count} students"
                )
            )
            if status_changed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {status_changed_count} students had their status updated"
                    )
                )
