from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Assign appropriate permissions to all staff roles'

    def handle(self, *args, **options):
        # Define permissions for each role type
        role_permissions = {
            'super_admin': self._get_super_admin_permissions(),
            'admin': self._get_admin_permissions(),
            'principal': self._get_principal_permissions(),
            'department_head': self._get_department_head_permissions(),
            'counselor': self._get_counselor_permissions(),
            'teacher': self._get_teacher_permissions(),
            'accountant': self._get_accountant_permissions(),
            'librarian': self._get_librarian_permissions(),
            'driver': self._get_driver_permissions(),
            'support': self._get_support_permissions(),
            'transport_manager': self._get_transport_manager_permissions(),
            'hostel_warden': self._get_hostel_warden_permissions(),
        }

        total_assigned = 0

        for role_type, permissions in role_permissions.items():
            try:
                role = Role.objects.filter(role_type=role_type).first()
                if not role:
                    self.stdout.write(
                        self.style.WARNING(f'Role {role_type} not found, skipping')
                    )
                    continue

                self.stdout.write(f'Assigning permissions to {role.name}...')

                role_assigned = 0
                for perm_codename in permissions:
                    try:
                        app_label, codename = perm_codename.split('.', 1)
                        permission = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename
                        )

                        if not role.permissions.filter(pk=permission.pk).exists():
                            role.permissions.add(permission)
                            role_assigned += 1
                            total_assigned += 1

                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Permission not found: {perm_codename}')
                        )
                    except ValueError:
                        self.stdout.write(
                            self.style.ERROR(f'Invalid permission format: {perm_codename}')
                        )

                self.stdout.write(
                    self.style.SUCCESS(f'Assigned {role_assigned} permissions to {role.name}')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error assigning permissions to {role_type}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Total permissions assigned: {total_assigned}')
        )

    def _get_super_admin_permissions(self):
        """Super admin gets all permissions"""
        return [
            # Users
            'users.add_user', 'users.change_user', 'users.delete_user', 'users.view_user',
            'users.add_role', 'users.change_role', 'users.delete_role', 'users.view_role',
            'users.approve_applications',

            # Academics
            'academics.add_academicsession', 'academics.change_academicsession', 'academics.delete_academicsession', 'academics.view_academicsession',
            'academics.add_department', 'academics.change_department', 'academics.delete_department', 'academics.view_department',
            'academics.add_subject', 'academics.change_subject', 'academics.delete_subject', 'academics.view_subject',
            'academics.add_class', 'academics.change_class', 'academics.delete_class', 'academics.view_class',
            'academics.add_student', 'academics.change_student', 'academics.delete_student', 'academics.view_student',
            'academics.add_teacher', 'academics.change_teacher', 'academics.delete_teacher', 'academics.view_teacher',
            'academics.add_enrollment', 'academics.change_enrollment', 'academics.delete_enrollment', 'academics.view_enrollment',
            'academics.add_timetable', 'academics.change_timetable', 'academics.delete_timetable', 'academics.view_timetable',
            'academics.add_classmaterial', 'academics.change_classmaterial', 'academics.delete_classmaterial', 'academics.view_classmaterial',

            # Assessment
            'assessment.add_exam', 'assessment.change_exam', 'assessment.delete_exam', 'assessment.view_exam',
            'assessment.add_assignment', 'assessment.change_assignment', 'assessment.delete_assignment', 'assessment.view_assignment',
            'assessment.add_result', 'assessment.change_result', 'assessment.delete_result', 'assessment.view_result',
            'assessment.add_reportcard', 'assessment.change_reportcard', 'assessment.delete_reportcard', 'assessment.view_reportcard',
            'assessment.add_mark', 'assessment.change_mark', 'assessment.delete_mark', 'assessment.view_mark',

            # Attendance
            'attendance.add_dailyattendance', 'attendance.change_dailyattendance', 'attendance.delete_dailyattendance', 'attendance.view_dailyattendance',
            'attendance.add_attendancesession', 'attendance.change_attendancesession', 'attendance.delete_attendancesession', 'attendance.view_attendancesession',
            'attendance.add_periodattendance', 'attendance.change_periodattendance', 'attendance.delete_periodattendance', 'attendance.view_periodattendance',
            'attendance.add_leave', 'attendance.change_leave', 'attendance.delete_leave', 'attendance.view_leave',
            'attendance.add_attendancesummary', 'attendance.change_attendancesummary', 'attendance.delete_attendancesummary', 'attendance.view_attendancesummary',

            # Communication
            'communication.add_announcement', 'communication.change_announcement', 'communication.delete_announcement', 'communication.view_announcement',
            'communication.add_noticeboard', 'communication.change_noticeboard', 'communication.delete_noticeboard', 'communication.view_noticeboard',
            'communication.add_emailtemplate', 'communication.change_emailtemplate', 'communication.delete_emailtemplate', 'communication.view_emailtemplate',
            'communication.add_smstemplate', 'communication.change_smstemplate', 'communication.delete_smstemplate', 'communication.view_smstemplate',
            'communication.add_message', 'communication.change_message', 'communication.delete_message', 'communication.view_message',
            'communication.add_realtimenotification', 'communication.change_realtimenotification', 'communication.delete_realtimenotification', 'communication.view_realtimenotification',

            # Finance
            'finance.add_invoice', 'finance.change_invoice', 'finance.delete_invoice', 'finance.view_invoice',
            'finance.add_payment', 'finance.change_payment', 'finance.delete_payment', 'finance.view_payment',
            'finance.add_feestructure', 'finance.change_feestructure', 'finance.delete_feestructure', 'finance.view_feestructure',
            'finance.add_expense', 'finance.change_expense', 'finance.delete_expense', 'finance.view_expense',
            'finance.add_financialreport', 'finance.change_financialreport', 'finance.delete_financialreport', 'finance.view_financialreport',

            # Library
            'library.add_library', 'library.change_library', 'library.delete_library', 'library.view_library',
            'library.add_author', 'library.change_author', 'library.delete_author', 'library.view_author',
            'library.add_publisher', 'library.change_publisher', 'library.delete_publisher', 'library.view_publisher',
            'library.add_bookcategory', 'library.change_bookcategory', 'library.delete_bookcategory', 'library.view_bookcategory',
            'library.add_book', 'library.change_book', 'library.delete_book', 'library.view_book',
            'library.add_bookcopy', 'library.change_bookcopy', 'library.delete_bookcopy', 'library.view_bookcopy',
            'library.add_librarymember', 'library.change_librarymember', 'library.delete_librarymember', 'library.view_librarymember',
            'library.add_borrowrecord', 'library.change_borrowrecord', 'library.delete_borrowrecord', 'library.view_borrowrecord',
            'library.add_reservation', 'library.change_reservation', 'library.delete_reservation', 'library.view_reservation',
            'library.add_finepayment', 'library.change_finepayment', 'library.delete_finepayment', 'library.view_finepayment',

            # Transport
            'transport.add_vehicle', 'transport.change_vehicle', 'transport.delete_vehicle', 'transport.view_vehicle',
            'transport.add_driver', 'transport.change_driver', 'transport.delete_driver', 'transport.view_driver',
            'transport.add_attendant', 'transport.change_attendant', 'transport.delete_attendant', 'transport.view_attendant',
            'transport.add_route', 'transport.change_route', 'transport.delete_route', 'transport.view_route',
            'transport.add_routestop', 'transport.change_routestop', 'transport.delete_routestop', 'transport.view_routestop',
            'transport.add_routeschedule', 'transport.change_routeschedule', 'transport.delete_routeschedule', 'transport.view_routeschedule',
            'transport.add_transportallocation', 'transport.change_transportallocation', 'transport.delete_transportallocation', 'transport.view_transportallocation',
            'transport.add_maintenancerecord', 'transport.change_maintenancerecord', 'transport.delete_maintenancerecord', 'transport.view_maintenancerecord',
            'transport.add_fuelrecord', 'transport.change_fuelrecord', 'transport.delete_fuelrecord', 'transport.view_fuelrecord',
            'transport.add_incidentreport', 'transport.change_incidentreport', 'transport.delete_incidentreport', 'transport.view_incidentreport',

            # Hostels
            'hostels.add_hostel', 'hostels.change_hostel', 'hostels.delete_hostel', 'hostels.view_hostel',
            'hostels.add_room', 'hostels.change_room', 'hostels.delete_room', 'hostels.view_room',
            'hostels.add_bed', 'hostels.change_bed', 'hostels.delete_bed', 'hostels.view_bed',
            'hostels.add_allocation', 'hostels.change_allocation', 'hostels.delete_allocation', 'hostels.view_allocation',
            'hostels.add_fee', 'hostels.change_fee', 'hostels.delete_fee', 'hostels.view_fee',
            'hostels.add_visitor', 'hostels.change_visitor', 'hostels.delete_visitor', 'hostels.view_visitor',
            'hostels.add_maintenance', 'hostels.change_maintenance', 'hostels.delete_maintenance', 'hostels.view_maintenance',
            'hostels.add_inventory', 'hostels.change_inventory', 'hostels.delete_inventory', 'hostels.view_inventory',

            # Activities
            'activities.add_activity', 'activities.change_activity', 'activities.delete_activity', 'activities.view_activity',
            'activities.add_enrollment', 'activities.change_enrollment', 'activities.delete_enrollment', 'activities.view_enrollment',
            'activities.add_equipment', 'activities.change_equipment', 'activities.delete_equipment', 'activities.view_equipment',
            'activities.add_budget', 'activities.change_budget', 'activities.delete_budget', 'activities.view_budget',
            'activities.add_competition', 'activities.change_competition', 'activities.delete_competition', 'activities.view_competition',

            # Health
            'health.add_healthrecord', 'health.change_healthrecord', 'health.delete_healthrecord', 'health.view_healthrecord',
            'health.add_medicalappointment', 'health.change_medicalappointment', 'health.delete_medicalappointment', 'health.view_medicalappointment',
            'health.add_medication', 'health.change_medication', 'health.delete_medication', 'health.view_medication',

            # Audit
            'audit.add_auditlog', 'audit.change_auditlog', 'audit.delete_auditlog', 'audit.view_auditlog',

            # Analytics
            'analytics.add_analyticsreport', 'analytics.change_analyticsreport', 'analytics.delete_analyticsreport', 'analytics.view_analyticsreport',

            # Support
            'support.add_helpcenter', 'support.change_helpcenter', 'support.delete_helpcenter', 'support.view_helpcenter',
            'support.add_faq', 'support.change_faq', 'support.delete_faq', 'support.view_faq',
            'support.add_resource', 'support.change_resource', 'support.delete_resource', 'support.view_resource',
        ]

    def _get_admin_permissions(self):
        """Admin gets most permissions except super admin only permissions"""
        permissions = self._get_teacher_permissions() + self._get_accountant_permissions() + self._get_librarian_permissions()
        permissions.extend([
            # Users management
            'users.add_user', 'users.change_user', 'users.delete_user', 'users.view_user',
            'users.add_role', 'users.change_role', 'users.view_role',
            'users.approve_applications',

            # Transport
            'transport.add_vehicle', 'transport.change_vehicle', 'transport.view_vehicle',
            'transport.add_driver', 'transport.change_driver', 'transport.view_driver',
            'transport.add_route', 'transport.change_route', 'transport.view_route',
            'transport.add_routeschedule', 'transport.change_routeschedule', 'transport.view_routeschedule',
            'transport.add_transportallocation', 'transport.change_transportallocation', 'transport.view_transportallocation',

            # Hostels
            'hostels.add_hostel', 'hostels.change_hostel', 'hostels.view_hostel',
            'hostels.add_room', 'hostels.change_room', 'hostels.view_room',
            'hostels.add_allocation', 'hostels.change_allocation', 'hostels.view_allocation',

            # Activities
            'activities.add_activity', 'activities.change_activity', 'activities.view_activity',
            'activities.add_enrollment', 'activities.change_enrollment', 'activities.view_enrollment',

            # Communication
            'communication.add_announcement', 'communication.change_announcement', 'communication.view_announcement',
            'communication.add_noticeboard', 'communication.change_noticeboard', 'communication.view_noticeboard',
        ])
        return permissions

    def _get_principal_permissions(self):
        """Principal gets academic oversight permissions"""
        permissions = self._get_teacher_permissions()
        permissions.extend([
            # Academic oversight
            'academics.add_student', 'academics.change_student', 'academics.view_student',
            'academics.add_teacher', 'academics.change_teacher', 'academics.view_teacher',
            'academics.add_enrollment', 'academics.change_enrollment', 'academics.view_enrollment',
            'academics.add_timetable', 'academics.change_timetable', 'academics.view_timetable',

            # Assessment oversight
            'assessment.add_exam', 'assessment.change_exam', 'assessment.view_exam',
            'assessment.add_result', 'assessment.change_result', 'assessment.view_result',
            'assessment.add_reportcard', 'assessment.change_reportcard', 'assessment.view_reportcard',

            # Communication
            'communication.add_announcement', 'communication.change_announcement', 'communication.view_announcement',
        ])
        return permissions

    def _get_department_head_permissions(self):
        """Department head gets department-specific permissions"""
        permissions = self._get_teacher_permissions()
        permissions.extend([
            'academics.add_subject', 'academics.change_subject', 'academics.view_subject',
            'academics.add_timetable', 'academics.change_timetable', 'academics.view_timetable',
            'assessment.add_exam', 'assessment.change_exam', 'assessment.view_exam',
        ])
        return permissions

    def _get_counselor_permissions(self):
        """Counselor gets student support permissions"""
        return [
            'academics.view_student', 'academics.view_teacher', 'academics.view_class',
            'assessment.view_result', 'assessment.view_reportcard', 'assessment.view_mark',
            'attendance.view_dailyattendance', 'attendance.view_attendancesummary',
            'communication.add_message', 'communication.view_message',
        ]

    def _get_teacher_permissions(self):
        """Teacher gets classroom management permissions"""
        return [
            # Academic
            'academics.view_department', 'academics.view_subject', 'academics.view_class',
            'academics.view_student', 'academics.view_enrollment', 'academics.view_timetable',
            'academics.add_classmaterial', 'academics.change_classmaterial', 'academics.delete_classmaterial', 'academics.view_classmaterial',

            # Assessment
            'assessment.add_assignment', 'assessment.change_assignment', 'assessment.delete_assignment', 'assessment.view_assignment',
            'assessment.add_mark', 'assessment.change_mark', 'assessment.view_mark',
            'assessment.view_exam', 'assessment.view_result',

            # Attendance
            'attendance.add_dailyattendance', 'attendance.change_dailyattendance', 'attendance.view_dailyattendance',
            'attendance.view_attendancesession', 'attendance.view_periodattendance',

            # Communication
            'communication.add_message', 'communication.view_message',
        ]

    def _get_accountant_permissions(self):
        """Accountant gets finance permissions"""
        return [
            'finance.add_invoice', 'finance.change_invoice', 'finance.delete_invoice', 'finance.view_invoice',
            'finance.add_payment', 'finance.change_payment', 'finance.delete_payment', 'finance.view_payment',
            'finance.add_feestructure', 'finance.change_feestructure', 'finance.delete_feestructure', 'finance.view_feestructure',
            'finance.add_expense', 'finance.change_expense', 'finance.delete_expense', 'finance.view_expense',
            'finance.add_financialreport', 'finance.change_financialreport', 'finance.delete_financialreport', 'finance.view_financialreport',
        ]

    def _get_librarian_permissions(self):
        """Librarian gets library permissions"""
        return [
            'library.add_library', 'library.change_library', 'library.delete_library', 'library.view_library',
            'library.add_author', 'library.change_author', 'library.delete_author', 'library.view_author',
            'library.add_publisher', 'library.change_publisher', 'library.delete_publisher', 'library.view_publisher',
            'library.add_bookcategory', 'library.change_bookcategory', 'library.delete_bookcategory', 'library.view_bookcategory',
            'library.add_book', 'library.change_book', 'library.delete_book', 'library.view_book',
            'library.add_bookcopy', 'library.change_bookcopy', 'library.delete_bookcopy', 'library.view_bookcopy',
            'library.add_librarymember', 'library.change_librarymember', 'library.delete_librarymember', 'library.view_librarymember',
            'library.add_borrowrecord', 'library.change_borrowrecord', 'library.delete_borrowrecord', 'library.view_borrowrecord',
            'library.add_reservation', 'library.change_reservation', 'library.delete_reservation', 'library.view_reservation',
            'library.add_finepayment', 'library.change_finepayment', 'library.delete_finepayment', 'library.view_finepayment',
        ]

    def _get_driver_permissions(self):
        """Driver gets basic transport permissions"""
        return [
            'transport.view_vehicle', 'transport.view_route', 'transport.view_routeschedule',
            'transport.add_incidentreport', 'transport.change_incidentreport', 'transport.view_incidentreport',
        ]

    def _get_support_permissions(self):
        """Support staff gets basic permissions"""
        return [
            'users.view_user',
            'communication.add_message', 'communication.view_message',
            'support.add_helpcenter', 'support.change_helpcenter', 'support.view_helpcenter',
            'support.add_faq', 'support.change_faq', 'support.view_faq',
            'support.add_resource', 'support.change_resource', 'support.view_resource',
        ]

    def _get_transport_manager_permissions(self):
        """Transport manager gets full transport permissions"""
        return [
            'transport.add_vehicle', 'transport.change_vehicle', 'transport.delete_vehicle', 'transport.view_vehicle',
            'transport.add_driver', 'transport.change_driver', 'transport.delete_driver', 'transport.view_driver',
            'transport.add_attendant', 'transport.change_attendant', 'transport.delete_attendant', 'transport.view_attendant',
            'transport.add_route', 'transport.change_route', 'transport.delete_route', 'transport.view_route',
            'transport.add_routestop', 'transport.change_routestop', 'transport.delete_routestop', 'transport.view_routestop',
            'transport.add_routeschedule', 'transport.change_routeschedule', 'transport.delete_routeschedule', 'transport.view_routeschedule',
            'transport.add_transportallocation', 'transport.change_transportallocation', 'transport.delete_transportallocation', 'transport.view_transportallocation',
            'transport.add_maintenancerecord', 'transport.change_maintenancerecord', 'transport.delete_maintenancerecord', 'transport.view_maintenancerecord',
            'transport.add_fuelrecord', 'transport.change_fuelrecord', 'transport.delete_fuelrecord', 'transport.view_fuelrecord',
            'transport.add_incidentreport', 'transport.change_incidentreport', 'transport.delete_incidentreport', 'transport.view_incidentreport',
        ]

    def _get_hostel_warden_permissions(self):
        """Hostel warden gets hostel permissions"""
        return [
            'hostels.add_hostel', 'hostels.change_hostel', 'hostels.delete_hostel', 'hostels.view_hostel',
            'hostels.add_room', 'hostels.change_room', 'hostels.delete_room', 'hostels.view_room',
            'hostels.add_bed', 'hostels.change_bed', 'hostels.delete_bed', 'hostels.view_bed',
            'hostels.add_allocation', 'hostels.change_allocation', 'hostels.delete_allocation', 'hostels.view_allocation',
            'hostels.add_fee', 'hostels.change_fee', 'hostels.delete_fee', 'hostels.view_fee',
            'hostels.add_visitor', 'hostels.change_visitor', 'hostels.delete_visitor', 'hostels.view_visitor',
            'hostels.add_maintenance', 'hostels.change_maintenance', 'hostels.delete_maintenance', 'hostels.view_maintenance',
            'hostels.add_inventory', 'hostels.change_inventory', 'hostels.delete_inventory', 'hostels.view_inventory',
        ]
