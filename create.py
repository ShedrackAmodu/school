#!/usr/bin/env python
"""
Consolidated System Creation Script

This script consolidates all school management system creation and setup functions
into a single executable file. It combines role creation, permission assignment,
multi-tenancy setup, analytics setup, and other initialization tasks.

Usage:
    python create.py

Requirements:
    - Django environment must be properly configured
    - Database should be set up and migrations run
    - All required apps must be installed

Author: Nexus Intelligence School Management System
"""

import os
import sys
import django
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.development')
django.setup()

# Import models and utilities
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from apps.users.models import Role
from apps.core.models import Institution, InstitutionUser
from apps.analytics.models import KPI
from apps.academics.models import AcademicSession
from apps.assessment.models import ExamType

User = get_user_model()


class SystemCreator:
    """Handles all system creation and setup tasks."""

    def __init__(self):
        self.created = 0
        self.updated = 0

    def log_success(self, message):
        """Log a success message."""
        print(f"✓ {message}")

    def log_info(self, message):
        """Log an info message."""
        print(f"ℹ {message}")

    def log_warning(self, message):
        """Log a warning message."""
        print(f"⚠ {message}")

    def log_error(self, message):
        """Log an error message."""
        print(f"✗ {message}")
        self.updated += 1  # Track as updated for error counting

    def setup_staff_roles(self):
        """Create default staff roles."""
        self.log_info("Setting up staff roles...")

        # Define staff roles with their display names and descriptions
        staff_roles_data = [
            {
                'role_type': Role.RoleType.SUPER_ADMIN,
                'name': 'Super Administrator',
                'description': 'Full system access and control',
                'hierarchy_level': 100,
            },
            {
                'role_type': Role.RoleType.ADMIN,
                'name': 'Administrator',
                'description': 'Administrative access to school management',
                'hierarchy_level': 90,
            },
            {
                'role_type': Role.RoleType.PRINCIPAL,
                'name': 'Principal',
                'description': 'School principal with oversight of all operations',
                'hierarchy_level': 85,
            },
            {
                'role_type': Role.RoleType.DEPARTMENT_HEAD,
                'name': 'Department Head',
                'description': 'Head of an academic department',
                'hierarchy_level': 70,
            },
            {
                'role_type': Role.RoleType.COUNSELOR,
                'name': 'School Counselor',
                'description': 'Student counseling and guidance',
                'hierarchy_level': 60,
            },
            {
                'role_type': Role.RoleType.TEACHER,
                'name': 'Teacher',
                'description': 'Classroom teacher',
                'hierarchy_level': 50,
            },
            {
                'role_type': Role.RoleType.ACCOUNTANT,
                'name': 'Accountant',
                'description': 'Financial management and accounting',
                'hierarchy_level': 45,
            },
            {
                'role_type': Role.RoleType.LIBRARIAN,
                'name': 'Librarian',
                'description': 'Library management and services',
                'hierarchy_level': 40,
            },
            {
                'role_type': Role.RoleType.DRIVER,
                'name': 'Driver',
                'description': 'School transport driver',
                'hierarchy_level': 30,
            },
            {
                'role_type': Role.RoleType.SUPPORT,
                'name': 'Support Staff',
                'description': 'General support staff',
                'hierarchy_level': 25,
            },
            {
                'role_type': Role.RoleType.TRANSPORT_MANAGER,
                'name': 'Transport Manager',
                'description': 'Management of school transportation',
                'hierarchy_level': 55,
            },
            {
                'role_type': Role.RoleType.HOSTEL_WARDEN,
                'name': 'Hostel Warden',
                'description': 'Management of student hostel facilities',
                'hierarchy_level': 50,
            },
        ]

        for role_data in staff_roles_data:
            role, created = Role.objects.get_or_create(
                role_type=role_data['role_type'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'hierarchy_level': role_data['hierarchy_level'],
                    'is_system_role': True,
                    'status': 'active',
                }
            )

            if created:
                self.created += 1
                self.log_success(f"Created role: {role.name}")
            else:
                # Update existing role if needed
                updated = False
                if role.name != role_data['name']:
                    role.name = role_data['name']
                    updated = True
                if role.description != role_data['description']:
                    role.description = role_data['description']
                    updated = True
                if role.hierarchy_level != role_data['hierarchy_level']:
                    role.hierarchy_level = role_data['hierarchy_level']
                    updated = True
                if role.status != 'active':
                    role.status = 'active'
                    updated = True

                if updated:
                    role.save()
                    self.updated += 1
                    self.log_warning(f'Updated role: {role.name}')

        self.log_success(f"Staff roles setup complete. Created: {self.created}, Updated: {self.updated}")

    def assign_role_permissions(self):
        """Assign appropriate permissions to all staff roles."""
        self.log_info("Assigning role permissions...")

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
                    self.log_warning(f'Role {role_type} not found, skipping')
                    continue

                self.log_info(f'Assigning permissions to {role.name}...')

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
                        self.log_warning(f'Permission not found: {perm_codename}')
                    except ValueError:
                        self.log_error(f'Invalid permission format: {perm_codename}')

                self.log_success(f'Assigned {role_assigned} permissions to {role.name}')

            except Exception as e:
                self.log_error(f'Error assigning permissions to {role_type}: {e}')

        self.log_success(f'Total permissions assigned: {total_assigned}')

    def setup_multitenancy(self):
        """Set up multi-tenancy infrastructure and automatically map users to institutions."""
        self.log_info("Setting up multi-tenancy infrastructure...")

        institution_name = "Default School"
        institution_code = "DEFAULT"
        institution_domain = getattr(settings, 'SITE_DOMAIN', 'localhost')

        # Create default institution if it doesn't exist
        institution, created = Institution.objects.get_or_create(
            code=institution_code,
            defaults={
                'name': institution_name,
                'short_name': institution_name[:50],
                'website': f'https://{institution_domain}',
                'description': f'Default institution: {institution_name}',
                'institution_type': Institution.InstitutionType.HIGH_SCHOOL,
                'ownership_type': Institution.OwnershipType.PRIVATE,
                'max_students': 1000,
                'max_staff': 100,
                'timezone': 'UTC',
                'is_active': True,
            }
        )

        if created:
            self.created += 1
            self.log_success(f'Created default institution: {institution.name} ({institution.code})')
        else:
            self.updated += 1
            self.log_warning(f'Institution already exists: {institution.name} ({institution.code})')

        # Automatically map users to institutions based on their roles
        users_assigned = 0
        users_updated = 0

        # Define staff role types that require institution mapping
        staff_role_types = [
            'super_admin', 'admin', 'principal', 'department_head', 'counselor',
            'teacher', 'accountant', 'librarian', 'driver', 'support',
            'transport_manager', 'hostel_warden'
        ]

        # Find users with staff roles but no institution mapping
        from django.db.models import Q

        unmapped_staff = User.objects.filter(
            Q(user_roles__role__role_type__in=staff_role_types, user_roles__status='active') &
            ~Q(institution_memberships__isnull=False)
        ).distinct()

        for user in unmapped_staff:
            try:
                # Get the user's primary role for employee ID generation
                primary_role = user.user_roles.filter(
                    is_primary=True,
                    status='active'
                ).first()

                if primary_role:
                    role_type = primary_role.role.role_type
                else:
                    # Use the first active staff role
                    staff_role = user.user_roles.filter(
                        role__role_type__in=staff_role_types,
                        status='active'
                    ).first()
                    role_type = staff_role.role.role_type if staff_role else 'staff'

                # Generate employee ID
                employee_id = f'{role_type}_{institution.code}_{user.id}'

                # Create institution-user relationship
                institution_user, membership_created = InstitutionUser.objects.get_or_create(
                    user=user,
                    institution=institution,
                    defaults={
                        'is_primary': True,
                        'employee_id': employee_id,
                    }
                )

                if membership_created:
                    users_assigned += 1
                    self.log_success(f'Mapped {user.email} to {institution.code} with ID {employee_id}')
                else:
                    users_updated += 1
                    self.log_info(f'Updated mapping for {user.email}')

                # Update user profile with employee ID
                if hasattr(user, 'profile') and user.profile and not user.profile.employee_id:
                    user.profile.employee_id = employee_id
                    user.profile.save()

            except Exception as e:
                self.log_error(f'Error mapping user {user.email}: {str(e)}')

        # Special handling for superusers (always map to all institutions)
        superusers = User.objects.filter(is_superuser=True)
        superuser_mappings = 0

        for superuser in superusers:
            # Create default mapping for superuser
            if not InstitutionUser.objects.filter(user=superuser, institution=institution).exists():
                InstitutionUser.objects.get_or_create(
                    user=superuser,
                    institution=institution,
                    defaults={
                        'is_primary': True,
                        'employee_id': f'superuser_{institution.code}_{superuser.id}',
                    }
                )
                superuser_mappings += 1
                self.log_success(f'Mapped superuser {superuser.email} to {institution.code}')

        # Map non-staff users with roles to default institution (parents, students)
        other_users = User.objects.filter(
            is_staff=False,
            is_superuser=False,
            user_roles__isnull=False
        ).exclude(institution_memberships__isnull=False).distinct()

        for user in other_users:
            # For students and parents, assign to default institution
            InstitutionUser.objects.get_or_create(
                user=user,
                institution=institution,
                defaults={
                    'is_primary': True,
                }
            )
            users_assigned += 1
            self.log_info(f'Mapped {user.email} (non-staff) to {institution.code}')

        self.log_success(f'Multi-tenancy setup complete!')
        self.log_info(f'  - Staff/users mapped: {users_assigned}')
        self.log_info(f'  - Existing mappings updated: {users_updated}')

        # Display comprehensive summary
        total_users = User.objects.count()
        total_staff = User.objects.filter(
            user_roles__role__role_type__in=staff_role_types,
            user_roles__status='active'
        ).distinct().count()

        institution_staff = InstitutionUser.objects.filter(
            institution=institution,
            user__user_roles__role__role_type__in=staff_role_types,
            user__user_roles__status='active'
        ).distinct().count()

        institution_users = InstitutionUser.objects.filter(institution=institution).distinct().count()

        self.log_info(f'Institution: {institution.name} ({institution.code})')
        self.log_info(f'  - Total users in system: {total_users}')
        self.log_info(f'  - Total staff users: {total_staff}')
        self.log_info(f'  - Staff mapped to {institution.code}: {institution_staff}')
        self.log_info(f'  - Total users mapped to {institution.code}: {institution_users}')
        self.log_info(f'  - Users with access to {institution.code}: {institution_users}')

        # Warn about unmapped staff (shouldn't happen after our logic)
        unmapped_after_setup = total_staff - institution_staff
        if unmapped_after_setup > 0:
            self.log_warning(f'Warning: {unmapped_after_setup} staff users still unmapped after setup!')

    def setup_system_kpis(self):
        """Create system performance KPIs for monitoring."""
        self.log_info("Setting up system KPIs...")

        # Get or create current academic session
        current_session, created = AcademicSession.objects.get_or_create(
            name="2025-2026",
            defaults={
                'start_date': '2025-01-01',
                'end_date': '2026-12-31',
                'status': 'active'
            }
        )

        if created:
            self.log_success("Created default academic session")

        # System Performance KPIs
        system_kpis = [
            {
                'name': 'CPU Usage',
                'code': 'system_cpu_usage',
                'category': 'system',
                'description': 'Percentage of CPU utilization across the system',
                'value_type': 'percentage',
                'target_value': 70.0,
                'max_value': 100.0,
                'refresh_frequency': 'realtime',
                'is_trending': True,
                'display_format': '{value}%',
                'data_source': 'system.monitoring.cpu',
            },
            {
                'name': 'Memory Usage',
                'code': 'system_memory_usage',
                'category': 'system',
                'description': 'Percentage of RAM memory utilization',
                'value_type': 'percentage',
                'target_value': 80.0,
                'max_value': 100.0,
                'refresh_frequency': 'realtime',
                'is_trending': True,
                'display_format': '{value}%',
                'data_source': 'system.monitoring.memory',
            },
            {
                'name': 'Disk Usage',
                'code': 'system_disk_usage',
                'category': 'system',
                'description': 'Percentage of disk storage utilization',
                'value_type': 'percentage',
                'target_value': 85.0,
                'max_value': 100.0,
                'refresh_frequency': 'hourly',
                'is_trending': True,
                'display_format': '{value}%',
                'data_source': 'system.monitoring.disk',
            },
            {
                'name': 'Database Connections',
                'code': 'db_active_connections',
                'category': 'system',
                'description': 'Number of active database connections',
                'value_type': 'number',
                'target_value': 50.0,
                'max_value': 100.0,
                'refresh_frequency': 'realtime',
                'is_trending': True,
                'display_format': '{value}',
                'data_source': 'database.monitoring.connections',
            },
            {
                'name': 'Average Response Time',
                'code': 'app_response_time',
                'category': 'system',
                'description': 'Average application response time in milliseconds',
                'value_type': 'duration',
                'target_value': 500.0,  # 500ms target
                'max_value': 2000.0,   # 2s max acceptable
                'refresh_frequency': 'realtime',
                'is_trending': True,
                'display_format': '{value}ms',
                'data_source': 'application.monitoring.response_time',
            },
            {
                'name': 'Error Rate',
                'code': 'app_error_rate',
                'category': 'system',
                'description': 'Percentage of requests resulting in errors',
                'value_type': 'percentage',
                'target_value': 1.0,   # 1% target
                'max_value': 5.0,     # 5% max acceptable
                'refresh_frequency': 'hourly',
                'is_trending': True,
                'display_format': '{value}%',
                'data_source': 'application.monitoring.errors',
            },
            {
                'name': 'Active User Sessions',
                'code': 'user_active_sessions',
                'category': 'system',
                'description': 'Number of currently active user sessions',
                'value_type': 'number',
                'target_value': 1000.0,
                'refresh_frequency': 'realtime',
                'is_trending': True,
                'display_format': '{value}',
                'data_source': 'users.monitoring.sessions',
            },
            {
                'name': 'Database Query Performance',
                'code': 'db_query_performance',
                'category': 'system',
                'description': 'Average database query execution time in milliseconds',
                'value_type': 'duration',
                'target_value': 100.0,  # 100ms target
                'max_value': 1000.0,   # 1s max acceptable
                'refresh_frequency': 'hourly',
                'is_trending': True,
                'display_format': '{value}ms',
                'data_source': 'database.monitoring.query_time',
            },
            {
                'name': 'System Uptime',
                'code': 'system_uptime',
                'category': 'system',
                'description': 'System uptime percentage over the last 30 days',
                'value_type': 'percentage',
                'target_value': 99.9,
                'refresh_frequency': 'daily',
                'is_trending': True,
                'display_format': '{value}%',
                'data_source': 'system.monitoring.uptime',
            },
            {
                'name': 'Backup Status',
                'code': 'backup_status',
                'category': 'system',
                'description': 'Days since last successful backup',
                'value_type': 'number',
                'target_value': 1.0,   # Daily backup target
                'max_value': 7.0,     # Max 7 days acceptable
                'refresh_frequency': 'daily',
                'is_trending': False,
                'display_format': '{value} days',
                'data_source': 'system.monitoring.backup',
            },
        ]

        kpi_created = 0
        kpi_updated = 0

        for kpi_data in system_kpis:
            kpi, created = KPI.objects.get_or_create(
                code=kpi_data['code'],
                defaults=kpi_data
            )

            if created:
                kpi_created += 1
                self.created += 1
                self.log_success(f'Created KPI: {kpi.name}')
            else:
                # Update existing KPI with new values
                for key, value in kpi_data.items():
                    setattr(kpi, key, value)
                kpi.save()
                kpi_updated += 1
                self.updated += 1
                self.log_warning(f'Updated KPI: {kpi.name}')

        self.log_success(f'System KPIs setup complete. Created: {kpi_created}, Updated: {kpi_updated}')

    def populate_exam_types(self):
        """Create default exam types for assessment system."""
        self.log_info("Setting up exam types...")

        # Define default exam types
        exam_types_data = [
            {
                'name': 'Mid-Term Examination',
                'code': 'MID_TERM',
                'description': 'Mid-term assessment covering half the curriculum',
                'weightage': 30.0,
                'is_final': False,
                'order': 1,
            },
            {
                'name': 'Final Examination',
                'code': 'FINAL',
                'description': 'Final examination covering complete curriculum',
                'weightage': 50.0,
                'is_final': True,
                'order': 2,
            },
            {
                'name': 'Practical Examination',
                'code': 'PRACTICAL',
                'description': 'Practical assessment for science and technical subjects',
                'weightage': 20.0,
                'is_final': False,
                'order': 3,
            },
            {
                'name': 'Continuous Assessment',
                'code': 'CA',
                'description': 'Continuous assessment throughout the term',
                'weightage': 25.0,
                'is_final': False,
                'order': 4,
            },
            {
                'name': 'Project Work',
                'code': 'PROJECT',
                'description': 'Project-based assessment',
                'weightage': 30.0,
                'is_final': False,
                'order': 5,
            },
            {
                'name': 'Viva Voce',
                'code': 'VIVA_VOCE',
                'description': 'Oral examination',
                'weightage': 15.0,
                'is_final': False,
                'order': 6,
            },
        ]

        exam_created = 0
        exam_updated = 0

        for exam_data in exam_types_data:
            exam, created = ExamType.objects.get_or_create(
                code=exam_data['code'],
                defaults=exam_data
            )

            if created:
                exam_created += 1
                self.created += 1
                self.log_success(f'Created exam type: {exam.name}')
            else:
                # Update existing exam type
                updated = False
                for key, value in exam_data.items():
                    if getattr(exam, key) != value:
                        setattr(exam, key, value)
                        updated = True

                if updated:
                    exam.save()
                    exam_updated += 1
                    self.updated += 1
                    self.log_warning(f'Updated exam type: {exam.name}')

        self.log_success(f'Exam types setup complete. Created: {exam_created}, Updated: {exam_updated}')

    def run_all_setup(self):
        """Run all setup functions in proper order."""
        print("=" * 60)
        print(" SCHOOL MANAGEMENT SYSTEM - CONSOLIDATED SETUP ")
        print("=" * 60)
        print()

        try:
            # Run setup functions in logical order
            self.setup_staff_roles()
            self.assign_role_permissions()
            self.setup_multitenancy()
            self.setup_system_kpis()
            self.populate_exam_types()

            print()
            print("=" * 60)
            self.log_success("SYSTEM SETUP COMPLETE!")
            self.log_info(f"Total records created: {self.created}")
            if self.updated > 0:
                self.log_info(f"Total records updated: {self.updated}")
            print("=" * 60)

        except Exception as e:
            print()
            self.log_error(f"Setup failed with error: {e}")
            raise

    # Permission helper methods (extracted from assign_role_permissions.py)
    def _get_super_admin_permissions(self):
        """Super admin gets all permissions"""
        return [
            # Users
            'users.add_user', 'users.change_user', 'users.delete_user', 'users.view_user',
            'users.add_role', 'users.change_role', 'users.delete_role', 'users.view_role',
            'users.approve_applications',

            # Core
            'core.add_institution', 'core.change_institution', 'core.delete_institution', 'core.view_institution',
            'core.add_institutionuser', 'core.change_institutionuser', 'core.delete_institutionuser', 'core.view_institutionuser',

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
            'assessment.add_assessment', 'assessment.change_assessment', 'assessment.delete_assessment', 'assessment.view_assessment',
            'assessment.add_exam', 'assessment.change_exam', 'assessment.delete_exam', 'assessment.view_exam',
            'assessment.add_assignment', 'assessment.change_assignment', 'assessment.delete_assignment', 'assessment.view_assignment',
            'assessment.add_result', 'assessment.change_result', 'assessment.delete_result', 'assessment.view_result',
            'assessment.add_examtype', 'assessment.change_examtype', 'assessment.delete_examtype', 'assessment.view_examtype',
            'assessment.add_reportcard', 'assessment.change_reportcard', 'assessment.delete_reportcard', 'assessment.view_reportcard',
            'assessment.add_mark', 'assessment.change_mark', 'assessment.delete_mark', 'assessment.view_mark',

            # Attendance
            'attendance.add_dailyattendance', 'attendance.change_dailyattendance', 'attendance.delete_dailyattendance', 'attendance.view_dailyattendance',
            'attendance.add_attendancesession', 'attendance.change_attendancesession', 'attendance.delete_attendancesession', 'attendance.view_attendancesession',
            'attendance.add_periodattendance', 'attendance.change_periodattendance', 'attendance.delete_periodattendance', 'attendance.view_periodattendance',
            'attendance.add_leave', 'attendance.change_leave', 'attendance.delete_leave', 'attendance.view_leave',
            'attendance.add_attendancesummary', 'attendance.change_attendancesummary', 'attendance.delete_attendancesummary', 'attendance.view_attendancesummary',

            # Analytics
            'analytics.add_analyticsreport', 'analytics.change_analyticsreport', 'analytics.delete_analyticsreport', 'analytics.view_analyticsreport',
            'analytics.add_kpi', 'analytics.change_kpi', 'analytics.delete_kpi', 'analytics.view_kpi',
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


def main():
    """Main execution function."""
    try:
        creator = SystemCreator()
        creator.run_all_setup()
        return 0
    except Exception as e:
        print(f"\n✗ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
