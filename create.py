#!/usr/bin/env python
"""
Consolidated System Creation Script

This script consolidates all school management system creation and setup functions
into a single executable file. It combines role creation, permission assignment,
institution mapping/setup, analytics setup, and other initialization tasks for a single-tenant deployment.

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
from django.core.management import call_command
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

        roles_created = 0
        roles_updated = 0

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
                roles_created += 1
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
                    roles_updated += 1
                    self.updated += 1
                    self.log_warning(f'Updated role: {role.name}')

        self.log_success(f"Staff roles setup complete. Created: {roles_created}, Updated: {roles_updated}")

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

                if role_assigned > 0:
                    self.log_success(f'Assigned {role_assigned} permissions to {role.name}')

            except Exception as e:
                self.log_error(f'Error assigning permissions to {role_type}: {e}')

        self.log_success(f'Total permissions assigned: {total_assigned}')

    

        # Institution mapping and default-institution setup removed for single-tenant deployments.
        # If you need to assign users to institutions, do this manually via the admin interface.

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
                'target_value': 500.0,
                'max_value': 2000.0,
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
                'target_value': 1.0,
                'max_value': 5.0,
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
                'target_value': 100.0,
                'max_value': 1000.0,
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
                'target_value': 1.0,
                'max_value': 7.0,
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

    def setup_support_data(self):
        """Initialize support system data including FAQs and legal documents."""
        self.log_info("Setting up support system data...")

        try:
            # Import support models
            from apps.support.models import FAQ, Category, LegalDocument

            # Setup FAQ categories and data
            self._create_faq_categories()
            self._populate_faqs()
            self._populate_legal_documents()

            self.log_success("Support system data setup complete.")
        except ImportError:
            self.log_warning("Support app not installed. Skipping support data setup.")
        except Exception as e:
            self.log_error(f"Error setting up support data: {e}")

    def _create_faq_categories(self):
        """Create FAQ categories."""
        try:
            from apps.support.models import Category

            categories_data = [
                {'name': 'Account & Login', 'slug': 'account-login', 'description': 'Questions about user accounts, login, and authentication'},
                {'name': 'Academic Records', 'slug': 'academic-records', 'description': 'Questions about grades, courses, and academic information'},
                {'name': 'Fees & Payments', 'slug': 'fees-payments', 'description': 'Questions about school fees, payments, and financial matters'},
                {'name': 'System Usage', 'slug': 'system-usage', 'description': 'Questions about using the school management system'},
                {'name': 'Support & Communication', 'slug': 'support-communication', 'description': 'Questions about getting help and contacting school staff'},
                {'name': 'Library Services', 'slug': 'library-services', 'description': 'Questions about library resources and borrowing'},
                {'name': 'Health & Medical', 'slug': 'health-medical', 'description': 'Questions about school health services and medical care'},
                {'name': 'Transportation', 'slug': 'transportation', 'description': 'Questions about school transportation services'},
                {'name': 'Hostel & Accommodation', 'slug': 'hostel-accommodation', 'description': 'Questions about hostel facilities and accommodation'},
                {'name': 'Activities & Clubs', 'slug': 'activities-clubs', 'description': 'Questions about extracurricular activities and clubs'},
            ]

            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    slug=cat_data['slug'],
                    defaults={
                        'name': cat_data['name'],
                        'description': cat_data['description'],
                        'is_active': True
                    }
                )
                if created:
                    self.created += 1
                    self.log_success(f'Created FAQ category: {cat_data["name"]}')
        except Exception as e:
            self.log_error(f"Error creating FAQ categories: {e}")

    def _populate_faqs(self):
        """Create comprehensive FAQs."""
        try:
            from apps.support.models import FAQ, Category

            faqs_data = [
                # Account & Login
                {
                    'question': 'How do I reset my password?',
                    'answer': (
                        "To reset your password:\n\n"
                        "1. Go to the login page and click \"Forgot Password?\"\n"
                        "2. Enter your email address\n"
                        "3. Check your email for a password reset link\n"
                        "4. Follow the link to create a new password\n\n"
                        "If you don't receive the email, please contact support or check your spam folder."
                    ),
                    'category_slug': 'account-login',
                    'order': 1
                },
                {
                    'question': 'How do I change my profile information?',
                    'answer': (
                        "To update your profile:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to your profile/dashboard\n"
                        "3. Click on \"Edit Profile\" or \"Account Settings\"\n"
                        "4. Update your information as needed\n"
                        "5. Save your changes\n\n"
                        "For students, some information may be managed by school administrators."
                    ),
                    'category_slug': 'account-login',
                    'order': 2
                },
                {
                    'question': 'Why can\'t I log in to my account?',
                    'answer': (
                        "Common login issues and solutions:\n\n"
                        "Wrong credentials: Double-check your username/email and password (note: passwords are case-sensitive)\n\n"
                        "Account locked: After several failed attempts, accounts may be temporarily locked. Wait 15 minutes or contact support.\n\n"
                        "Browser issues: Clear your browser cache/cookies or try a different browser.\n\n"
                        "System maintenance: The system may be down for maintenance. Check the school website for announcements.\n\n"
                        "If none of these work, please contact support with your username/email address."
                    ),
                    'category_slug': 'account-login',
                    'order': 3
                },
                {
                    'question': 'How do I enable two-factor authentication?',
                    'answer': (
                        "To enhance your account security:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Account Settings\" > \"Security\"\n"
                        "3. Click \"Enable Two-Factor Authentication\"\n"
                        "4. Follow the setup process using your authenticator app\n"
                        "5. Save your backup codes in a safe place\n\n"
                        "2FA is recommended for all users to protect your account."
                    ),
                    'category_slug': 'account-login',
                    'order': 4
                },
                {
                    'question': 'How do I switch between different user roles?',
                    'answer': (
                        "If you have multiple roles (e.g., student and parent):\n\n"
                        "1. Log in with your primary account\n"
                        "2. Click on your profile picture/initials\n"
                        "3. Select \"Switch Role\" from the dropdown\n"
                        "4. Choose the role you want to use\n"
                        "5. The interface will update for that role\n\n"
                        "Some features may only be available in certain roles."
                    ),
                    'category_slug': 'account-login',
                    'order': 5
                },
                # Academic Information
                {
                    'question': 'How can I view my grades and academic records?',
                    'answer': (
                        "To view your academic information:\n\n"
                        "1. Log in to your student portal\n"
                        "2. Navigate to \"Academics\" or \"Grades\" section\n"
                        "3. Select the academic year/term you want to view\n"
                        "4. Click on individual subjects for detailed grade breakdowns\n\n"
                        "Parents can view their children's academic records through the parent portal by selecting their student first."
                    ),
                    'category_slug': 'academic-records',
                    'order': 1
                },
                {
                    'question': 'How do I register for classes?',
                    'answer': (
                        "Course registration process:\n\n"
                        "1. Log in during the registration period announced by your school\n"
                        "2. Go to \"Academics\" > \"Course Registration\"\n"
                        "3. Browse available courses by subject/department\n"
                        "4. Select your preferred courses (respecting prerequisites and schedule conflicts)\n"
                        "5. Submit your registration for approval\n\n"
                        "Check with your academic advisor for course recommendations."
                    ),
                    'category_slug': 'academic-records',
                    'order': 2
                },
                {
                    'question': 'What is my class schedule and how can I view it?',
                    'answer': (
                        "To view your class schedule:\n\n"
                        "1. Log in to your student portal\n"
                        "2. Go to \"Schedule\" or \"Timetable\"\n"
                        "3. Select the current term/academic year\n"
                        "4. Your schedule will show class times, locations, and instructors\n\n"
                        "You can also download or print your schedule for reference. Schedule changes will be reflected here automatically."
                    ),
                    'category_slug': 'academic-records',
                    'order': 3
                },
                {
                    'question': 'How do I check my attendance records?',
                    'answer': (
                        "To view attendance information:\n\n"
                        "1. Log in to your student portal\n"
                        "2. Navigate to \"Attendance\" section\n"
                        "3. Select the period you want to review (daily, weekly, monthly)\n"
                        "4. View detailed attendance records by subject\n\n"
                        "Parents can monitor their children's attendance through the parent portal. Contact your teachers or academic office if you notice any discrepancies."
                    ),
                    'category_slug': 'academic-records',
                    'order': 4
                },
                {
                    'question': 'How do I request an academic transcript?',
                    'answer': (
                        "To request a transcript:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Documents\" > \"Academic Records\"\n"
                        "3. Select \"Request Transcript\"\n"
                        "4. Choose the format and delivery method\n"
                        "5. Submit your request with any required fees\n\n"
                        "Processing time is typically 3-5 business days. Official transcripts are sent directly to institutions or your mailing address."
                    ),
                    'category_slug': 'academic-records',
                    'order': 5
                },
                # Fees & Payments
                {
                    'question': 'How can I view my fee statement and payment history?',
                    'answer': (
                        "To access your financial information:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Finance\" or \"Fees & Payments\"\n"
                        "3. Select \"Fee Statement\" to see outstanding balances\n"
                        "4. Choose \"Payment History\" to view past transactions\n\n"
                        "All fees, payments, discounts, and outstanding balances are displayed here."
                    ),
                    'category_slug': 'fees-payments',
                    'order': 1
                },
                {
                    'question': 'What payment methods are accepted?',
                    'answer': (
                        "We accept the following payment methods:\n\n"
                        "Online Payments:\n"
                        "- Credit/Debit cards (Visa, MasterCard, American Express)\n"
                        "- Bank transfers\n"
                        "- Mobile money (M-Pesa, Airtel Money, etc.)\n"
                        "- Online banking\n\n"
                        "Offline Payments:\n"
                        "- Cash payments at school bursar's office\n"
                        "- Bank deposits (provide reference number when submitting proof)\n"
                        "- Cheques\n\n"
                        "All payments should include your student ID or reference number."
                    ),
                    'category_slug': 'fees-payments',
                    'order': 2
                },
                {
                    'question': 'How do I pay school fees online?',
                    'answer': (
                        "Online payment process:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Finance\" > \"Make Payment\"\n"
                        "3. Select the fee type and amount\n"
                        "4. Choose your payment method\n"
                        "5. Review and confirm payment details\n"
                        "6. Complete the transaction\n\n"
                        "You'll receive a payment confirmation and receipt via email. Processing time is usually instant for cards and 1-2 business days for bank transfers."
                    ),
                    'category_slug': 'fees-payments',
                    'order': 3
                },
                {
                    'question': 'What if I have a payment dispute or need a refund?',
                    'answer': (
                        "For payment issues:\n\n"
                        "1. Contact the bursar's office with your payment reference\n"
                        "2. Provide supporting documentation\n"
                        "3. Submit a formal request through the system or email\n\n"
                        "Refunds are processed within 14-21 business days after approval. All refund requests are reviewed by the finance department."
                    ),
                    'category_slug': 'fees-payments',
                    'order': 4
                },
                {
                    'question': 'How do I apply for a fee waiver or scholarship?',
                    'answer': (
                        "Fee waiver/scholarship process:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Finance\" > \"Financial Aid\"\n"
                        "3. Select \"Apply for Waiver/Scholarship\"\n"
                        "4. Fill out the application form with required details\n"
                        "5. Upload supporting documents\n"
                        "6. Submit your application\n\n"
                        "Applications are reviewed by the financial aid office. You'll be notified of the decision via email or through the system."
                    ),
                    'category_slug': 'fees-payments',
                    'order': 5
                },
                # System Usage
                {
                    'question': 'How do I update my contact information?',
                    'answer': (
                        "To update your contact details:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Profile\" or \"Account Settings\"\n"
                        "3. Select \"Contact Information\"\n"
                        "4. Update phone number, email, or address as needed\n"
                        "5. Save changes\n\n"
                        "Important contact updates (like emergency contacts) may require verification. Always keep your information current for important school communications."
                    ),
                    'category_slug': 'system-usage',
                    'order': 1
                },
                {
                    'question': 'How do I download documents like transcripts or certificates?',
                    'answer': (
                        "To download official documents:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Documents\" or \"Downloads\" section\n"
                        "3. Select the document type you need (transcript, certificate, etc.)\n"
                        "4. Choose the academic year/period\n"
                        "5. Click \"Generate\" or \"Download\"\n\n"
                        "Some documents may require approval before they become available for download."
                    ),
                    'category_slug': 'system-usage',
                    'order': 2
                },
                {
                    'question': 'How do I report a technical issue with the system?',
                    'answer': (
                        "To report a technical problem:\n\n"
                        "1. Contact support through the \"Support\" section\n"
                        "2. Select \"Technical Issue\" as the category\n"
                        "3. Provide detailed description including:\n"
                        "   - What you were trying to do\n"
                        "   - Error messages received\n"
                        "   - Browser and device information\n"
                        "   - Steps to reproduce the issue\n\n"
                        "Include screenshots if possible. Our technical team will respond within 24 hours."
                    ),
                    'category_slug': 'system-usage',
                    'order': 3
                },
                {
                    'question': 'How do I use the mobile app?',
                    'answer': (
                        "Using the mobile app:\n\n"
                        "1. Download from Google Play Store or Apple App Store\n"
                        "2. Log in with your school account credentials\n"
                        "3. Sets up notifications for important updates\n"
                        "4. Access all features available in the web version\n\n"
                        "The mobile app offers offline viewing for schedules and assignments."
                    ),
                    'category_slug': 'system-usage',
                    'order': 4
                },
                {
                    'question': 'How do I export my data or reports?',
                    'answer': (
                        "To export reports and data:\n\n"
                        "1. Navigate to the relevant section (Grades, Finance, etc.)\n"
                        "2. Click on \"Export\" or \"Download Report\"\n"
                        "3. Select your preferred format (PDF, Excel, CSV)\n"
                        "4. Choose date ranges and filters as needed\n"
                        "5. Click \"Generate\" and download\n\n"
                        "Exports are available for most reports and historical data."
                    ),
                    'category_slug': 'system-usage',
                    'order': 5
                },
                # Support & Communication
                {
                    'question': 'How do I contact my teachers or academic advisors?',
                    'answer': (
                        "Communication methods:\n\n"
                        "Through the System:\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Messages\" or \"Communication\"\n"
                        "3. Select your teacher/advisor from the directory\n"
                        "4. Send your message\n\n"
                        "Direct Contact: Use email addresses or phone numbers provided by your school.\n\n"
                        "Office Hours: Visit teachers during their posted office hours for in-person discussions."
                    ),
                    'category_slug': 'support-communication',
                    'order': 1
                },
                {
                    'question': 'Who do I contact for different types of support?',
                    'answer': (
                        "Support contacts by category:\n\n"
                        "Academic Issues: Academic advisor or department head\n"
                        "Technical Problems: IT Support (available 24/7 for critical issues)\n"
                        "Financial Concerns: Bursar's office\n"
                        "Medical/Health Issues: School nurse or health services\n"
                        "Disciplinary Matters: Student affairs office\n"
                        "General Support: Student services or reception\n\n"
                        "Use the support ticketing system for faster, tracked assistance."
                    ),
                    'category_slug': 'support-communication',
                    'order': 2
                },
                {
                    'question': 'How do I get emergency contact information?',
                    'answer': (
                        "Emergency contacts:\n\n"
                        "Within School Hours:\n"
                        "- Main Office: Ext. 100\n"
                        "- Security: Ext. 111 (Emergency button on all phones)\n"
                        "- Nurse: Ext. 222\n\n"
                        "Outside School Hours:\n"
                        "- Emergency Services: Call local emergency number\n"
                        "- School Administration: Contact the principal's direct line\n\n"
                        "All emergency procedures are posted in common areas and available on the school website."
                    ),
                    'category_slug': 'support-communication',
                    'order': 3
                },
                # Library Services
                {
                    'question': 'How do I search for books in the library?',
                    'answer': (
                        "To search the library catalog:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Library\" section\n"
                        "3. Use the search bar with keywords, author, or title\n"
                        "4. Filter results by subject, type, or availability\n"
                        "5. Click on a book to see details and reserve/place holds\n\n"
                        "You can also browse books by category or view new acquisitions."
                    ),
                    'category_slug': 'library-services',
                    'order': 1
                },
                {
                    'question': 'What are the library borrowing rules?',
                    'answer': (
                        "Library borrowing policy:\n\n"
                        "- Books: 2 weeks for general, 1 week for reference\n"
                        "- Maximum books: 5 for students, 10 for staff\n"
                        "- Renewals: Up to 2 times online\n"
                        "- Fines: $0.50 per day for overdue books\n"
                        "- Holds: Reserve books online when they're checked out\n\n"
                        "Lost or damaged books must be replaced or paid for. Check your library account regularly."
                    ),
                    'category_slug': 'library-services',
                    'order': 2
                },
                # Health & Medical
                {
                    'question': 'How do I schedule a health appointment?',
                    'answer': (
                        "To schedule medical care:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Health\" > \"Schedule Appointment\"\n"
                        "3. Select the type of service needed\n"
                        "4. Choose available date and time\n"
                        "5. Submit your request\n\n"
                        "Emergency medical issues should be reported to the school nurse immediately. Parents will be notified for serious concerns."
                    ),
                    'category_slug': 'health-medical',
                    'order': 1
                },
                {
                    'question': 'What medical services are available?',
                    'answer': (
                        "Available health services:\n\n"
                        "- Daily health check-ups\n"
                        "- First aid and emergency response\n"
                        "- Immunization tracking\n"
                        "- Health education and counseling\n"
                        "- Chronic condition management\n"
                        "- Mental health support\n\n"
                        "Students requiring regular medication should register with the health office. All services are confidential."
                    ),
                    'category_slug': 'health-medical',
                    'order': 2
                },
                # Transportation
                {
                    'question': 'How do I check bus routes and schedules?',
                    'answer': (
                        "To view transportation information:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Transportation\" section\n"
                        "3. View assigned bus route and stops\n"
                        "4. Check daily schedule and any changes\n"
                        "5. Download route maps for reference\n\n"
                        "Route changes are updated in real-time. Contact transport office for route changes or special requests."
                    ),
                    'category_slug': 'transportation',
                    'order': 1
                },
                {
                    'question': 'What should I do if I miss my bus?',
                    'answer': (
                        "If you miss your assigned bus:\n\n"
                        "- Contact the transport office immediately\n"
                        "- Inform your parents/guardians\n"
                        "- Use alternative transportation if arranged\n"
                        "- Report to school office for late arrival procedures\n\n"
                        "Never leave campus with unauthorized individuals. Safety protocols must be followed."
                    ),
                    'category_slug': 'transportation',
                    'order': 2
                },
                # Hostel & Accommodation
                {
                    'question': 'How do I apply for hostel accommodation?',
                    'answer': (
                        "Hostel application process:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Hostel\" > \"Apply for Accommodation\"\n"
                        "3. Fill out the application form\n"
                        "4. Upload required documents (ID, medical certificate, etc.)\n"
                        "5. Submit application with hostel fees\n\n"
                        "Applications are processed on a first-come basis. Space is limited and allocated by merit."
                    ),
                    'category_slug': 'hostel-accommodation',
                    'order': 1
                },
                {
                    'question': 'What are the hostel rules and regulations?',
                    'answer': (
                        "Important hostel rules:\n\n"
                        "- Check-in/out: 6 AM - 10 PM for security\n"
                        "- Visitors: Only during designated hours with permission\n"
                        "- Curfew: Must be in rooms by specified time\n"
                        "- Cleanliness: Maintain personal and common areas\n"
                        "- Noise: Respect quiet hours during study times\n\n"
                        "Violation of rules may result in warnings or expulsion. Safety and security are top priorities."
                    ),
                    'category_slug': 'hostel-accommodation',
                    'order': 2
                },
                # Activities & Clubs
                {
                    'question': 'How do I join a school club or activity?',
                    'answer': (
                        "To join extracurricular activities:\n\n"
                        "1. Log in to your account\n"
                        "2. Go to \"Activities\" > \"Browse Clubs\"\n"
                        "3. View available sports, clubs, and societies\n"
                        "4. Click \"Join\" for activities of interest\n"
                        "5. Attend the first meeting or tryout\n\n"
                        "Some activities have auditions, trials, or limited membership. Check activity requirements."
                    ),
                    'category_slug': 'activities-clubs',
                    'order': 1
                },
                {
                    'question': 'How do I view upcoming events and activities?',
                    'answer': (
                        "To browse school events:\n\n"
                        "1. Go to \"Activities\" > \"Events Calendar\"\n"
                        "2. View events by date, type, or participation\n"
                        "3. Filter by sports events, cultural programs, etc.\n"
                        "4. Click on events for details and registration\n\n"
                        "Subscribe to notifications for your favorite activities and never miss important events."
                    ),
                    'category_slug': 'activities-clubs',
                    'order': 2
                },
            ]

            faq_created = 0
            faq_updated = 0

            for faq_data in faqs_data:
                category = Category.objects.filter(slug=faq_data['category_slug']).first()
                if not category:
                    self.log_warning(f'Category {faq_data["category_slug"]} not found for FAQ: {faq_data["question"][:50]}...')
                    continue

                faq, created = FAQ.objects.get_or_create(
                    question__iexact=faq_data['question'],
                    category=category,
                    defaults={
                        'question': faq_data['question'],
                        'answer': faq_data['answer'].strip(),
                        'category': category,
                        'order': faq_data['order'],
                        'is_published': True
                    }
                )

                if created:
                    faq_created += 1
                    self.created += 1
                    self.log_success(f'Created FAQ: {faq_data["question"][:50]}...')
                else:
                    if faq.answer.strip() != faq_data['answer'].strip():
                        faq.answer = faq_data['answer'].strip()
                        faq.order = faq_data['order']
                        faq.save()
                        faq_updated += 1
                        self.updated += 1
                        self.log_warning(f'Updated FAQ: {faq_data["question"][:50]}...')

            self.log_success(f'FAQs setup complete. Created: {faq_created}, Updated: {faq_updated}')
        except Exception as e:
            self.log_error(f"Error populating FAQs: {e}")

    def _populate_legal_documents(self):
        """Create essential legal documents."""
        try:
            from apps.support.models import LegalDocument

            documents_data = [
                {
                    'document_type': 'terms_of_service',
                    'title': 'Terms of Service',
                    'slug': 'terms-of-service',
                    'content': (
                        "# Terms of Service for Nexus School Management System\n\n"
                        "## 1. Acceptance of Terms\n\n"
                        "By accessing and using the Nexus School Management System (\"the System\"), you accept and agree to be bound by the terms and provision of this agreement.\n\n"
                        "## 2. Use License\n\n"
                        "Permission is granted to temporarily download one copy of the System per user for personal, non-commercial transitory viewing only.\n\n"
                        "## 3. Disclaimer\n\n"
                        "The materials on the System are provided on an 'as is' basis. The School makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties including, without limitation, implied warranties or conditions of merchantability, fitness for a particular purpose, or non-infringement of intellectual property or other violation of rights.\n\n"
                        "## 4. Limitations\n\n"
                        "In no event shall the School or its suppliers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the System, even if the School or its authorized representative has been notified orally or in writing of the possibility of such damage.\n\n"
                        "## 5. Accuracy of Materials\n\n"
                        "The materials appearing on the System could include technical, typographical, or photographic errors. The School does not warrant that any of the materials on its System are accurate, complete, or current.\n\n"
                        "## 6. Modifications\n\n"
                        "The School may revise these terms of service at any time without notice. By using this System you are agreeing to be bound by the then current version of these Terms and Conditions of Use.\n\n"
                        "## 7. Data Privacy\n\n"
                        "Your privacy is important to us. Please review our Privacy Policy, which also governs your use of the System, to understand our practices.\n\n"
                        "## 8. User Obligations\n\n"
                        "Users agree to:\n"
                        "- Provide accurate and complete information\n"
                        "- Maintain the confidentiality of their account credentials\n"
                        "- Use the system responsibly and ethically\n"
                        "- Report any security concerns immediately\n"
                        "- Comply with all applicable school policies\n\n"
                        "## 9. System Availability\n\n"
                        "While we strive for 99.9%% uptime, the School does not guarantee uninterrupted access to the System. Maintenance windows will be announced in advance.\n\n"
                        "## 10. Termination\n\n"
                        "The School may terminate or suspend access to the System immediately, without prior notice, for conduct that violates these terms or applicable laws."
                    ),
                    'is_active': True,
                    'requires_acknowledgment': True
                },
                {
                    'document_type': 'privacy_policy',
                    'title': 'Privacy Policy',
                    'slug': 'privacy-policy',
                    'content': (
                        "# Privacy Policy for Nexus School Management System\n\n"
                        "## 1. Information We Collect\n\n"
                        "We collect information you provide directly to us, such as when you create an account, use our services, or contact us for support. This includes personal information like name, email, phone number, and academic records.\n\n"
                        "We also collect information automatically through your use of our system, including IP addresses, browser information, and usage patterns.\n\n"
                        "## 2. How We Use Your Information\n\n"
                        "We use the information we collect to:\n"
                        "- Provide, maintain, and improve our services\n"
                        "- Process transactions and send related information (fee payments, grades, etc.)\n"
                        "- Send you technical notices, updates, and support messages\n"
                        "- Communicate with parents about their children's progress\n"
                        "- Ensure the safety and security of all users\n"
                        "- Comply with legal and regulatory requirements\n\n"
                        "## 3. Information Sharing and Disclosure\n\n"
                        "We do not sell, trade, or otherwise transfer your personal information to third parties without your consent, except as described in this policy or required by law.\n\n"
                        "We may share information with:\n"
                        "- Parents/guardians for students under 18\n"
                        "- School staff when necessary for educational purposes\n"
                        "- Third-party service providers who assist our operations (under strict confidentiality agreements)\n"
                        "- Law enforcement when required by legal processes\n\n"
                        "## 4. Data Security\n\n"
                        "We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. These include encryption, access controls, and regular security audits.\n\n"
                        "## 5. Your Rights\n\n"
                        "You have the right to:\n"
                        "- Access your personal data\n"
                        "- Rectify inaccurate data\n"
                        "- Erase your data (\"right to be forgotten\")\n"
                        "- Restrict processing of your data\n"
                        "- Data portability\n"
                        "- Object to processing based on legitimate interests\n\n"
                        "## 6. Cookies and Tracking\n\n"
                        "We use cookies to enhance your experience, remember your preferences, and analyze system usage. You can control cookie settings through your browser.\n\n"
                        "## 7. Data Retention\n\n"
                        "We retain personal data only as long as necessary for the purposes for which it was collected, or as required by law. Academic records are typically retained for extended periods as required by education regulations.\n\n"
                        "## 8. Changes to This Policy\n\n"
                        "We may update this privacy policy from time to time. We will notify users of material changes through the system or email.\n\n"
                        "## 9. Contact Us\n\n"
                        "If you have questions about this privacy policy or our data practices, please contact the school's data protection officer."
                    ),
                    'is_active': True,
                    'requires_acknowledgment': True
                },
                {
                    'document_type': 'cookie_policy',
                    'title': 'Cookie Policy',
                    'slug': 'cookie-policy',
                    'content': (
                        "# Cookie Policy for Nexus School Management System\n\n"
                        "## What Are Cookies\n\n"
                        "Cookies are small text files that are placed on your computer or mobile device when you visit our website or use our applications.\n\n"
                        "## How We Use Cookies\n\n"
                        "We use cookies to:\n"
                        "- Remember your preferences and settings\n"
                        "- Keep you signed in to your account across sessions\n"
                        "- Analyze how our site is used to improve performance\n"
                        "- Remember your language and accessibility preferences\n"
                        "- Provide personalized content and recommendations\n\n"
                        "## Types of Cookies We Use\n\n"
                        "### Essential Cookies\n"
                        "Required for the website to function properly. These include authentication and security cookies.\n\n"
                        "### Analytics Cookies\n"
                        "Help us understand how visitors interact with our website, allowing us to improve the system. We use these to generate reports on system usage.\n\n"
                        "### Preference Cookies\n"
                        "Remember your settings and preferences, such as language selection and display options.\n\n"
                        "### Functional Cookies\n"
                        "Enable enhanced functionality, such as remembering form data and user preferences.\n\n"
                        "## Third-Party Cookies\n\n"
                        "Some features may use third-party services (like payment processors or analytics tools) that set their own cookies. We carefully select partners who align with our privacy standards.\n\n"
                        "## Managing Cookies\n\n"
                        "You can control cookies through your browser settings. However, disabling cookies may affect the functionality of our system. Essential cookies cannot be disabled as they are necessary for basic system operation.\n\n"
                        "### Browser Settings\n"
                        "- Chrome: Settings > Privacy and security > Cookies\n"
                        "- Firefox: Preferences > Privacy & Security > Cookies\n"
                        "- Safari: Preferences > Privacy > Manage Website Data\n"
                        "- Edge: Settings > Cookies and site permissions\n\n"
                        "## Cookie Duration\n\n"
                        "- Session cookies: Deleted when you close your browser\n"
                        "- Persistent cookies: Remain until deleted or expired\n"
                        "- Essential cookies: Typically expire with your session or after a short period\n\n"
                        "## Updates to This Policy\n\n"
                        "This cookie policy may be updated periodically. Significant changes will be communicated through the system."
                    ),
                    'is_active': True,
                    'requires_acknowledgment': False
                },
                {
                    'document_type': 'data_protection',
                    'title': 'Data Protection Policy',
                    'slug': 'data-protection',
                    'content': (
                        "# Data Protection Policy for Nexus School Management System\n\n"
                        "## 1. Introduction\n\n"
                        "This policy outlines how we handle personal data in compliance with applicable data protection laws, including GDPR, CCPA, and other relevant regulations.\n\n"
                        "## 2. Data Collection Principles\n\n"
                        "We collect and process personal data fairly, lawfully, and transparently. We ensure data is:\n"
                        "- Processed for specified, legitimate purposes\n"
                        "- Adequate, relevant, and limited to what's necessary\n"
                        "- Accurate and kept up to date\n"
                        "- Retained only as long as necessary\n"
                        "- Processed securely and confidentially\n\n"
                        "## 3. Lawful Bases for Processing\n\n"
                        "We process personal data based on:\n"
                        "- Consent from the data subject\n"
                        "- Contract performance\n"
                        "- Legal obligations\n"
                        "- Vital interests of the data subject\n"
                        "- Public task performance\n"
                        "- Legitimate interests\n\n"
                        "## 4. Data Subject Rights\n\n"
                        "You have the right to:\n"
                        "- Access your personal data and processing details\n"
                        "- Rectify inaccurate or incomplete data\n"
                        "- Erase your data (\"right to be forgotten\")\n"
                        "- Restrict processing of your data\n"
                        "- Data portability (receive your data in a structured format)\n"
                        "- Object to processing based on legitimate interests or direct marketing\n"
                        "- Not be subject to automated decision-making without human intervention\n\n"
                        "## 5. Parental Consent for Minors\n\n"
                        "For students under 18, we require parental consent for data processing and may share relevant information with parents/guardians. Parents have the right to review and request correction of their children's data.\n\n"
                        "## 6. Data Security Measures\n\n"
                        "We implement comprehensive security measures including:\n"
                        "- Encryption of data in transit and at rest\n"
                        "- Access controls and role-based permissions\n"
                        "- Regular security audits and penetration testing\n"
                        "- Employee training on data protection\n"
                        "- Secure backup and recovery procedures\n"
                        "- Incident response and breach notification procedures\n\n"
                        "## 7. Data Breach Procedures\n\n"
                        "In case of a data breach, we will:\n"
                        "- Assess and contain the breach\n"
                        "- Notify affected individuals within 72 hours\n"
                        "- Report to relevant data protection authorities\n"
                        "- Document the breach and implement corrective measures\n\n"
                        "## 8. International Data Transfers\n\n"
                        "When transferring data outside your country, we ensure adequate protection through:\n"
                        "- EU-approved adequacy decisions\n"
                        "- Standard contractual clauses\n"
                        "- Binding corporate rules\n"
                        "- Certification schemes\n\n"
                        "## 9. Data Retention\n\n"
                        "We retain personal data according to our retention schedule:\n"
                        "- Student academic records: 7 years after graduation\n"
                        "- Financial records: 7 years\n"
                        "- Contact information: While account is active\n"
                        "- Anonymized analytics data: Indefinitely\n\n"
                        "## 10. Data Protection Officer\n\n"
                        "Contact our Data Protection Officer for questions about this policy or to exercise your rights."
                    ),
                    'is_active': True,
                    'requires_acknowledgment': True
                },
                {
                    'document_type': 'acceptable_use_policy',
                    'title': 'Acceptable Use Policy',
                    'slug': 'acceptable-use-policy',
                    'content': (
                        "# Acceptable Use Policy\n\n"
                        "## 1. Purpose\n\n"
                        "This policy defines acceptable use of the Nexus School Management System to ensure a safe, productive, and respectful environment for all users.\n\n"
                        "## 2. General Guidelines\n\n"
                        "Users must:\n"
                        "- Use the system only for authorized educational and administrative purposes\n"
                        "- Respect the rights and privacy of others\n"
                        "- Protect their account credentials and not share access\n"
                        "- Report security concerns or inappropriate content immediately\n"
                        "- Comply with all applicable laws and school policies\n\n"
                        "## 3. Prohibited Activities\n\n"
                        "The following activities are strictly prohibited:\n"
                        "- Attempting to gain unauthorized access to accounts or systems\n"
                        "- Sharing or distributing inappropriate content\n"
                        "- Using the system for commercial purposes without permission\n"
                        "- Sending harassing, threatening, or offensive communications\n"
                        "- Violating intellectual property rights\n"
                        "- Installing unauthorized software or modifying system settings\n"
                        "- Excessive use that impacts system performance for others\n\n"
                        "## 4. Content Standards\n\n"
                        "All content posted or shared through the system must:\n"
                        "- Be accurate and appropriate for an educational environment\n"
                        "- Respect cultural, religious, and personal differences\n"
                        "- Not contain hate speech, discrimination, or harassment\n"
                        "- Not infringe on copyrights or other intellectual property rights\n"
                        "- Not promote illegal activities or violence\n\n"
                        "## 5. Internet and Network Usage\n\n"
                        "When using internet features:\n"
                        "- Access only appropriate websites and content\n"
                        "- Do not download or distribute copyrighted materials illegally\n"
                        "- Respect bandwidth limitations and network resources\n"
                        "- Report suspicious or harmful websites to administrators\n\n"
                        "## 6. Communication Standards\n\n"
                        "Electronic communications must:\n"
                        "- Be professional and appropriate\n"
                        "- Use correct grammar and respectful language\n"
                        "- Protect sensitive student information\n"
                        "- Not disclose confidential school matters\n"
                        "- Comply with family educational rights and privacy laws\n\n"
                        "## 7. Monitoring and Privacy\n\n"
                        "The school reserves the right to monitor, audit, and review system usage. Users should have no expectation of privacy when using school systems, though we respect individual privacy rights.\n\n"
                        "## 8. Consequences of Violation\n\n"
                        "Violations may result in:\n"
                        "- Warning and required training\n"
                        "- Temporary suspension of system access\n"
                        "- Permanent account termination\n"
                        "- Referral to school administration or legal authorities\n"
                        "- Potential disciplinary action or legal consequences\n\n"
                        "## 9. Incident Reporting\n\n"
                        "Report policy violations immediately to:\n"
                        "- System administrators for technical issues\n"
                        "- School administration for policy violations\n"
                        "- Your supervisor for workplace-related concerns\n\n"
                        "## 10. Policy Updates\n\n"
                        "This policy may be updated periodically. Users will be notified of significant changes through the system."
                    ),
                    'is_active': True,
                    'requires_acknowledgment': True
                },
                {
                    'document_type': 'accessibility_statement',
                    'title': 'Accessibility Statement',
                    'slug': 'accessibility-statement',
                    'content': (
                        "# Accessibility Statement for Nexus School Management System\n\n"
                        "## Our Commitment\n\n"
                        "We are committed to ensuring digital accessibility for people with disabilities. We strive to provide an inclusive environment where all users can access information and complete tasks effectively.\n\n"
                        "## Compliance Standards\n\n"
                        "Our website aims to conform to:\n"
                        "- Web Content Accessibility Guidelines (WCAG) 2.1 AA standards\n"
                        "- Section 508 of the Rehabilitation Act\n"
                        "- Accessibility for Ontarians with Disabilities Act (AODA) where applicable\n"
                        "- EN 301 549 standards for public procurement\n\n"
                        "## Accessibility Features\n\n"
                        "### Built-in Features\n"
                        "- Keyboard navigation support throughout the application\n"
                        "- Screen reader compatibility with popular assistive technologies\n"
                        "- High contrast options and customizable display settings\n"
                        "- Resizable text without loss of functionality (zoom up to 200%%)\n"
                        "- Consistent navigation and page structure\n"
                        "- Alternative text for all images and non-text content\n"
                        "- Clear heading hierarchy and semantic structure\n"
                        "- Form labels and error messages that work with assistive technologies\n\n"
                        "### Additional Support\n"
                        "- Multiple methods to access the same information\n"
                        "- Printable versions of important documents\n"
                        "- Video content with captions and transcripts\n"
                        "- Audio descriptions for video content when practical\n"
                        "- Consistent color schemes that are not relied upon alone for meaning\n\n"
                        "## Known Limitations\n\n"
                        "While we strive for full accessibility, some legacy content or third-party integrations may have limitations. We continuously work to improve accessibility across the system.\n\n"
                        "## Feedback and Support\n\n"
                        "If you encounter accessibility barriers, please contact us:\n\n"
                        "Accessibility Support Team\n"
                        "- Email: accessibility@nexus-sms.edu\n"
                        "- Phone: [School Accessibility Helpline]\n"
                        "- Through the system's support ticketing system\n\n"
                        "Provide details about:\n"
                        "- The page or feature you're trying to use\n"
                        "- The assistive technology you're using\n"
                        "- The specific barrier you're encountering\n"
                        "- Your preferred format for receiving information\n\n"
                        "## Response Time\n\n"
                        "We aim to respond to accessibility concerns within 2 business days. Complex issues requiring development changes will be prioritized and scheduled for resolution in upcoming updates.\n\n"
                        "## Progressive Enhancement\n\n"
                        "We are committed to progressive improvement. Each system update includes accessibility enhancements based on user feedback and technological advancements.\n\n"
                        "## Testing\n\n"
                        "Our accessibility testing includes:\n"
                        "- Automated accessibility scanners\n"
                        "- Manual testing with assistive technologies\n"
                        "- User testing with people with disabilities\n"
                        "- Compliance audits with accessibility experts\n\n"
                        "## Contact Information\n\n"
                        "For questions about this accessibility statement or to request accommodations:\n\n"
                        "Accessibility Officer\n"
                        "Nexus School Management System\n"
                        "Email: accessibility@nexus-sms.edu\n"
                        "Phone: [Contact Number]"
                    ),
                    'is_active': True,
                    'requires_acknowledgment': False
                }
            ]

            doc_created = 0
            doc_updated = 0

            for doc_data in documents_data:
                doc, created = LegalDocument.objects.get_or_create(
                    document_type=doc_data['document_type'],
                    defaults={
                        'title': doc_data['title'],
                        'slug': doc_data['slug'],
                        'content': doc_data['content'].strip(),
                        'is_active': doc_data['is_active'],
                        'requires_acknowledgment': doc_data['requires_acknowledgment']
                    }
                )

                if created:
                    doc_created += 1
                    self.created += 1
                    self.log_success(f'Created legal document: {doc_data["title"]}')
                else:
                    if not (doc.title == doc_data['title'] and
                            doc.content.strip() == doc_data['content'].strip() and
                            doc.slug == doc_data['slug'] and
                            doc.is_active == doc_data['is_active'] and
                            doc.requires_acknowledgment == doc_data['requires_acknowledgment']):
                        doc.title = doc_data['title']
                        doc.slug = doc_data['slug']
                        doc.content = doc_data['content'].strip()
                        doc.is_active = doc_data['is_active']
                        doc.requires_acknowledgment = doc_data['requires_acknowledgment']
                        doc.save()
                        doc_updated += 1
                        self.updated += 1
                        self.log_warning(f'Updated legal document: {doc_data["title"]}')

            self.log_success(f'Legal documents setup complete. Created: {doc_created}, Updated: {doc_updated}')
        except Exception as e:
            self.log_error(f"Error populating legal documents: {e}")

    def run_populate_commands(self):
        """Run all populate management commands to populate the database."""
        self.log_info("Running populate management commands...")

        populate_commands = [
            'populate_exam_types',
            'populate_faqs',
            'populate_legal_documents'
        ]

        for command_name in populate_commands:
            try:
                self.log_info(f'Running {command_name}...')
                call_command(command_name)
                self.log_success(f'Successfully executed {command_name}')
            except Exception as e:
                self.log_error(f'Failed to execute {command_name}: {e}')

    def create_superuser(self):
        """Create default superuser with username 'drmk' and password 'drmk'."""
        self.log_info("Creating default superuser...")

        username = "drmk"
        password = "drmk"

        if User.objects.filter(username=username).exists():
            self.log_warning(f"Superuser '{username}' already exists. Skipping creation.")
        else:
            User.objects.create_superuser(
                username=username,
                password=password,
                email=f"{username}@admin.com",
            )
            self.created += 1
            self.log_success(f"Superuser '{username}' created successfully.")

    def run_all_setup(self):
        """Run all setup functions in proper order."""
        print("=" * 60)
        print(" SCHOOL MANAGEMENT SYSTEM - CONSOLIDATED SETUP ")
        print("=" * 60)
        print()

        try:
            # Run setup functions in logical order
            self.create_superuser()
            self.setup_staff_roles()
            self.assign_role_permissions()
            self.setup_system_kpis()
            self.populate_exam_types()
            self.setup_support_data()

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
            import traceback
            traceback.print_exc()
            raise

    # Permission helper methods
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