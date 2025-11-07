from django.core.management.base import BaseCommand
from apps.users.models import sync_all_user_permissions


class Command(BaseCommand):
    help = 'Synchronize user permissions based on their roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        self.stdout.write('Starting permission synchronization...')

        try:
            if dry_run:
                # Count users that would be affected
                from django.db.models import Count
                from apps.users.models import User, UserRole

                users_with_roles = User.objects.filter(
                    user_roles__status='active'
                ).distinct().count()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Would synchronize permissions for {users_with_roles} users'
                    )
                )
            else:
                users_updated = sync_all_user_permissions()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully synchronized permissions for {users_updated} users'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during permission synchronization: {e}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Permission synchronization completed')
        )
