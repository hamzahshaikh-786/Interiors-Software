from django.core.management.base import BaseCommand
from users.models import User

class Command(BaseCommand):
    help = 'Setup a superadmin user'

    def handle(self, *args, **options):
        username = 'superadmin'
        email = 'superadmin@example.com'
        password = 'pass'
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role=User.SUPERADMIN
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created superadmin user "{username}" with password "{password}"'))
        else:
            user = User.objects.get(username=username)
            user.role = User.SUPERADMIN
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'User "{username}" already exists. Updated role to SUPERADMIN.'))
