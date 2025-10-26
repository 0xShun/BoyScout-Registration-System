from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User


class Command(BaseCommand):
    help = "Convert legacy registration_status values 'Active Member' -> 'active' (dry-run by default)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Apply changes to the database')

    def handle(self, *args, **options):
        apply_changes = options.get('apply', False)

        qs = User.objects.filter(registration_status='Active Member')
        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No users with registration_status="Active Member" found.'))
            return

        self.stdout.write(f'Found {count} user(s) with registration_status="Active Member"')

        # Show a sample of affected users
        sample = qs.order_by('id')[:10]
        for u in sample:
            self.stdout.write(f' - id={u.id} email={u.email} status={u.registration_status}')

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run mode (no changes made). Run with --apply to modify the database.'))
            return

        # Apply changes in a transaction
        with transaction.atomic():
            updated = qs.update(registration_status='active')
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} user(s) to registration_status="active"'))
