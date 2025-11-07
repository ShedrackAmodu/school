from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Assign transport permissions to transport manager role'

    def handle(self, *args, **options):
        try:
            # Get the transport manager role
            transport_manager_role = Role.objects.filter(role_type='transport_manager').first()
            if not transport_manager_role:
                self.stdout.write(
                    self.style.ERROR('Transport manager role not found. Please run seed_staff_roles first.')
                )
                return

            # Define transport permissions to assign
            transport_permissions = [
                'transport.add_vehicle',
                'transport.change_vehicle',
                'transport.delete_vehicle',
                'transport.view_vehicle',

                'transport.add_driver',
                'transport.change_driver',
                'transport.delete_driver',
                'transport.view_driver',

                'transport.add_attendant',
                'transport.change_attendant',
                'transport.delete_attendant',
                'transport.view_attendant',

                'transport.add_route',
                'transport.change_route',
                'transport.delete_route',
                'transport.view_route',

                'transport.add_routestop',
                'transport.change_routestop',
                'transport.delete_routestop',
                'transport.view_routestop',

                'transport.add_routeschedule',
                'transport.change_routeschedule',
                'transport.delete_routeschedule',
                'transport.view_routeschedule',

                'transport.add_transportallocation',
                'transport.change_transportallocation',
                'transport.delete_transportallocation',
                'transport.view_transportallocation',

                'transport.add_maintenancerecord',
                'transport.change_maintenancerecord',
                'transport.delete_maintenancerecord',
                'transport.view_maintenancerecord',

                'transport.add_fuelrecord',
                'transport.change_fuelrecord',
                'transport.delete_fuelrecord',
                'transport.view_fuelrecord',

                'transport.add_incidentreport',
                'transport.change_incidentreport',
                'transport.delete_incidentreport',
                'transport.view_incidentreport',
            ]

            permissions_assigned = 0

            for perm_codename in transport_permissions:
                try:
                    app_label, codename = perm_codename.split('.', 1)
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )

                    # Check if permission is already assigned
                    if not transport_manager_role.permissions.filter(pk=permission.pk).exists():
                        transport_manager_role.permissions.add(permission)
                        permissions_assigned += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Assigned permission: {perm_codename}')
                        )
                    else:
                        self.stdout.write(
                            f'Permission already assigned: {perm_codename}'
                        )

                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Permission not found: {perm_codename}')
                    )
                except ValueError:
                    self.stdout.write(
                        self.style.ERROR(f'Invalid permission format: {perm_codename}')
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully assigned {permissions_assigned} permissions to transport manager role'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error assigning permissions: {e}')
            )
