from django.contrib.auth.management.commands.createsuperuser import Command as BaseCreateSuperuserCommand

class Command(BaseCreateSuperuserCommand):
    def handle(self, *args, **options):
        super().handle(*args, **options)
        # After the superuser is created, set rank to 'admin'
        from accounts.models import User
        email = options.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                user.rank = 'admin'
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Set rank='admin' for superuser {email}"))
            except User.DoesNotExist:
                pass 