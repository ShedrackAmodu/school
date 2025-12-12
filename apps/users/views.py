# apps/users/views.py

import logging
import secrets
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail, get_connection, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import smtplib
import ssl
from django.http import JsonResponse, HttpResponse
import csv
import openpyxl
from io import BytesIO


from apps.audit.models import AuditLog
from apps.academics.models import (
    AcademicSession, AcademicRecord, BehaviorRecord, Class, ClassMaterial,
    Enrollment, Student, Subject, SubjectAssignment, Teacher, Timetable
)

from .models import (
    User, UserProfile, Role, UserRole, LoginHistory,
    PasswordHistory, UserSession, ParentStudentRelationship,
    StudentApplication, StaffApplication, UserRoleActivity,
    get_student_guardians, notify_guardians_profile_update
)
from .forms import (
    UserCreationForm, UserUpdateForm, UserProfileForm, RoleForm,
    UserRoleAssignmentForm, CustomPasswordChangeForm, ParentStudentRelationshipForm,
    StudentApplicationForm, StaffApplicationForm, LoginHistorySearchForm,
    UserBulkActionForm, UserImportForm
)

logger = logging.getLogger(__name__)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def can_assign_roles(user):
    """
    Check if user can assign roles to other users.
    Only superusers and school admins (admin/principal roles) can assign roles.
    """
    if user.is_superuser:
        return True

    # Check if user has admin or principal role
    return user.user_roles.filter(
        role__role_type__in=['admin', 'principal'],
        status='active'
    ).exists()


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def login_history(request):
    """
    View login history with search and filtering capabilities.
    """
    from django.core.paginator import Paginator
    
    # Get login history queryset
    login_entries = LoginHistory.objects.select_related('user').order_by('-created_at')
    
    # Filter by user if specified (for user detail page link)
    user_id = request.GET.get('user')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            login_entries = login_entries.filter(user=user)
        except User.DoesNotExist:
            messages.error(request, _('User not found.'))
            return redirect('users:user_list')
    
    # Apply form filters
    form = LoginHistorySearchForm(request.GET)
    if form.is_valid():
        # User filter
        if form.cleaned_data['user']:
            login_entries = login_entries.filter(user=form.cleaned_data['user'])
        
        # Success filter
        if form.cleaned_data['was_successful'] != '':
            if form.cleaned_data['was_successful'] == 'true':
                login_entries = login_entries.filter(was_successful=True)
            elif form.cleaned_data['was_successful'] == 'false':
                login_entries = login_entries.filter(was_successful=False)
        
        # Date range filter
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        date_range = form.cleaned_data.get('date_range')
        
        if date_range == 'custom' and start_date and end_date:
            login_entries = login_entries.filter(created_at__date__range=[start_date, end_date])
        elif date_range == 'today':
            today = timezone.now().date()
            login_entries = login_entries.filter(created_at__date=today)
        elif date_range == 'week':
            week_ago = timezone.now() - timezone.timedelta(days=7)
            login_entries = login_entries.filter(created_at__gte=week_ago)
        elif date_range == 'month':
            month_ago = timezone.now() - timezone.timedelta(days=30)
            login_entries = login_entries.filter(created_at__gte=month_ago)

def create_user_from_student_application(application, reviewed_by):
    """Create user account from approved student application."""
    try:
        with transaction.atomic():
            # Generate temporary password
            characters = string.ascii_letters + string.digits + string.punctuation
            temporary_password = ''.join(secrets.choice(characters) for i in range(12))

            # Check if user already exists
            user, created = User.objects.get_or_create(
                email=application.email,
                defaults={
                    'first_name': application.first_name,
                    'last_name': application.last_name,
                    'mobile': application.phone,
                    'is_active': True,
                    'is_verified': True, # Will need to verify email
                }
            )

            if created:
                user.set_password(temporary_password)
            else:
                # If user exists, update their details and set a new temporary password
                user.first_name = application.first_name
                user.last_name = application.last_name
                user.mobile = application.phone
                user.is_active = True
                user.is_verified = True
                user.set_password(temporary_password) # Reset password for existing user
            user.save()

            # Update profile
            profile = user.profile
            profile.date_of_birth = application.date_of_birth
            profile.gender = application.gender
            profile.nationality = application.nationality
            profile.address_line_1 = application.address
            profile.city = application.city
            profile.state = application.state
            profile.postal_code = application.postal_code
            profile.country = application.country
            profile.save()

            # Create Student profile
            from apps.academics.models import Student
            student, student_created = Student.objects.get_or_create(
                user=user,
                defaults={
                    'admission_number': application.application_number,  # Use application number as admission number
                    'admission_date': timezone.now().date(),
                    'date_of_birth': application.date_of_birth,
                    'place_of_birth': '',  # Could be added to application form later
                    'gender': application.gender,
                    'nationality': application.nationality,
                    'previous_school': application.previous_school or '',
                    'status': 'active',
                }
            )

            if not student_created:
                # Update existing student profile
                student.admission_number = application.application_number
                student.admission_date = timezone.now().date()
                student.date_of_birth = application.date_of_birth
                student.gender = application.gender
                student.nationality = application.nationality
                student.previous_school = application.previous_school or ''
                student.status = 'active'
                student.save()

            student_role = Role.objects.filter(role_type='student').first()
            if not student_role:
                student_role = Role.objects.create(
                    name='Student',
                    role_type='student',
                    description='Student role',
                    hierarchy_level=10,
                    is_system_role=True,
                    status='active'
                )

            UserRole.objects.create(
                user=user,
                role=student_role,
                is_primary=True,
                academic_session=application.academic_session,
                context_id=f"grade_{application.grade_applying_for}"
            )
            
            # Create parent relationship if parent email is different
            if application.parent_email and application.parent_email != application.email:
                parent_user, created = User.objects.get_or_create(
                    email=application.parent_email,
                    defaults={
                        'first_name': application.parent_first_name or 'Parent',
                        'last_name': application.parent_last_name or 'User',
                        'mobile': application.parent_phone,
                        'is_active': True,
                    }
                )
                
                if created:
                    # Set temporary password for parent
                    parent_user.make_random_password(length=12)
                    
                    # Get or create parent role - FIXED VERSION
                    parent_role = Role.objects.filter(role_type='parent').first()
                    if not parent_role:
                        parent_role = Role.objects.create(
                            name='Parent',
                            role_type='parent',
                            description='Parent role',
                            hierarchy_level=20,
                            is_system_role=True,
                            status='active'
                        )
                    
                    UserRole.objects.create(
                        user=parent_user,
                        role=parent_role,
                        is_primary=True
                    )
                    # Create profile for parent if it doesn't exist
                    if not hasattr(parent_user, 'profile'):
                        UserProfile.objects.create(user=parent_user)
                
                # Create parent-student relationship
                ParentStudentRelationship.objects.create(
                    parent=parent_user,
                    student=user,
                    relationship_type=application.parent_relationship,
                    is_primary_contact=True
                )
            
            return user, temporary_password
            
    except Exception as e:
        logger.error(f"Error creating user from student application: {e}")
        raise

def create_user_from_staff_application(application, reviewed_by):
    """Create user account from approved staff application."""
    try:
        with transaction.atomic():
            # Generate temporary password
            characters = string.ascii_letters + string.digits + string.punctuation
            temporary_password = ''.join(secrets.choice(characters) for i in range(12))

            # Check if user already exists
            user, created = User.objects.get_or_create(
                email=application.email,
                defaults={
                    'first_name': application.first_name,
                    'last_name': application.last_name,
                    'mobile': application.phone,
                    'is_active': True,
                    'is_verified': True,
                    'status': 'active',
                }
            )

            if created:
                user.set_password(temporary_password)
            else:
                # If user exists, update their details and set a new temporary password
                user.first_name = application.first_name
                user.last_name = application.last_name
                user.mobile = application.phone
                user.is_active = True
                user.is_verified = True
                user.status = 'active'
                user.set_password(temporary_password) # Reset password for existing user
            user.save()

            # Update profile
            profile = user.profile
            profile.date_of_birth = application.date_of_birth
            profile.gender = application.gender
            profile.nationality = application.nationality
            profile.address_line_1 = application.address
            profile.city = application.city
            profile.state = application.state
            profile.postal_code = application.postal_code
            profile.country = application.country
            profile.bio = f"Applied for {application.position_applied_for.name} position"
            profile.save()

            # Generate employee ID using SequenceGenerator
            from apps.core.models import SequenceGenerator
            sequence, created = SequenceGenerator.objects.get_or_create(
                sequence_type='employee_id',
                defaults={
                    'prefix': 'EMP',
                    'last_number': 0,
                    'padding': 6
                }
            )
            employee_id = sequence.get_next_number()

            # Create staff profile based on position type
            position_role_type = application.position_applied_for.role_type

            if position_role_type == 'teacher':
                # Create Teacher profile
                from apps.academics.models import Teacher
                teacher, teacher_created = Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        'teacher_id': f"T{employee_id[3:]}",  # Remove EMP prefix and add T
                        'employee_id': employee_id,
                        'date_of_birth': application.date_of_birth,
                        'gender': application.gender,
                        'qualification': application.highest_qualification,
                        'specialization': application.previous_position or '',
                        'joining_date': timezone.now().date(),
                        'experience_years': application.years_of_experience,
                        'bio': f"Hired as {application.position_applied_for.name}",
                        'status': 'active'
                    }
                )
                if not teacher_created:
                    # Update existing teacher profile
                    teacher.employee_id = employee_id
                    teacher.qualification = application.highest_qualification
                    teacher.specialization = application.previous_position or teacher.specialization
                    teacher.experience_years = application.years_of_experience
                    teacher.save()

            elif position_role_type == 'driver':
                # Create Driver profile
                from apps.transport.models import Driver
                driver, driver_created = Driver.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_id': employee_id,
                        'license_number': '',  # Will need to be updated later
                        'license_type': 'lmv',
                        'license_expiry': timezone.now().date() + timezone.timedelta(days=365),  # Default 1 year
                        'date_of_birth': application.date_of_birth,
                        'date_of_joining': timezone.now().date(),
                        'status': 'active'
                    }
                )
                if not driver_created:
                    driver.employee_id = employee_id
                    driver.save()

            elif position_role_type in ['support', 'librarian', 'accountant']:
                # For support staff, create Attendant profile (can be used for various support roles)
                from apps.transport.models import Attendant
                attendant, attendant_created = Attendant.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_id': employee_id,
                        'date_of_birth': application.date_of_birth,
                        'date_of_joining': timezone.now().date(),
                        'responsibilities': f"{application.position_applied_for.name} responsibilities",
                        'status': 'active'
                    }
                )
                if not attendant_created:
                    attendant.employee_id = employee_id
                    attendant.responsibilities = f"{application.position_applied_for.name} responsibilities"
                    attendant.save()

            # Assign staff role if not already assigned
            existing_role = UserRole.objects.filter(
                user=user,
                role=application.position_applied_for,
                academic_session=application.academic_session
            ).first()

            if not existing_role:
                UserRole.objects.create(
                    user=user,
                    role=application.position_applied_for,
                    is_primary=True,
                    academic_session=application.academic_session
                )

            # Set staff permissions based on role
            if position_role_type in ['admin', 'principal', 'teacher']:
                user.is_staff = True
                user.save()

            return user, temporary_password

    except Exception as e:
        logger.error(f"Error creating user from staff application: {e}")
        raise

def send_email_with_retry(subject, message, from_email, recipient_list, html_message=None, max_retries=3):
    """
    Send email with retry logic and better error handling for Gmail.
    """
    connection = None
    last_error = None

    for attempt in range(max_retries):
        try:
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
            )

            if html_message:
                email.content_subtype = 'html'
                email.body = html_message

            # Get connection with proper Gmail settings
            connection = get_connection()

            # Send the email
            email.send()

            logger.info(f"Email sent successfully to {recipient_list} on attempt {attempt + 1}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            last_error = f"Authentication failed: {e}"
            logger.error(f"SMTP Authentication Error (attempt {attempt + 1}): {e}")
            # Don't retry auth errors
            break
        except smtplib.SMTPConnectError as e:
            last_error = f"Connection failed: {e}"
            logger.error(f"SMTP Connection Error (attempt {attempt + 1}): {e}")
        except smtplib.SMTPException as e:
            last_error = f"SMTP error: {e}"
            logger.error(f"SMTP Error (attempt {attempt + 1}): {e}")
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected email error (attempt {attempt + 1}): {e}")

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            import time
            time.sleep(2 ** attempt)

    logger.error(f"Failed to send email after {max_retries} attempts. Last error: {last_error}")
    return False

def send_approval_email(request, application, user, temporary_password):
    """Send approval email with login credentials."""
    subject = _('Application Approved - Welcome to {}').format(getattr(settings, 'SCHOOL_NAME', 'Our School'))

    # Get student information if this is a student application
    student_id = None
    admission_number = None
    if hasattr(user, 'student_profile'):
        student_id = user.student_profile.student_id
        admission_number = user.student_profile.admission_number

    # Check if this was a staff application that went through interview process
    had_interview = False
    interview_date = None
    if hasattr(application, 'interview_date') and application.interview_date:
        had_interview = True
        interview_date = application.interview_date

    context = {
        'application': application,
        'user': user,
        'temporary_password': temporary_password,
        'login_url': request.build_absolute_uri(reverse('users:login')),
        'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
        'contact_email': settings.DEFAULT_FROM_EMAIL,
        'student_id': student_id,
        'admission_number': admission_number,
        'had_interview': had_interview,
        'interview_date': interview_date,
    }

    html_message = render_to_string('users/emails/application_approved.html', context)
    text_message = strip_tags(html_message)

    success = send_email_with_retry(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

    if success:
        logger.info(f"Approval email sent to {user.email}")
    else:
        logger.error(f"Failed to send approval email to {user.email}")

def send_rejection_email(application, review_notes):
    """Send rejection email to applicant."""
    subject = _('Application Update - {}').format(application.application_number)

    context = {
        'application': application,
        'review_notes': review_notes,
        'contact_email': settings.DEFAULT_FROM_EMAIL,
    }

    html_message = render_to_string('users/emails/application_rejected.html', context)
    text_message = strip_tags(html_message)

    success = send_email_with_retry(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message
    )

    if success:
        logger.info(f"Rejection email sent to {application.email}")
    else:
        logger.error(f"Failed to send rejection email to {application.email}")

def send_interview_email(application, interview_date, review_notes):
    """Send interview scheduling email to applicant."""
    subject = _('Interview Scheduled - {}').format(application.application_number)

    context = {
        'application': application,
        'interview_date': interview_date,
        'review_notes': review_notes,
        'contact_email': settings.DEFAULT_FROM_EMAIL,
        'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
    }

    html_message = render_to_string('users/emails/interview_scheduled.html', context)
    text_message = strip_tags(html_message)

    success = send_email_with_retry(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.email],
        html_message=html_message
    )

    if success:
        logger.info(f"Interview scheduling email sent to {application.email}")
    else:
        logger.error(f"Failed to send interview scheduling email to {application.email}")

def get_user_redirect_url(user):
    """
    Determine redirect URL based on user's primary role.
    """
    try:
        primary_role = user.user_roles.filter(is_primary=True).first()
        
        if not primary_role:
            # If no primary role, check any role
            any_role = user.user_roles.first()
            if any_role:
                return get_role_redirect_url(any_role.role.role_type)
            return reverse('users:dashboard')
        
        return get_role_redirect_url(primary_role.role.role_type)
    
    except Exception as e:
        logger.error(f"Error determining redirect URL for user {user.id}: {e}")
        return reverse('users:dashboard')

def get_role_redirect_url(role_type):
    """
    Map role types to their respective dashboard URLs.
    """
    role_redirects = {
        'super_admin': reverse('admin:index'),
        'admin': reverse('core:school_admin_dashboard'),
        'principal': reverse('core:school_admin_dashboard'),
        'teacher': reverse('users:dashboard'),
        'student': reverse('users:dashboard'),
        'parent': reverse('users:dashboard'),
        'accountant': reverse('finance:dashboard'),
        'librarian': reverse('library:librarian_dashboard'),
        'driver': reverse('transport:driver_dashboard'),
        'support': reverse('support:dashboard'),
    }
    return role_redirects.get(role_type, reverse('users:dashboard'))

# =============================================================================
# APPLICATION DETAIL VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.view_staffapplication'))
def staff_application_detail(request, application_id):
    """
    View detailed information about a specific staff application.
    """
    application = get_object_or_404(StaffApplication, id=application_id)

    context = {
        'title': _('Staff Application Details'),
        'application': application,
        'active_tab': 'applications',
    }
    return render(request, 'users/admin/applications/staff_application_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.view_studentapplication'))
def student_application_detail(request, application_id):
    """
    View detailed information about a specific student application.
    """
    application = get_object_or_404(StudentApplication, id=application_id)

    context = {
        'title': _('Student Application Details'),
        'application': application,
        'active_tab': 'applications',
    }
    return render(request, 'users/admin/applications/student_application_detail.html', context)

# =============================================================================
# GUEST/PUBLIC VIEWS
# =============================================================================

def guest_home(request):
    """
    Main landing page for non-authenticated users.
    """
    context = {
        'title': _('Welcome to Nexus Intelligence School Management System'),
        'show_application_links': True,
    }
    return render(request, 'users/guest/guest_home.html', context)

def application_portal(request):
    """
    Portal where non-members can apply as students or staff.
    """
    context = {
        'title': _('Application Portal'),
        'academic_sessions': AcademicSession.objects.filter(status='active', is_current=True),
    }
    return render(request, 'users/applications/application_portal.html', context)

def application_submitted(request):
    """
    Confirmation page after application submission.
    """
    context = {
        'title': _('Application Submitted'),
        'message': _('Thank you for your application! We have received your submission and will review it shortly.'),
        'show_application_links': False,
    }
    return render(request, 'users/applications/application_submitted.html', context)

class StudentApplicationView(FormView):
    """
    View for student applications.
    """
    template_name = 'users/applications/student_application.html'
    form_class = StudentApplicationForm
    success_url = reverse_lazy('users:application_submitted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Student Application')
        context['academic_sessions'] = AcademicSession.objects.filter(status='active', is_current=True)
        return context
    
    def form_valid(self, form):
        try:
            # Save the application
            application = form.save(commit=False)
            
            # Set additional fields
            application.application_status = StudentApplication.ApplicationStatus.PENDING
            
            # Handle academic_session - it's now required in the form
            academic_session = form.cleaned_data.get('academic_session')
            if academic_session:
                application.academic_session = academic_session
            
            # Save the application
            application.save()
            
            # Log the application submission
            AuditLog.objects.create(
                user=None,  # No user since it's a public application
                action=AuditLog.ActionType.CREATE,
                model_name='users.StudentApplication',
                object_id=str(application.id),
                ip_address=get_client_ip(self.request),
                details={
                    'action': 'Student application submitted',
                    'application_number': application.application_number,
                    'grade': application.grade_applying_for,
                    'academic_session': str(application.academic_session) if application.academic_session else 'Not specified'
                }
            )
            
            # Send confirmation email to applicant
            self.send_application_confirmation_email(application)
            
            # Send notification email to admin
            self.send_admin_notification_email(application)
            
            messages.success(self.request, _('Student application submitted successfully! You will receive a confirmation email shortly.'))
            
        except Exception as e:
            logger.error(f"Error submitting student application: {e}")
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Form data: {form.cleaned_data}")
            messages.error(self.request, _('There was an error submitting your application. Please check the form and try again.'))
            return self.form_invalid(form)
        
        return super().form_valid(form)

    def send_application_confirmation_email(self, application):
        """Send confirmation email to student applicant."""
        subject = _('Application Received - {}').format(getattr(settings, 'SCHOOL_NAME', 'Our School'))
        
        context = {
            'application': application,
            'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
            'contact_email': settings.DEFAULT_FROM_EMAIL,
        }
        
        message = render_to_string('users/emails/student_application_confirmation.html', context)
        
        try:
            send_mail(
                subject,
                strip_tags(message),
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                html_message=message,
                fail_silently=False,
            )
            logger.info(f"Student application confirmation email sent to {application.email}")
        except Exception as e:
            logger.error(f"Error sending student application confirmation email: {e}")
            raise

    def send_admin_notification_email(self, application):
        """Send notification email to admin about new student application."""
        subject = _('New Student Application Received - {}').format(application.application_number)
        
        context = {
            'application': application,
            'admin_url': self.request.build_absolute_uri(reverse('users:pending_applications')),
            'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
        }
        
        message = render_to_string('users/emails/admin_student_application_notification.html', context)
        
        admin_emails = [email for name, email in settings.ADMINS] if hasattr(settings, 'ADMINS') else [settings.DEFAULT_FROM_EMAIL]
        
        try:
            send_mail(
                subject,
                strip_tags(message),
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                html_message=message,
                fail_silently=False,
            )
            logger.info(f"Admin notification email sent for application {application.application_number}")
        except Exception as e:
            logger.error(f"Error sending admin notification email for application {application.application_number}: {e}")
            raise

class StaffApplicationView(FormView):
    """
    View for staff applications.
    """
    template_name = 'users/applications/staff_application.html'
    form_class = StaffApplicationForm
    success_url = reverse_lazy('users:application_submitted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Staff Application')
        context['staff_types'] = Role.objects.exclude(role_type__in=['student', 'parent']).filter(status='active')
        context['academic_sessions'] = AcademicSession.objects.filter(status='active', is_current=True)
        return context
    
    def send_application_confirmation_email(self, application):
        """Send confirmation email to staff applicant."""
        subject = _('Staff Application Received - {}').format(getattr(settings, 'SCHOOL_NAME', 'Our School'))

        context = {
            'application': application,
            'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
            'contact_email': settings.DEFAULT_FROM_EMAIL,
        }

        try:
            message = render_to_string('users/emails/staff_application_confirmation.html', context)

            send_mail(
                subject,
                strip_tags(message),
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                html_message=message,
                fail_silently=True,  # Changed to fail_silently=True to prevent application failure
            )
            logger.info(f"Staff application confirmation email sent to {application.email}")
            return True
        except Exception as e:
            logger.error(f"Error sending staff application confirmation email to {application.email}: {e}")
            return False

    def send_admin_notification_email(self, application):
        """Send notification email to admin about new staff application."""
        subject = _('New Staff Application Received - {}').format(application.application_number)

        context = {
            'application': application,
            'admin_url': self.request.build_absolute_uri(reverse('users:pending_applications')),
            'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
        }

        try:
            message = render_to_string('users/emails/admin_staff_application_notification.html', context)

            admin_emails = [email for name, email in settings.ADMINS] if hasattr(settings, 'ADMINS') else [settings.DEFAULT_FROM_EMAIL]

            send_mail(
                subject,
                strip_tags(message),
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                html_message=message,
                fail_silently=True,  # Changed to fail_silently=True to prevent application failure
            )
            logger.info(f"Admin notification email sent for staff application {application.application_number}")
            return True
        except Exception as e:
            logger.error(f"Error sending admin notification email for staff application {application.application_number}: {e}")
            return False
    
    def form_valid(self, form):
        try:
            logger.info(f"Starting staff application submission for email: {form.cleaned_data.get('email')}")

            # Save the application
            application = form.save(commit=False)

            # Set additional fields
            application.application_status = StaffApplication.ApplicationStatus.PENDING

            # Save the application
            application.save()

            logger.info(f"Staff application saved successfully with ID: {application.id}, number: {application.application_number}")

            # Log the application submission
            AuditLog.objects.create(
                user=None,  # No user since it's a public application
                action=AuditLog.ActionType.CREATE,
                model_name='users.StaffApplication',
                object_id=str(application.id),
                ip_address=get_client_ip(self.request),
                details={
                    'action': 'Staff application submitted',
                    'application_number': application.application_number,
                    'position': application.position_applied_for.name if application.position_applied_for else 'Not specified'
                }
            )

            # Send confirmation email to applicant
            email_sent_to_applicant = self.send_application_confirmation_email(application)
            if email_sent_to_applicant:
                logger.info(f"Confirmation email sent successfully to {application.email}")
            else:
                logger.warning(f"Failed to send confirmation email to {application.email}")

            # Send notification email to admin
            email_sent_to_admin = self.send_admin_notification_email(application)
            if email_sent_to_admin:
                logger.info(f"Admin notification email sent successfully for application {application.application_number}")
            else:
                logger.warning(f"Failed to send admin notification email for application {application.application_number}")

            # Success message based on email status
            if email_sent_to_applicant and email_sent_to_admin:
                messages.success(self.request, _('Staff application submitted successfully! You will receive a confirmation email shortly.'))
            elif email_sent_to_applicant:
                messages.success(self.request, _('Staff application submitted successfully! You will receive a confirmation email shortly. (Note: Admin notification may be delayed)'))
            elif email_sent_to_admin:
                messages.warning(self.request, _('Staff application submitted successfully, but there was an issue sending the confirmation email. Please check your email later or contact support.'))
            else:
                messages.warning(self.request, _('Staff application submitted successfully, but there were issues sending emails. Please contact support if you do not receive confirmation.'))

        except Exception as e:
            logger.error(f"Error submitting staff application: {e}")
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Form data: {form.cleaned_data}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Provide more specific error messages
            error_message = str(e).lower()
            if "unique constraint failed" in error_message or "duplicate key value" in error_message:
                messages.error(self.request, _('An application with this email address has already been submitted.'))
            elif "file" in error_message and ("size" in error_message or "type" in error_message):
                messages.error(self.request, _('There was an issue with one of your uploaded files. Please check the file type and size.'))
            elif "sequence" in error_message:
                messages.error(self.request, _('There was a system error generating your application number. Please try again.'))
            elif "validation" in error_message:
                messages.error(self.request, _('Please check your form data and try again. Some fields may be invalid.'))
            else:
                messages.error(self.request, _('There was an error submitting your application. Please try again or contact support if the problem persists.'))

            return self.form_invalid(form)

        return super().form_valid(form)

def send_password_change_email(user, request):
    """
    Send email confirmation when user changes password.
    """
    subject = _('Password Changed - {}').format(getattr(settings, 'SCHOOL_NAME', 'Our School'))

    context = {
        'user': user,
        'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
        'contact_email': settings.DEFAULT_FROM_EMAIL,
        'login_url': request.build_absolute_uri(reverse('users:login')),
        'change_date': timezone.now(),
    }

    html_message = render_to_string('users/emails/password_changed.html', context)
    text_message = strip_tags(html_message)

    success = send_email_with_retry(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

    if success:
        logger.info(f"Password change email sent to {user.email}")
    else:
        logger.error(f"Failed to send password change email to {user.email}")

    return success

# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

def custom_login(request):
    """
    Custom login view with enhanced logging and security.
    """
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect(get_user_redirect_url(request.user))

    change_password_mode = False

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(f"Login attempt - Email: {email}")  # Debug line
        remember_me = request.POST.get('remember_me')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        change_password = request.POST.get('change_password')

        # Check if this is a change password request
        if change_password and new_password and confirm_password:
            # Change password mode
            change_password_mode = True
            user = authenticate(request, email=email, password=password)

            if user is not None:
                # Check if user is active
                if not user.is_active:
                    messages.error(request, _('Your account is inactive. Please contact administrator.'))
                    return render(request, 'users/auth/login.html', {'change_password_mode': change_password_mode})

                if new_password != confirm_password:
                    messages.error(request, _('New passwords do not match.'))
                    return render(request, 'users/auth/login.html', {'change_password_mode': change_password_mode})

                # Validate new password strength
                if len(new_password) < 8:
                    messages.error(request, _('Password must be at least 8 characters long.'))
                    return render(request, 'users/auth/login.html', {'change_password_mode': change_password_mode})

                # Change password
                user.set_password(new_password)
                user.save()

                # Send password change confirmation email
                send_password_change_email(user, request)

                # Log password change
                AuditLog.objects.create(
                    user=user,
                    action=AuditLog.ActionType.UPDATE,
                    model_name='users.User',
                    object_id=str(user.id),
                    ip_address=get_client_ip(request),
                    details={'action': 'Password changed via login page'}
                )

                messages.success(request, _('Password changed successfully! Please log in with your new password.'))
                return redirect('users:login')
            else:
                messages.error(request, _('Invalid email or current password.'))
                return render(request, 'users/auth/login.html', {'change_password_mode': change_password_mode})
        else:
            # Normal login attempt
            # Authenticate user
            user = authenticate(request, email=email, password=password)
            print(f"Authentication result: {user}")  # Debug line

            # Log login attempt
            login_history = LoginHistory(
                user=user if user else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                was_successful=user is not None,
                failure_reason='' if user else 'Invalid credentials'
            )

            if user is not None:
                # Check if user is active
                if not user.is_active:
                    login_history.failure_reason = 'Account inactive'
                    login_history.save()
                    messages.error(request, _('Your account is inactive. Please contact administrator.'))
                    return render(request, 'users/auth/login.html')

                # Check if user is verified (if required)
                if not user.is_verified:
                    login_history.failure_reason = 'Email not verified'
                    login_history.save()
                    messages.warning(request, _('Please verify your email before logging in.'))
                    return render(request, 'users/auth/login.html')

                # Login successful
                login(request, user)
                login_history.was_successful = True
                login_history.failure_reason = ''
                login_history.save()

                # Update user login stats
                user.increment_login_count()
                user.current_login_ip = get_client_ip(request)
                user.save()

                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Browser session
                else:
                    request.session.set_expiry(1209600)  # 2 weeks

                # Log audit event
                AuditLog.objects.create(
                    user=user,
                    action=AuditLog.ActionType.LOGIN,
                    model_name='users.User',
                    object_id=str(user.id),
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                messages.success(request, _('Login successful!'))
                logger.debug(f"User {user.email} authenticated. Is authenticated: {request.user.is_authenticated}. Redirecting to: {get_user_redirect_url(user)}")
                return redirect(get_user_redirect_url(user))

            else:
                # Login failed
                login_history.save()
                messages.error(request, _('Invalid email or password.'))

    context = {
        'title': _('Login'),
        'show_application_links': True,
        'change_password_mode': change_password_mode,
    }
    return render(request, 'users/auth/login.html', context)

def custom_logout(request):
    """
    Custom logout view with logging.
    """
    if request.user.is_authenticated:
        # Log audit event
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.LOGOUT,
            model_name='users.User',
            object_id=str(request.user.id),
            ip_address=get_client_ip(request)
        )
    
    logout(request)
    messages.info(request, _('You have been logged out successfully.'))
    return redirect('users:guest_home')

# =============================================================================
# DASHBOARD & PROFILE VIEWS
# =============================================================================

@login_required
def user_dashboard(request):
    """
    Main user dashboard - redirects to role-specific dashboard or shows basic dashboard.
    """
    logger.debug(f"Accessing user_dashboard. Is authenticated: {request.user.is_authenticated}. User: {request.user.email}")
    try:
        redirect_url = get_user_redirect_url(request.user)
        logger.debug(f"user_dashboard determined redirect URL: {redirect_url} for user {request.user.email}")

        # Prevent redirect loop if get_user_redirect_url points back to user_dashboard itself
        if redirect_url == reverse('users:dashboard'):
            logger.debug("Redirect URL is 'users:dashboard', rendering generic dashboard directly.")
            primary_role = request.user.user_roles.filter(is_primary=True).first()
            context = {
                'title': _('Dashboard'),
                'user': request.user,
                'primary_role': primary_role,
            }

            # Add role-based context variables for sidebar navigation
            primary_role = request.user.user_roles.filter(is_primary=True).first()
            user_roles = request.user.user_roles.all()

            # Role flags for sidebar
            is_student = hasattr(request.user, 'student_profile')
            is_teacher = request.user.user_roles.filter(role__role_type='teacher').exists()
            is_parent = request.user.user_roles.filter(role__role_type='parent').exists()
            can_manage_academics = request.user.user_roles.filter(
                role__role_type__in=['admin', 'principal', 'teacher']
            ).exists()
            can_manage_users = request.user.is_superuser or request.user.user_roles.filter(
                role__role_type__in=['admin', 'principal']
            ).exists()
            can_manage_library = request.user.user_roles.filter(
                role__role_type__in=['admin', 'principal', 'librarian']
            ).exists()
            can_manage_transport = request.user.user_roles.filter(
                role__role_type__in=['admin', 'principal', 'driver']
            ).exists()
            can_manage_hostels = request.user.user_roles.filter(
                role__role_type__in=['admin', 'principal', 'warden']
            ).exists()

            # Get unread notification count
            from apps.communication.models import RealTimeNotification
            unread_notification_count = RealTimeNotification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()

            # Add student-specific context if user is a student
            if is_student:
                student = request.user.student_profile
                current_session = AcademicSession.objects.filter(is_current=True).first()

                # Get current enrollment
                current_enrollment = None
                if current_session:
                    current_enrollment = student.enrollments.filter(
                        academic_session=current_session,
                        enrollment_status='active'
                    ).select_related('class_enrolled').first()

                # Add calculated class statistics if enrollment exists
                if current_enrollment:
                    current_class = current_enrollment.class_enrolled
                    # Calculate student count for the class
                    student_count = current_class.enrollments.filter(
                        academic_session=current_session,
                        enrollment_status='active'
                    ).count()
                    # Calculate subject count for the class
                    subject_count = current_class.subject_assignments.filter(
                        academic_session=current_session
                    ).values('subject').distinct().count()

                    # Add these to the class object for template access
                    current_class.student_count = student_count
                    current_class.subject_count = subject_count

                # Get today's attendance
                from django.utils import timezone
                today = timezone.now().date()
                today_attendance = None
                if current_session and current_enrollment:
                    from apps.attendance.models import DailyAttendance
                    today_attendance = DailyAttendance.objects.filter(
                        student=student,
                        date=today,
                        attendance_session__academic_session=current_session
                    ).first()

                # Get today's timetable
                today_timetable = []
                if current_enrollment and current_session:
                    from apps.academics.models import Timetable
                    today_weekday = timezone.now().strftime('%A').lower()
                    today_timetable = Timetable.objects.filter(
                        class_assigned=current_enrollment.class_enrolled,
                        academic_session=current_session,
                        day_of_week=today_weekday
                    ).select_related('subject', 'teacher').order_by('start_time')

                # Get recent announcements
                recent_announcements = []
                try:
                    from apps.communication.models import Announcement
                    recent_announcements = Announcement.objects.filter(
                        is_published=True,
                        published_at__isnull=False
                    ).order_by('-published_at')[:5]
                except:
                    pass

                # Get upcoming assignments
                upcoming_assignments = []
                if current_session:
                    try:
                        from apps.assessment.models import Assignment
                        from django.db.models import Q
                        upcoming_assignments = Assignment.objects.filter(
                            Q(academic_class=current_enrollment.class_enrolled) if current_enrollment else Q(),
                            academic_session=current_session,
                            due_date__gte=today,
                            is_active=True
                        ).select_related('subject', 'teacher').order_by('due_date')[:5]
                    except:
                        pass

                # Get performance stats
                performance_stats = {}
                if current_session:
                    try:
                        from apps.assessment.models import Mark
                        marks = Mark.objects.filter(
                            student=student,
                            exam__academic_session=current_session
                        )
                        if marks.exists():
                            total_marks = marks.count()
                            average_percentage = marks.aggregate(avg=models.Avg('percentage'))['avg'] or 0
                            passed_exams = marks.filter(percentage__gte=40).count()

                            performance_stats = {
                                'total_exams': total_marks,
                                'average_percentage': round(average_percentage, 1),
                                'passed_exams': passed_exams,
                                'pass_rate': round((passed_exams / total_marks * 100), 1) if total_marks > 0 else 0
                            }
                    except:
                        pass

                # Get recent grades
                recent_grades = []
                if current_session:
                    try:
                        from apps.assessment.models import Mark
                        recent_grades = Mark.objects.filter(
                            student=student,
                            exam__academic_session=current_session
                        ).select_related('exam', 'exam__subject').order_by('-exam__exam_date')[:6]
                    except:
                        pass

                # Get library status
                library_status = None
                try:
                    from apps.library.models import BookBorrow
                    current_borrows = BookBorrow.objects.filter(
                        student=student,
                        return_date__isnull=True,
                        due_date__gte=today
                    ).select_related('book')
                    max_borrows = 5  # You can make this configurable
                    can_borrow_more = len(current_borrows) < max_borrows

                    library_status = {
                        'current_borrows': list(current_borrows),
                        'can_borrow_more': can_borrow_more,
                        'max_borrows': max_borrows
                    }
                except ImportError:
                    # Library app might not be available
                    pass

                # Add all the context variables needed by the comprehensive dashboard
                context.update({
                    'student': student,
                    'current_session': current_session,
                    'current_enrollment': current_enrollment,
                    'today_timetable': today_timetable,
                    'recent_announcements': recent_announcements,
                    'upcoming_assignments': upcoming_assignments,
                    'today_attendance': today_attendance,
                    'performance_stats': performance_stats,
                    'recent_grades': recent_grades,
                    'library_status': library_status,
                    'today': today,
                })

            return render(request, 'users/dashboard/dashboard.html', context)
        else:
            logger.debug(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
    except Exception as e:
        logger.error(f"Error in user_dashboard for user {request.user.email}: {e}")
        # Fallback basic dashboard
        primary_role = request.user.user_roles.filter(is_primary=True).first()
        is_admin_staff = request.user.is_staff or (primary_role and primary_role.role.role_type in ['admin', 'principal', 'super_admin'])
        context = {
            'title': _('Dashboard'),
            'user': request.user,
            'primary_role': primary_role,
            'is_admin_staff': is_admin_staff,
        }
        return render(request, 'users/dashboard/dashboard.html', context)

@login_required
def profile_view(request):
    """
    User profile view and update.
    """
    user = request.user
    profile = user.profile

    # Get user's application data if it exists
    student_application = user.student_application.first()
    staff_application = user.staff_application.first()

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            # Log profile update
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ActionType.UPDATE,
                model_name='users.UserProfile',
                object_id=str(profile.id),
                ip_address=get_client_ip(request),
                details={'action': 'Profile updated'}
            )

            messages.success(request, _('Profile updated successfully!'))
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    # Determine status badge for application
    application_status_badge = 'secondary'
    application_status = None

    if student_application:
        application_status = student_application.get_application_status_display()
        if student_application.application_status == 'approved':
            application_status_badge = 'success'
        elif student_application.application_status in ['pending', 'under_review']:
            application_status_badge = 'warning'
        elif student_application.application_status == 'rejected':
            application_status_badge = 'danger'
        else:
            application_status_badge = 'secondary'
    elif staff_application:
        application_status = staff_application.get_application_status_display()
        if staff_application.application_status == 'approved':
            application_status_badge = 'success'
        elif staff_application.application_status in ['pending', 'under_review', 'interview_scheduled']:
            application_status_badge = 'warning'
        elif staff_application.application_status == 'rejected':
            application_status_badge = 'danger'
        else:
            application_status_badge = 'secondary'

    context = {
        'title': _('My Profile'),
        'user_form': user_form,
        'profile_form': profile_form,
        'active_tab': 'profile',
        'student_application': student_application,
        'staff_application': staff_application,
        'application_status_badge': application_status_badge,
    }
    return render(request, 'users/profile/profile.html', context)

@login_required
def password_change_view(request):
    """
    Custom password change view.
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log password change
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.UPDATE,
                model_name='users.User',
                object_id=str(request.user.id),
                ip_address=get_client_ip(request),
                details={'action': 'Password changed'}
            )
            
            messages.success(request, _('Password changed successfully!'))
            return redirect('users:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    context = {
        'title': _('Change Password'),
        'form': form,
        'active_tab': 'password',
    }
    return render(request, 'users/profile/password_change.html', context)

# =============================================================================
# ADMIN USER MANAGEMENT VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_list(request):
    """
    List all users with filtering and search capabilities.
    """
    users = User.objects.all().select_related('profile').prefetch_related('user_roles__role')
    
    # Filtering
    role_filter = request.GET.get('role')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')
    
    if role_filter:
        users = users.filter(user_roles__role__role_type=role_filter)
    
    if status_filter:
        users = users.filter(status=status_filter)
    
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(mobile__icontains=search_query)
        )
    
    context = {
        'title': _('User Management'),
        'users': users.distinct(),
        'roles': Role.objects.all(),
        'active_tab': 'users',
    }
    return render(request, 'users/admin/users/user_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_create(request):
    """
    Create new user (admin only).
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log user creation
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.CREATE,
                model_name='users.User',
                object_id=str(user.id),
                ip_address=get_client_ip(request),
                details={'action': 'User created by admin'}
            )
            
            messages.success(request, _('User created successfully!'))
            return redirect('users:user_list')
    else:
        form = UserCreationForm()
    
    context = {
        'title': _('Create User'),
        'form': form,
        'active_tab': 'users',
    }
    return render(request, 'users/admin/users/user_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_detail(request, user_id):
    """
    User detail view with all related information.
    """
    user = get_object_or_404(User, id=user_id)

    # Security check - staff can only view, superuser can edit
    can_edit = request.user.is_superuser

    # Get recent login history
    recent_logins = LoginHistory.objects.filter(user=user).order_by('-created_at')[:5]

    # Get user's application data if it exists
    student_application = user.student_application.first()
    staff_application = user.staff_application.first()

    # Determine status badge for application
    application_status_badge = 'secondary'
    if student_application:
        if student_application.application_status == 'approved':
            application_status_badge = 'success'
        elif student_application.application_status in ['pending', 'under_review']:
            application_status_badge = 'warning'
        elif student_application.application_status == 'rejected':
            application_status_badge = 'danger'
        else:
            application_status_badge = 'secondary'
    elif staff_application:
        if staff_application.application_status == 'approved':
            application_status_badge = 'success'
        elif staff_application.application_status in ['pending', 'under_review', 'interview_scheduled']:
            application_status_badge = 'warning'
        elif staff_application.application_status == 'rejected':
            application_status_badge = 'danger'
        else:
            application_status_badge = 'secondary'

    context = {
        'title': _('User Details'),
        'user_obj': user,
        'can_edit': can_edit,
        'active_tab': 'users',
        'recent_logins': recent_logins,
        'student_application': student_application,
        'staff_application': staff_application,
        'application_status_badge': application_status_badge,
    }
    return render(request, 'users/admin/users/user_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_update(request, user_id):
    """
    Update user information (superuser only).
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()

            # Log user update
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.UPDATE,
                model_name='users.User',
                object_id=str(user.id),
                ip_address=get_client_ip(request),
                details={'action': 'User updated by admin'}
            )

            messages.success(request, _('User updated successfully!'))
            return redirect('users:user_detail', user_id=user.id)
    else:
        form = UserUpdateForm(instance=user)

    context = {
        'title': _('Edit User'),
        'form': form,
        'user_obj': user,
        'active_tab': 'users',
    }
    return render(request, 'users/admin/users/user_form.html', context)

@login_required
@user_passes_test(can_assign_roles)
def user_roles_manage(request, user_id):
    """
    Manage user roles and assignments.
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST)
        if form.is_valid():
            user_role = form.save(commit=False)
            user_role.user = user

            # Set audit context
            user_role._audit_user = request.user
            user_role._audit_ip = get_client_ip(request)
            user_role._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')

            user_role.save()

            # Log the activity
            UserRoleActivity.log_activity(
                user=user,
                role=user_role.role,
                action_type=UserRoleActivity.ActionType.ASSIGNED,
                performed_by=request.user,
                academic_session=user_role.academic_session,
                details=f"Role assigned to user {user.display_name}"
            )

            messages.success(request, _('Role assigned successfully!'))
            return redirect('users:user_roles_manage', user_id=user.id)
    else:
        form = UserRoleAssignmentForm()

    # Get user roles
    user_roles = user.user_roles.all().select_related('role', 'academic_session')

    # Calculate effective permissions from active roles
    effective_permissions = set()
    for user_role in user_roles.filter(status='active'):
        permissions = user_role.role.permissions.all()
        effective_permissions.update(perm.codename for perm in permissions)
    effective_permissions = list(effective_permissions)

    # Get roles available for quick assignment
    quick_roles = Role.objects.filter(status='active', is_system_role=False)

    # Calculate role statistics
    primary_roles_count = user_roles.filter(is_primary=True).count()
    active_roles_count = user_roles.filter(status='active').count()
    inactive_roles_count = user_roles.filter(status='inactive').count()

    context = {
        'title': _('Manage User Roles'),
        'target_user': user,
        'form': form,
        'user_roles': user_roles,
        'effective_permissions': effective_permissions,
        'quick_roles': quick_roles,
        'primary_roles_count': primary_roles_count,
        'active_roles_count': active_roles_count,
        'inactive_roles_count': inactive_roles_count,
        'active_tab': 'users',
    }
    return render(request, 'users/admin/users/user_roles.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_role_set_primary(request, user_id):
    """
    Set a user role as primary.
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user_role_id = request.POST.get('user_role_id')
        try:
            user_role = get_object_or_404(UserRole, id=user_role_id, user=user)

            # Set audit context
            user_role._audit_user = request.user
            user_role._audit_ip = get_client_ip(request)
            user_role._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')

            user_role.is_primary = True
            user_role.save()

            # Log the activity
            UserRoleActivity.log_activity(
                user=user,
                role=user_role.role,
                action_type=UserRoleActivity.ActionType.SET_PRIMARY,
                performed_by=request.user,
                academic_session=user_role.academic_session,
                details=f"Set as primary role for user {user.display_name}"
            )

            messages.success(request, _('Role set as primary successfully!'))
        except Exception as e:
            logger.error(f"Error setting role as primary: {e}")
            messages.error(request, _('Error setting role as primary.'))

    return redirect('users:user_roles_manage', user_id=user.id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_role_set_secondary(request, user_id):
    """
    Set a user role as secondary.
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user_role_id = request.POST.get('user_role_id')
        try:
            user_role = get_object_or_404(UserRole, id=user_role_id, user=user)

            # Set audit context
            user_role._audit_user = request.user
            user_role._audit_ip = get_client_ip(request)
            user_role._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')

            user_role.is_primary = False
            user_role.save()

            # Log the activity
            UserRoleActivity.log_activity(
                user=user,
                role=user_role.role,
                action_type=UserRoleActivity.ActionType.SET_SECONDARY,
                performed_by=request.user,
                academic_session=user_role.academic_session,
                details=f"Set as secondary role for user {user.display_name}"
            )

            messages.success(request, _('Role set as secondary successfully!'))
        except Exception as e:
            logger.error(f"Error setting role as secondary: {e}")
            messages.error(request, _('Error setting role as secondary.'))

    return redirect('users:user_roles_manage', user_id=user.id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_role_remove(request, user_id):
    """
    Remove a role from a user.
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user_role_id = request.POST.get('user_role_id')
        try:
            user_role = get_object_or_404(UserRole, id=user_role_id, user=user)
            role_name = user_role.role.name

            # Set audit context
            user_role._audit_user = request.user
            user_role._audit_ip = get_client_ip(request)
            user_role._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Log the activity before deleting
            UserRoleActivity.log_activity(
                user=user,
                role=user_role.role,
                action_type=UserRoleActivity.ActionType.REMOVED,
                performed_by=request.user,
                academic_session=user_role.academic_session,
                details=f"Role removed from user {user.display_name}"
            )

            user_role.delete()

            # Check if request is AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Calculate updated statistics
                user_roles = user.user_roles.all()
                primary_roles_count = user_roles.filter(is_primary=True).count()
                active_roles_count = user_roles.filter(status='active').count()
                inactive_roles_count = user_roles.filter(status='inactive').count()

                # Calculate effective permissions
                effective_permissions = set()
                for ur in user_roles.filter(status='active'):
                    permissions = ur.role.permissions.all()
                    effective_permissions.update(perm.codename for perm in permissions)
                effective_permissions = list(effective_permissions)

                return JsonResponse({
                    'success': True,
                    'message': _('Role "{}" removed successfully!').format(role_name),
                    'statistics': {
                        'total': user_roles.count(),
                        'primary': primary_roles_count,
                        'active': active_roles_count,
                        'inactive': inactive_roles_count
                    },
                    'permissions': effective_permissions[:10],  # Limit for performance
                    'permissions_count': len(effective_permissions)
                })

            messages.success(request, _('Role "{}" removed successfully!').format(role_name))
        except Exception as e:
            logger.error(f"Error removing role: {e}")

            # Check if request is AJAX for error response
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': _('Error removing role.')
                }, status=400)

            messages.error(request, _('Error removing role.'))

    return redirect('users:user_roles_manage', user_id=user.id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_toggle_status(request, user_id):
    """
    Activate/Deactivate user account.
    """
    user = get_object_or_404(User, id=user_id)
    
    if user.status == 'active':
        user.status = 'inactive'
        action = 'deactivated'
    else:
        user.status = 'active'
        action = 'activated'
    
    user.save()
    
    # Log status change
    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.ActionType.UPDATE,
        model_name='users.User',
        object_id=str(user.id),
        ip_address=get_client_ip(request),
        details={'action': f'User {action}'}
    )
    
    messages.success(request, _(f'User {action} successfully!'))
    return redirect('users:user_detail', user_id=user.id)

# =============================================================================
# APPLICATION MANAGEMENT VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.approve_applications'))
def pending_applications(request):
    """
    View and manage pending applications.
    """
    student_applications = StudentApplication.objects.filter(
        application_status__in=['pending', 'under_review']
    ).select_related('academic_session').order_by('-application_date')
    
    staff_applications = StaffApplication.objects.filter(
        application_status__in=['pending', 'under_review']
    ).select_related('position_applied_for', 'academic_session').order_by('-application_date')
    
    context = {
        'title': _('Pending Applications'),
        'student_applications': student_applications,
        'staff_applications': staff_applications,
        'active_tab': 'applications',
    }
    return render(request, 'users/admin/applications/pending_applications.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.approve_applications'))
def approve_application(request, application_id, application_type):
    """
    Approve an application and create user account.
    Supports both AJAX and regular POST requests.
    """
    try:
        with transaction.atomic():
            logger.info(f"Starting approval process for {application_type} application {application_id}")

            if application_type == 'student':
                application = get_object_or_404(StudentApplication, id=application_id)
                logger.info(f"Found student application: {application}")
                user, temporary_password = create_user_from_student_application(application, request.user)

            elif application_type == 'staff':
                application = get_object_or_404(StaffApplication, id=application_id)
                logger.info(f"Found staff application: {application}")
                user, temporary_password = create_user_from_staff_application(application, request.user)

            else:
                error_msg = _('Invalid application type.')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('users:pending_applications')

            # Update application status
            application.application_status = 'approved'
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.user_account = user
            application.save()

            logger.info(f"Application approved successfully, user created: {user.email}")

            # Log approval
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.UPDATE,
                model_name=f'users.{application_type.capitalize()}Application',
                object_id=str(application.id),
                ip_address=get_client_ip(request),
                details={
                    'action': 'Application approved',
                    'application_number': application.application_number,
                    'user_created_id': str(user.id)
                }
            )

            # Send approval email
            send_approval_email(request, application, user, temporary_password)

            success_msg = _('Application approved and user account created!')

            # Handle AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_msg,
                    'application_id': str(application.id),
                    'user_email': user.email
                })

            messages.success(request, success_msg)

    except Exception as e:
        logger.error(f"Error approving application {application_id}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        error_msg = _('Error approving application. Please try again.')

        # Handle AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg}, status=500)

        messages.error(request, error_msg)

    return redirect('users:pending_applications')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.approve_applications'))
def reject_application(request, application_id, application_type):
    """
    Reject an application with reason.
    """
    if request.method == 'POST':
        review_notes = request.POST.get('review_notes', '')
        
        try:
            with transaction.atomic():
                if application_type == 'student':
                    application = get_object_or_404(StudentApplication, id=application_id)
                elif application_type == 'staff':
                    application = get_object_or_404(StaffApplication, id=application_id)
                else:
                    messages.error(request, _('Invalid application type.'))
                    return redirect('users:pending_applications')
                
                # Update application status
                application.application_status = 'rejected'
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_notes = review_notes
                application.save()
                
                # Log rejection
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.UPDATE,
                    model_name=f'users.{application_type.capitalize()}Application',
                    object_id=str(application.id),
                    ip_address=get_client_ip(request),
                    details={
                        'action': 'Application rejected',
                        'application_number': application.application_number,
                        'review_notes': review_notes[:100]  # First 100 chars
                    }
                )
                
                # Send rejection email
                send_rejection_email(application, review_notes)
                
                messages.success(request, _('Application rejected successfully.'))

        except Exception as e:
            logger.error(f"Error rejecting application {application_id}: {e}")
            messages.error(request, _('Error rejecting application. Please try again.'))

    return redirect('users:pending_applications')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.approve_applications'))
def mark_application_under_review(request, application_id, application_type):
    """
    Mark an application as 'under_review' with optional notes.
    """
    if request.method == 'POST':
        review_notes = request.POST.get('review_notes', '')
        
        try:
            with transaction.atomic():
                if application_type == 'student':
                    application = get_object_or_404(StudentApplication, id=application_id)
                elif application_type == 'staff':
                    application = get_object_or_404(StaffApplication, id=application_id)
                else:
                    messages.error(request, _('Invalid application type.'))
                    return redirect('users:pending_applications')
                
                # Update application status
                application.application_status = 'under_review'
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_notes = review_notes
                application.save()
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.UPDATE,
                    model_name=f'users.{application_type.capitalize()}Application',
                    object_id=str(application.id),
                    ip_address=get_client_ip(request),
                    details={
                        'action': 'Application marked under review',
                        'application_number': application.application_number,
                        'review_notes': review_notes[:100]  # First 100 chars
                    }
                )
                
                messages.success(request, _('Application marked as "Under Review" successfully.'))

        except Exception as e:
            logger.error(f"Error marking application {application_id} under review: {e}")
            messages.error(request, _('Error marking application under review. Please try again.'))

    return redirect('users:pending_applications')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.approve_applications'))
def schedule_interview(request, application_id):
    """
    Schedule interview for a staff application.
    """
    if request.method == 'POST':
        interview_date = request.POST.get('interview_date')
        review_notes = request.POST.get('review_notes', '')

        try:
            with transaction.atomic():
                application = get_object_or_404(StaffApplication, id=application_id)

                # Validate interview_date
                if not interview_date:
                    messages.error(request, _('Interview date is required.'))
                    return redirect('users:pending_applications')

                # Update application status and interview details
                application.application_status = StaffApplication.ApplicationStatus.INTERVIEW_SCHEDULED
                application.interview_date = interview_date
                application.review_notes = review_notes
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.save()

                # Log the interview scheduling
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.UPDATE,
                    model_name='users.StaffApplication',
                    object_id=str(application.id),
                    ip_address=get_client_ip(request),
                    details={
                        'action': 'Interview scheduled',
                        'application_number': application.application_number,
                        'interview_date': interview_date,
                        'review_notes': review_notes[:100]  # First 100 chars
                    }
                )

                # Send interview scheduling email
                send_interview_email(application, interview_date, review_notes)

                messages.success(request, _('Interview scheduled successfully.'))

        except Exception as e:
            logger.error(f"Error scheduling interview for application {application_id}: {e}")
            messages.error(request, _('Error scheduling interview. Please try again.'))

    return redirect('users:pending_applications')

# =============================================================================
# ROLE MANAGEMENT VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def role_list(request):
    """
    List all roles in the system.
    """
    roles = Role.objects.all().prefetch_related('permissions')

    # Calculate statistics
    system_roles_count = roles.filter(is_system_role=True).count()
    user_roles_count = roles.filter(is_system_role=False).count()

    # Get recent role activity
    from .models import UserRoleActivity
    recent_activities = UserRoleActivity.objects.select_related(
        'user', 'role', 'performed_by', 'academic_session'
    ).order_by('-created_at')[:15]

    context = {
        'title': _('Role Management'),
        'roles': roles,
        'system_roles_count': system_roles_count,
        'user_roles_count': user_roles_count,
        'recent_activities': recent_activities,
        'active_tab': 'roles',
    }
    return render(request, 'users/admin/roles/role_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def role_create(request):
    """
    Create new role or edit existing role.
    """
    role = None
    editing = False
    edit_id = request.GET.get('edit')

    if edit_id:
        try:
            role = Role.objects.get(id=edit_id)
            editing = True
        except Role.DoesNotExist:
            messages.error(request, _('Role not found.'))
            return redirect('users:role_list')

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            saved_role = form.save()
            action = AuditLog.ActionType.UPDATE if role else AuditLog.ActionType.CREATE
            message_key = _('Role updated successfully!') if role else _('Role created successfully!')

            # Log role creation/update
            AuditLog.objects.create(
                user=request.user,
                action=action,
                model_name='users.Role',
                object_id=str(saved_role.id),
                ip_address=get_client_ip(request)
            )

            messages.success(request, message_key)
            return redirect('users:role_list')
    else:
        form = RoleForm(instance=role)

    context = {
        'title': _('Edit Role') if role else _('Create Role'),
        'form': form,
        'role': role,
        'role_permissions': list(role.permissions.values_list('codename', flat=True)) if role else [],
        'active_tab': 'roles',
    }
    return render(request, 'users/admin/roles/role_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def role_delete(request, role_id):
    """
    Delete a role (superuser only).
    """
    role = get_object_or_404(Role, id=role_id)

    # Prevent deletion of system roles
    if role.is_system_role:
        messages.error(request, _('System roles cannot be deleted.'))
        return redirect('users:role_list')

    # Check if role has users assigned
    user_count = UserRole.objects.filter(role=role).count()
    if user_count > 0:
        messages.error(request, _('Cannot delete role because it is assigned to {} user(s). Please remove the role from all users first.').format(user_count))
        return redirect('users:role_list')

    if request.method == 'POST':
        try:
            role_name = role.name
            role.delete()

            # Log role deletion
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.DELETE,
                model_name='users.Role',
                object_id=role_id,
                ip_address=get_client_ip(request),
                details={'action': 'Role deleted', 'role_name': role_name}
            )

            messages.success(request, _('Role deleted successfully!'))
        except Exception as e:
            logger.error(f"Error deleting role {role_id}: {e}")
            messages.error(request, _('Error deleting role. Please try again.'))

    return redirect('users:role_list')

# =============================================================================
# PARENT-STUDENT RELATIONSHIP VIEWS
# =============================================================================

@login_required
def parent_student_relationships(request):
    """
    View and manage parent-student relationships.
    """
    if request.user.user_roles.filter(role__role_type='parent').exists():
        # Parent view - show their children
        relationships = ParentStudentRelationship.objects.filter(parent=request.user)
    elif request.user.user_roles.filter(role__role_type='student').exists():
        # Student view - show their parents
        relationships = ParentStudentRelationship.objects.filter(student=request.user)
    else:
        # Admin/staff view - show all relationships
        relationships = ParentStudentRelationship.objects.all()

    context = {
        'title': _('Parent-Student Relationships'),
        'relationships': relationships.select_related('parent', 'student'),
        'active_tab': 'relationships',
    }
    return render(request, 'users/relationships/parent_student_relationships.html', context)


# =============================================================================
# PARENT PORTAL VIEWS
# =============================================================================

class ParentRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a parent."""

    def test_func(self):
        return self.request.user.user_roles.filter(role__role_type='parent').exists()

    def handle_no_permission(self):
        messages.error(self.request, _("You don't have permission to access this page."))
        return redirect('users:dashboard')


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='parent').exists(), login_url=reverse_lazy('users:dashboard'))
def parent_dashboard(request):
    """
    Parent dashboard showing overview of all children.
    """
    # Get all children linked to this parent
    children_relationships = ParentStudentRelationship.objects.filter(
        parent=request.user,
        status='active'
    ).select_related('student__user', 'student__student_profile')

    children = []
    for relationship in children_relationships:
        child = relationship.student

        # Get current class enrollment
        current_enrollment = child.enrollments.filter(
            academic_session__is_current=True,
            enrollment_status='active'
        ).select_related('class_enrolled').first()

        # Get current attendance percentage
        current_session = AcademicSession.objects.filter(is_current=True).first()
        attendance_percentage = None
        if current_session:
            from apps.attendance.models import AttendanceSummary
            try:
                attendance_summary = AttendanceSummary.objects.get(
                    student=child,
                    academic_session=current_session,
                    month=timezone.now().month,
                    year=timezone.now().year
                )
                attendance_percentage = attendance_summary.attendance_percentage
            except AttendanceSummary.DoesNotExist:
                # Calculate from daily attendance if summary doesn't exist
                from apps.attendance.models import DailyAttendance
                from django.db.models import Q
                current_month_attendance = DailyAttendance.objects.filter(
                    student=child,
                    date__year=timezone.now().year,
                    date__month=timezone.now().month,
                    attendance_session__academic_session=current_session
                )
                if current_month_attendance.exists():
                    total_days = current_month_attendance.count()
                    present_days = current_month_attendance.filter(
                        Q(status='present') | Q(status='late') | Q(status='half_day')
                    ).count()
                    if total_days > 0:
                        attendance_percentage = round((present_days / total_days) * 100, 1)

        # Get latest grade from results
        latest_result = None
        latest_grade = None
        from apps.assessment.models import Result
        try:
            latest_result = Result.objects.filter(
                student=child,
                academic_class__academic_session__is_current=True
            ).select_related('grade').order_by('-created_at').first()
            if latest_result and latest_result.grade:
                latest_grade = latest_result.grade.grade
        except:
            pass

        # Get pending fees
        pending_fees = 0
        if current_session:
            from apps.finance.models import Invoice
            pending_invoices = Invoice.objects.filter(
                student=child,
                academic_session=current_session,
                status__in=['issued', 'partial', 'overdue']
            )
            pending_fees = sum(float(invoice.balance_due) for invoice in pending_invoices)

    # Get recent notifications for this child
        from apps.communication.models import RealTimeNotification
        child_notifications = RealTimeNotification.objects.filter(
            recipient=request.user,
            content_type__model='student',
            object_id=str(child.id)
        ).order_by('-created_at')[:3]

        children.append({
            'student': child,
            'relationship': relationship,
            'current_class': current_enrollment.class_enrolled if current_enrollment else None,
            'current_attendance_percentage': attendance_percentage,
            'latest_grade': latest_grade,
            'pending_fees': pending_fees,
            'recent_notifications': child_notifications,
        })

    # Get recent general notifications for parent
    from apps.communication.models import RealTimeNotification
    recent_notifications = RealTimeNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]

    # Get unread notification count
    unread_count = RealTimeNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    context = {
        'title': _('Parent Dashboard'),
        'children': children,
        'recent_notifications': recent_notifications,
        'unread_count': unread_count,
    }
    return render(request, 'users/dashboard/parent_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='parent').exists(), login_url=reverse_lazy('users:dashboard'))
def child_academic_records(request, child_id):
    """
    View child's academic records.
    """
    # Verify parent has access to this child
    try:
        relationship = ParentStudentRelationship.objects.get(
            parent=request.user,
            student_id=child_id,
            status='active'
        )
        child = relationship.student
    except ParentStudentRelationship.DoesNotExist:
        messages.error(request, _("You don't have permission to view this child's records."))
        return redirect('users:dashboard')

    # Get academic records (same logic as student view)
    academic_records = AcademicRecord.objects.filter(
        student=child
    ).select_related('class_enrolled', 'academic_session').order_by('-academic_session__start_date')

    # Get detailed marks
    from apps.assessment.models import Mark, Result, ResultSubject
    marks = Mark.objects.filter(
        student=child
    ).select_related('exam', 'exam__subject', 'exam__exam_type').order_by('-exam__exam_date')

    # Subject-wise performance analysis
    subject_performance = {}
    for mark in marks:
        subject_name = mark.exam.subject.name
        if subject_name not in subject_performance:
            subject_performance[subject_name] = {
                'marks': [],
                'exams': 0,
                'average': 0,
                'highest': 0,
                'lowest': 100,
                'trend': []
            }

        subject_performance[subject_name]['marks'].append(mark.percentage)
        subject_performance[subject_name]['exams'] += 1

        if mark.percentage > subject_performance[subject_name]['highest']:
            subject_performance[subject_name]['highest'] = mark.percentage
        if mark.percentage < subject_performance[subject_name]['lowest']:
            subject_performance[subject_name]['lowest'] = mark.percentage

    # Calculate averages
    for subject_name, data in subject_performance.items():
        if data['marks']:
            data['average'] = sum(data['marks']) / len(data['marks'])

    # Results and report cards
    results = Result.objects.filter(
        student=child
    ).select_related('academic_class', 'exam_type', 'grade').prefetch_related('subject_marks')

    # Attendance summary
    attendance_summary = None
    current_session = AcademicSession.objects.filter(is_current=True).first()
    if current_session:
        from apps.attendance.models import DailyAttendance
        attendance_records = DailyAttendance.objects.filter(
            student=child,
            academic_session=current_session
        )

        total_days = attendance_records.count()
        if total_days > 0:
            present_days = attendance_records.filter(attendance_status='present').count()
            attendance_percentage = (present_days / total_days) * 100

            attendance_summary = {
                'total_days': total_days,
                'present_days': present_days,
                'attendance_percentage': round(attendance_percentage, 1),
                'current_session': current_session
            }

    context = {
        'child': child,
        'academic_records': academic_records,
        'subject_performance': subject_performance,
        'marks': marks[:20],  # Recent marks
        'results': results,
        'attendance_summary': attendance_summary,
        'total_exams': marks.count(),
        'average_percentage': marks.aggregate(avg=models.Avg('percentage'))['avg'] if marks else 0,
    }

    return render(request, 'users/parent/child_records.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='parent').exists(), login_url=reverse_lazy('users:dashboard'))
def child_attendance(request, child_id):
    """
    View child's attendance records.
    """
    # Verify parent has access to this child
    try:
        relationship = ParentStudentRelationship.objects.get(
            parent=request.user,
            student_id=child_id,
            status='active'
        )
        child = relationship.student
    except ParentStudentRelationship.DoesNotExist:
        messages.error(request, _("You don't have permission to view this child's attendance."))
        return redirect('users:dashboard')

    # Get attendance data
    current_session = AcademicSession.objects.filter(is_current=True).first()

    from apps.attendance.models import DailyAttendance, AttendanceSummary

    # Current session attendance
    attendance_records = DailyAttendance.objects.filter(
        student=child,
        academic_session=current_session
    ).order_by('-date') if current_session else []

    # Monthly summaries
    monthly_summaries = AttendanceSummary.objects.filter(
        student=child
    ).order_by('-year', '-month')[:12]

    # Calculate current month stats
    current_month = timezone.now().month
    current_year = timezone.now().year

    current_month_summary = AttendanceSummary.objects.filter(
        student=child,
        month=current_month,
        year=current_year
    ).first()

    context = {
        'child': child,
        'attendance_records': attendance_records[:30],  # Last 30 days
        'monthly_summaries': monthly_summaries,
        'current_month_summary': current_month_summary,
        'current_session': current_session,
    }

    return render(request, 'users/parent/child_attendance.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='parent').exists(), login_url=reverse_lazy('users:dashboard'))
def child_fee_status(request, child_id):
    """
    View child's fee status and payment history.
    """
    # Verify parent has access to this child
    try:
        relationship = ParentStudentRelationship.objects.get(
            parent=request.user,
            student_id=child_id,
            status='active'
        )
        child = relationship.student
    except ParentStudentRelationship.DoesNotExist:
        messages.error(request, _("You don't have permission to view this child's fee information."))
        return redirect('users:dashboard')

    from apps.finance.models import Invoice, Payment

    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get invoices for current session
    invoices = Invoice.objects.filter(
        student=child,
        academic_session=current_session
    ).order_by('-issue_date') if current_session else []

    # Get payment history
    payments = Payment.objects.filter(
        student=child
    ).select_related('invoice').order_by('-payment_date')[:10]

    # Calculate totals
    total_invoiced = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(invoice.amount_paid for invoice in invoices)
    total_pending = sum(invoice.balance_due for invoice in invoices)

    context = {
        'child': child,
        'invoices': invoices,
        'payments': payments,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'current_session': current_session,
    }

    return render(request, 'users/parent/child_fees.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='parent').exists(), login_url=reverse_lazy('users:dashboard'))
def message_teacher(request, teacher_id=None):
    """
    Allow parents to message teachers about their children.
    """
    from apps.communication.models import Message
    from apps.communication.forms import MessageForm

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.message_type = 'direct'
            message.save()

            # Add recipients
            teacher_user = form.cleaned_data['teacher']
            message.recipients.add(teacher_user)

            messages.success(request, _('Message sent successfully!'))
            return redirect('communication:inbox')
    else:
        initial = {}
        if teacher_id:
            # Pre-select teacher if provided
            try:
                from apps.academics.models import Teacher
                teacher = Teacher.objects.get(id=teacher_id)
                initial['recipients'] = [teacher.user]
            except Teacher.DoesNotExist:
                pass

        form = MessageForm(initial=initial)

    # Get list of teachers for the parent's children
    children_relationships = ParentStudentRelationship.objects.filter(
        parent=request.user,
        status='active'
    ).select_related('student')

    teacher_ids = set()
    for relationship in children_relationships:
        # Get teachers for this child's classes
        child = relationship.student
        current_enrollment = child.enrollments.filter(
            academic_session__is_current=True
        ).first()

        if current_enrollment:
            # Get subject assignments for this class
            subject_assignments = current_enrollment.class_enrolled.subject_assignments.filter(
                academic_session__is_current=True
            ).select_related('teacher')

            for assignment in subject_assignments:
                teacher_ids.add(assignment.teacher.id)

    teachers = []
    if teacher_ids:
        from apps.academics.models import Teacher
        teachers = Teacher.objects.filter(
            id__in=teacher_ids,
            status='active'
        ).select_related('user', 'department')

    context = {
        'title': _('Message Teacher'),
        'form': form,
        'teachers': teachers,
    }

    return render(request, 'users/parent/message_teacher.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.manage_relationships'))
def parent_student_relationship_create(request):
    """
    Create new parent-student relationship.
    """
    if request.method == 'POST':
        form = ParentStudentRelationshipForm(request.POST)
        if form.is_valid():
            relationship = form.save()
            
            messages.success(request, _('Relationship created successfully!'))
            return redirect('users:parent_student_relationships')
    else:
        form = ParentStudentRelationshipForm()
    
    context = {
        'title': _('Create Relationship'),
        'form': form,
        'active_tab': 'relationships',
    }
    return render(request, 'users/parent_student_relationship_form.html', context)

# =============================================================================
# BULK OPERATIONS
# =============================================================================

@login_required
@user_passes_test(can_assign_roles)
def user_bulk_action(request):
    """
    Perform bulk actions on users.
    """
    if request.method == 'POST':
        form = UserBulkActionForm(request.POST)
        if form.is_valid():
            users = form.cleaned_data['users']
            action = form.cleaned_data['action']

            try:
                with transaction.atomic():
                    if action == 'activate':
                        users.update(status='active')
                        message = _('Users activated successfully!')
                    elif action == 'deactivate':
                        users.update(status='inactive')
                        message = _('Users deactivated successfully!')
                    elif action == 'assign_role':
                        role = form.cleaned_data['role']

                        # Validate permission to assign this specific role
                        if not _can_assign_specific_role(request.user, role):
                            messages.error(request, _('You do not have permission to assign the selected role.'))
                            return redirect('users:user_list')

                        # Get current academic session for role assignment
                        current_session = AcademicSession.objects.filter(is_current=True).first()

                        for user in users:
                            # Check if user already has this role to avoid duplicates
                            existing_role = UserRole.objects.filter(
                                user=user,
                                role=role,
                                academic_session=current_session
                            ).first()

                            if not existing_role:
                                UserRole.objects.create(
                                    user=user,
                                    role=role,
                                    is_primary=False,  # Bulk assignments are not primary by default
                                    academic_session=current_session
                                )

                                # Log individual role assignment
                                UserRoleActivity.log_activity(
                                    user=user,
                                    role=role,
                                    action_type=UserRoleActivity.ActionType.ASSIGNED,
                                    performed_by=request.user,
                                    academic_session=current_session,
                                    details=f"Role assigned via bulk action"
                                )

                        message = _('Role assigned to users successfully!')

                    # Log bulk action
                    AuditLog.objects.create(
                        user=request.user,
                        action=AuditLog.ActionType.UPDATE,
                        model_name='users.User',
                        object_id='bulk',
                        ip_address=get_client_ip(request),
                        details={'action': f'Bulk {action}', 'count': len(users)}
                    )

                    messages.success(request, message)

            except Exception as e:
                logger.error(f"Error performing bulk action: {e}")
                messages.error(request, _('Error performing bulk action.'))

            return redirect('users:user_list')
    else:
        form = UserBulkActionForm()

    context = {
        'title': _('Bulk User Actions'),
        'form': form,
    }
    return render(request, 'users/admin/users/user_bulk_action.html', context)


def _can_assign_specific_role(user, target_role):
    """
    Check if user can assign a specific role based on hierarchy.
    Super admins can assign any role.
    School admins can assign roles below their level.
    """
    if user.is_superuser:
        return True

    # Get user's highest role level
    user_roles = user.user_roles.filter(status='active').select_related('role')
    if not user_roles:
        return False

    user_max_level = max(role.role.hierarchy_level for role in user_roles)

    # User can only assign roles with lower or equal hierarchy level
    # But school admins (admin/principal) can assign most staff roles
    admin_role_types = ['admin', 'principal']
    user_is_admin = any(role.role.role_type in admin_role_types for role in user_roles)

    if user_is_admin:
        # Admins can assign most roles except super_admin
        return target_role.role_type != 'super_admin'
    else:
        # Non-admin users can only assign roles at or below their level
        return target_role.hierarchy_level <= user_max_level

# =============================================================================
# API & AJAX VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def test_email_configuration(request):
    """
    Test email configuration by sending a test email.
    """
    if request.method == 'POST':
        test_email = request.POST.get('test_email', '').strip()

        if not test_email:
            messages.error(request, _('Please provide a test email address.'))
            return redirect('users:test_email_configuration')

        try:
            subject = _('Test Email - {}').format(getattr(settings, 'SCHOOL_NAME', 'School Management System'))
            message = _('This is a test email to verify that the email configuration is working correctly.')

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [test_email],
                fail_silently=False,
            )

            messages.success(request, _('Test email sent successfully to {}').format(test_email))
            logger.info(f"Test email sent successfully to {test_email}")

        except Exception as e:
            messages.error(request, _('Failed to send test email: {}').format(str(e)))
            logger.error(f"Failed to send test email to {test_email}: {e}")

        return redirect('users:test_email_configuration')

    context = {
        'title': _('Test Email Configuration'),
        'active_tab': 'settings',
    }
    return render(request, 'users/admin/test_email.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_bulk_import(request):
    """
    Bulk import users from CSV/Excel file.
    """
    if request.method == 'POST':
        form = UserImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            send_welcome_email = form.cleaned_data['send_welcome_email']
            generate_passwords = form.cleaned_data['generate_passwords']

            try:
                # Process the uploaded file
                import_results = process_bulk_import(
                    csv_file,
                    send_welcome_email,
                    generate_passwords,
                    request.user
                )

                # Log the bulk import action
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.IMPORT,
                    model_name='users.User',
                    object_id='bulk_import',
                    ip_address=get_client_ip(request),
                    details={
                        'action': 'Bulk user import',
                        'total_processed': import_results['total_processed'],
                        'successful': import_results['successful'],
                        'failed': import_results['failed']
                    }
                )

                # Store results in session for display
                request.session['import_results'] = import_results

                messages.success(
                    request,
                    _('Bulk import completed! {} users processed, {} successful, {} failed.').format(
                        import_results['total_processed'],
                        import_results['successful'],
                        import_results['failed']
                    )
                )

                return redirect('users:user_bulk_import')

            except Exception as e:
                logger.error(f"Error during bulk import: {e}")
                messages.error(request, _('Error processing file. Please check the format and try again.'))

    else:
        form = UserImportForm()

    # Get import results from session if available
    import_results = request.session.pop('import_results', None)

    context = {
        'title': _('Bulk User Import'),
        'form': form,
        'import_results': import_results,
        'active_tab': 'users',
    }
    return render(request, 'users/admin/users/user_bulk_import.html', context)

# =============================================================================
# STAFF MANAGEMENT VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def staff_list(request):
    """
    List all staff members with filtering and search capabilities.
    Staff members are users with any role other than 'student' or 'parent'.
    """
    staff_roles = Role.objects.exclude(role_type__in=['student', 'parent']).values_list('id', flat=True)
    staff_users = User.objects.filter(
        user_roles__role__id__in=staff_roles,
        is_active=True
    ).distinct().select_related('profile').prefetch_related('user_roles__role')

    # Filtering
    role_filter = request.GET.get('role')
    search_query = request.GET.get('q')

    if role_filter:
        staff_users = staff_users.filter(user_roles__role__role_type=role_filter)

    if search_query:
        staff_users = staff_users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(profile__employee_id__icontains=search_query)
        )

    context = {
        'title': _('Staff Management'),
        'staff_members': staff_users,
        'roles': Role.objects.exclude(role_type__in=['student', 'parent']),
        'active_tab': 'staff',
    }
    return render(request, 'users/admin/staff/staff_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def staff_detail(request, user_id):
    """
    Staff member detail view with profile and role management.
    """
    staff_member = get_object_or_404(User, id=user_id)

    # Ensure the user is actually a staff member
    if not staff_member.user_roles.filter(role__role_type__in=Role.STAFF_ROLES).exists():
        messages.error(request, _("The requested user is not a staff member."))
        return redirect('users:staff_list')

    profile = staff_member.profile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=staff_member)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.UPDATE,
                model_name='users.UserProfile',
                object_id=str(profile.id),
                ip_address=get_client_ip(request),
                details={'action': 'Staff profile updated'}
            )

            messages.success(request, _('Staff profile updated successfully!'))
            return redirect('users:staff_detail', user_id=staff_member.id)
    else:
        user_form = UserUpdateForm(instance=staff_member)
        profile_form = UserProfileForm(instance=profile)

    # Get user roles
    user_roles = staff_member.user_roles.all().select_related('role', 'academic_session')

    context = {
        'title': _('Staff Details'),
        'staff_member': staff_member,
        'user_form': user_form,
        'profile_form': profile_form,
        'user_roles': user_roles,
        'active_tab': 'staff',
    }
    return render(request, 'users/admin/staff/staff_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('users.view_studentapplication') or u.has_perm('users.view_staffapplication'))
def export_applications(request, application_type):
    """
    Export student or staff applications to CSV or Excel.
    """
    format = request.GET.get('format', 'csv')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')

    if application_type == 'student':
        queryset = StudentApplication.objects.all().select_related('academic_session')
        filename_prefix = 'student_applications'
        fields = [
            'application_number', 'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'gender', 'nationality', 'address', 'city', 'state',
            'postal_code', 'country', 'grade_applying_for', 'previous_school',
            'previous_grade', 'academic_achievements', 'parent_first_name',
            'parent_last_name', 'parent_email', 'parent_phone', 'parent_relationship',
            'application_status', 'academic_session__name', 'application_date',
            'reviewed_by__email', 'reviewed_at', 'review_notes', 'user_account__email'
        ]
        field_titles = [
            _('Application Number'), _('First Name'), _('Last Name'), _('Email'), _('Phone'),
            _('Date of Birth'), _('Gender'), _('Nationality'), _('Address'), _('City'), _('State'),
            _('Postal Code'), _('Country'), _('Grade Applying For'), _('Previous School'),
            _('Previous Grade'), _('Academic Achievements'), _('Parent First Name'),
            _('Parent Last Name'), _('Parent Email'), _('Parent Phone'), _('Parent Relationship'),
            _('Application Status'), _('Academic Session'), _('Application Date'),
            _('Reviewed By'), _('Reviewed At'), _('Review Notes'), _('User Account')
        ]
    elif application_type == 'staff':
        queryset = StaffApplication.objects.all().select_related('position_applied_for', 'academic_session')
        filename_prefix = 'staff_applications'
        fields = [
            'application_number', 'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'gender', 'nationality', 'address', 'city', 'state',
            'postal_code', 'country', 'position_applied_for__name', 'position_type',
            'expected_salary', 'highest_qualification', 'institution', 'year_graduated',
            'years_of_experience', 'previous_employer', 'previous_position',
            'reference1_name', 'reference1_position', 'reference1_contact',
            'reference2_name', 'reference2_position', 'reference2_contact',
            'application_status', 'academic_session__name', 'application_date',
            'reviewed_by__email', 'reviewed_at', 'review_notes', 'interview_date',
            'user_account__email'
        ]
        field_titles = [
            _('Application Number'), _('First Name'), _('Last Name'), _('Email'), _('Phone'),
            _('Date of Birth'), _('Gender'), _('Nationality'), _('Address'), _('City'), _('State'),
            _('Postal Code'), _('Country'), _('Position Applied For'), _('Position Type'),
            _('Expected Salary'), _('Highest Qualification'), _('Institution'), _('Year Graduated'),
            _('Years of Experience'), _('Previous Employer'), _('Previous Position'),
            _('Reference 1 Name'), _('Reference 1 Position'), _('Reference 1 Contact'),
            _('Reference 2 Name'), _('Reference 2 Position'), _('Reference 2 Contact'),
            _('Application Status'), _('Academic Session'), _('Application Date'),
            _('Reviewed By'), _('Reviewed At'), _('Review Notes'), _('Interview Date'),
            _('User Account')
        ]
    else:
        messages.error(request, _('Invalid application type for export.'))
        return redirect('users:pending_applications')

    # Apply filters
    if status_filter != 'all':
        queryset = queryset.filter(application_status=status_filter)
    if search_query:
        queryset = queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(application_number__icontains=search_query)
        )

    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(field_titles)
        for obj in queryset:
            row = []
            for field_name in fields:
                # Handle related fields
                if '__' in field_name:
                    parts = field_name.split('__')
                    value = obj
                    for part in parts:
                        if value is None:
                            break
                        value = getattr(value, part, None)
                else:
                    value = getattr(obj, field_name, None)
                
                # Format specific fields
                if isinstance(value, timezone.datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, timezone.date):
                    value = value.strftime('%Y-%m-%d')
                elif value is None:
                    value = ''
                row.append(str(value))
            writer.writerow(row)
        return response

    elif format == 'excel':
        output = BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = filename_prefix.replace('_', ' ').title()

        sheet.append(field_titles)

        for obj in queryset:
            row = []
            for field_name in fields:
                if '__' in field_name:
                    parts = field_name.split('__')
                    value = obj
                    for part in parts:
                        if value is None:
                            break
                        value = getattr(value, part, None)
                else:
                    value = getattr(obj, field_name, None)
                
                if isinstance(value, timezone.datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, timezone.date):
                    value = value.strftime('%Y-%m-%d')
                elif value is None:
                    value = ''
                row.append(str(value))
            sheet.append(row)

        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        return response
    
    messages.error(request, _('Invalid export format.'))
    return redirect('users:pending_applications')


@login_required
def get_user_suggestions(request):
    """
    AJAX view for user search suggestions.
    """
    query = request.GET.get('q', '')
    role_type = request.GET.get('role_type', '')

    users = User.objects.filter(
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).filter(is_active=True)

    if role_type:
        users = users.filter(user_roles__role__role_type=role_type)

    suggestions = [
        {
            'id': user.id,
            'text': f"{user.get_full_name()} ({user.email})"
        }
        for user in users[:10]
    ]

    return JsonResponse({'results': suggestions})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def get_application_counts(request):
    """
    AJAX view to get current counts of pending student and staff applications.
    """
    student_count = StudentApplication.objects.filter(
        application_status__in=['pending', 'under_review']
    ).count()
    staff_count = StaffApplication.objects.filter(
        application_status__in=['pending', 'under_review']
    ).count()
    
    return JsonResponse({
        'student_count': student_count,
        'staff_count': staff_count
    })


@login_required
def check_email_availability(request):
    """
    AJAX view to check if email is available.
    """
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id')

    users = User.objects.filter(email=email)
    if user_id:
        users = users.exclude(id=user_id)

    available = not users.exists()

    return JsonResponse({'available': available})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def get_user_roles_ajax(request, user_id):
    """
    AJAX view to get a user's roles and primary role status.
    """
    user = get_object_or_404(User, id=user_id)
    user_roles = user.user_roles.all().select_related('role')
    
    roles_data = []
    for user_role in user_roles:
        roles_data.append({
            'id': str(user_role.id),
            'role_name': user_role.role.name,
            'role_type': user_role.role.role_type,
            'is_primary': user_role.is_primary,
            'status': user_role.status,
            'academic_session': user_role.academic_session.name if user_role.academic_session else None,
            'context_id': user_role.context_id,
        })
    
    primary_roles = [role for role in roles_data if role['is_primary']]
    
    return JsonResponse({
        'user_id': str(user.id),
        'roles': roles_data,
        'primary_roles': primary_roles,
        'display_name': user.display_name,
        'initials': user.get_initials(),
        'profile_picture_url': user.profile.profile_picture.url if user.profile.profile_picture else None,
    })


@login_required
def upload_profile_picture(request):
    """
    AJAX view to handle profile picture upload.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    user = request.user

    # Check if profile_picture is in request.FILES
    if 'profile_picture' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'No file uploaded'})

    profile_picture = request.FILES['profile_picture']

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if profile_picture.content_type not in allowed_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'
        })

    # Validate file size (5MB limit)
    max_size = 5 * 1024 * 1024
    if profile_picture.size > max_size:
        return JsonResponse({
            'success': False,
            'message': 'File too large. Maximum size is 5MB.'
        })

    try:
        # Update user's profile picture
        profile = user.profile
        profile.profile_picture = profile_picture
        profile.save()

        # Log the profile picture update
        AuditLog.objects.create(
            user=user,
            action=AuditLog.ActionType.UPDATE,
            model_name='users.UserProfile',
            object_id=str(profile.id),
            ip_address=get_client_ip(request),
            details={'action': 'Profile picture updated'}
        )

        # Trigger guardian notifications if user is a student
        if user.user_roles.filter(role__role_type='student').exists():
            guardians = get_student_guardians(user)
            if guardians:
                notify_guardians_profile_update(user, guardians, ['profile_picture'])

        return JsonResponse({
            'success': True,
            'message': 'Profile picture updated successfully!',
            'picture_url': profile.profile_picture.url if profile.profile_picture else None
        })

    except Exception as e:
        logger.error(f"Error uploading profile picture for user {user.id}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while uploading the picture. Please try again.'
        }, status=500)

# =============================================================================
# BULK IMPORT UTILITIES
# =============================================================================

def process_bulk_import(csv_file, send_welcome_email, generate_passwords, performed_by):
    """
    Process bulk user import from CSV/Excel file.
    Returns a dictionary with import results.
    """
    import pandas as pd
    from io import BytesIO

    results = {
        'total_processed': 0,
        'successful': 0,
        'failed': 0,
        'errors': [],
        'created_users': []
    }

    try:
        # Read the file
        if csv_file.name.endswith('.csv'):
            df = pd.read_csv(csv_file)
        elif csv_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(csv_file)
        else:
            raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

        # Normalize column names (convert to lowercase and replace spaces with underscores)
        df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')

        # Required columns
        required_columns = ['email', 'first_name', 'last_name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Process each row
        for index, row in df.iterrows():
            results['total_processed'] += 1

            try:
                with transaction.atomic():
                    # Extract user data
                    email = str(row.get('email', '')).strip()
                    first_name = str(row.get('first_name', '')).strip()
                    last_name = str(row.get('last_name', '')).strip()
                    mobile = str(row.get('mobile', '')).strip() if pd.notna(row.get('mobile')) else ''
                    role_type = str(row.get('role', 'student')).strip().lower()

                    # Validate required fields
                    if not email or not first_name or not last_name:
                        raise ValueError("Email, first name, and last name are required")

                    # Check if user already exists
                    if User.objects.filter(email=email).exists():
                        raise ValueError(f"User with email {email} already exists")

                    # Generate password
                    if generate_passwords:
                        password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(12))
                    else:
                        password = 'changeme123'  # Default password

                    # Create user
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        mobile=mobile if mobile else None,
                        is_active=True,
                        is_verified=True
                    )

                    # Update profile with additional data
                    profile = user.profile
                    if pd.notna(row.get('date_of_birth')):
                        profile.date_of_birth = row.get('date_of_birth')
                    if pd.notna(row.get('gender')):
                        profile.gender = str(row.get('gender')).strip().lower()
                    if pd.notna(row.get('nationality')):
                        profile.nationality = str(row.get('nationality')).strip()
                    if pd.notna(row.get('address')):
                        profile.address_line_1 = str(row.get('address')).strip()
                    if pd.notna(row.get('city')):
                        profile.city = str(row.get('city')).strip()
                    if pd.notna(row.get('state')):
                        profile.state = str(row.get('state')).strip()
                    if pd.notna(row.get('postal_code')):
                        profile.postal_code = str(row.get('postal_code')).strip()
                    if pd.notna(row.get('country')):
                        profile.country = str(row.get('country')).strip()
                    profile.save()

                    # Assign role
                    role = Role.objects.filter(role_type=role_type, status='active').first()
                    if not role:
                        # Try to find by name or create default student role
                        if role_type == 'student':
                            role = Role.objects.filter(role_type='student').first()
                            if not role:
                                role = Role.objects.create(
                                    name='Student',
                                    role_type='student',
                                    description='Student role',
                                    hierarchy_level=10,
                                    is_system_role=True,
                                    status='active'
                                )
                        else:
                            raise ValueError(f"Invalid role type: {role_type}")

                    # Get current academic session
                    current_session = AcademicSession.objects.filter(is_current=True).first()

                    UserRole.objects.create(
                        user=user,
                        role=role,
                        is_primary=True,
                        academic_session=current_session
                    )

                    # Set staff permissions if needed
                    if role.role_type in ['admin', 'principal', 'teacher']:
                        user.is_staff = True
                        user.save()

                    # Send welcome email if requested
                    if send_welcome_email:
                        try:
                            subject = _('Welcome to {}').format(getattr(settings, 'SCHOOL_NAME', 'Our School'))
                            context = {
                                'user': user,
                                'password': password,
                                'login_url': f"{settings.SITE_URL}/users/login/" if hasattr(settings, 'SITE_URL') else '/users/login/',
                                'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
                            }

                            message = render_to_string('users/emails/bulk_import_welcome.html', context)
                            send_mail(
                                subject,
                                strip_tags(message),
                                settings.DEFAULT_FROM_EMAIL,
                                [user.email],
                                html_message=message,
                                fail_silently=True
                            )
                        except Exception as email_error:
                            logger.warning(f"Failed to send welcome email to {user.email}: {email_error}")

                    results['successful'] += 1
                    results['created_users'].append({
                        'id': user.id,
                        'email': user.email,
                        'name': user.get_full_name(),
                        'role': role.name
                    })

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'row': index + 2,  # +2 because pandas is 0-indexed and header row
                    'email': str(row.get('email', '')),
                    'error': str(e)
                })
                logger.error(f"Error importing user at row {index + 2}: {e}")

    except Exception as e:
        logger.error(f"Error processing bulk import file: {e}")
        raise

    return results

# =============================================================================
# ERROR HANDLING
# =============================================================================

def handler403(request, exception):
    """
    Custom 403 error handler.
    """
    context = {
        'title': _('Access Denied'),
        'exception': exception
    }
    return render(request, 'errors/403.html', context, status=403)

def handler404(request, exception):
    """
    Custom 404 error handler.
    """
    context = {
        'title': _('Page Not Found'),
        'exception': exception
    }
    return render(request, 'errors/404.html', context, status=404)

def handler500(request):
    """
    Custom 500 error handler.
    """
    context = {
        'title': _('Server Error')
    }
    return render(request, 'errors/500.html', context, status=500)

# =============================================================================
# TEACHER PORTAL VIEWS
# =============================================================================

@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_dashboard(request):
    """
    Enhanced teacher dashboard with comprehensive overview.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get teacher's classes and assignments
    teacher_assignments = teacher.subject_assignments.filter(
        academic_session=current_session
    ).select_related('subject', 'class_assigned', 'academic_session')

    # Calculate statistics
    total_classes = teacher_assignments.values('class_assigned').distinct().count()
    total_subjects = teacher_assignments.values('subject').distinct().count()
    total_periods = teacher_assignments.aggregate(total=models.Sum('periods_per_week'))['total'] or 0

    # Get today's classes
    today_classes = []
    if current_session:
        from datetime import datetime
        today_weekday = datetime.now().strftime('%A').lower()

        today_timetable = teacher.timetable_entries.filter(
            academic_session=current_session,
            day_of_week=today_weekday
        ).select_related('class_assigned', 'subject').order_by('start_time')

        today_classes = list(today_timetable)

    # Get pending grading tasks
    from apps.assessment.models import Assignment
    pending_grading = Assignment.objects.filter(
        teacher=teacher,
        student__isnull=False,
        submission_status__in=['submitted', 'late'],
        graded_date__isnull=True
    ).count()

    # Get recent activities
    from apps.assessment.models import Mark
    recent_marks = Mark.objects.filter(
        entered_by=teacher
    ).select_related('exam', 'student').order_by('-entered_at')[:5]

    # Get attendance summary for today
    from apps.attendance.models import DailyAttendance
    from django.utils import timezone
    today = timezone.now().date()

    today_attendance_count = DailyAttendance.objects.filter(
        marked_by=request.user,
        date=today
    ).count()

    context = {
        'title': _('Teacher Dashboard'),
        'teacher': teacher,
        'current_session': current_session,
        'teacher_assignments': teacher_assignments,
        'total_classes': total_classes,
        'total_subjects': total_subjects,
        'total_periods': total_periods,
        'today_classes': today_classes,
        'pending_grading': pending_grading,
        'recent_marks': recent_marks,
        'today_attendance_count': today_attendance_count,
    }

    return render(request, 'users/teacher/dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_classes(request):
    """
    View all classes assigned to the teacher.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get all classes taught by this teacher
    teacher_assignments = teacher.subject_assignments.filter(
        academic_session=current_session
    ).select_related('subject', 'class_assigned', 'academic_session')

    # Group by class
    classes_data = {}
    for assignment in teacher_assignments:
        class_obj = assignment.class_assigned
        if class_obj.id not in classes_data:
            classes_data[class_obj.id] = {
                'class': class_obj,
                'subjects': [],
                'total_students': class_obj.enrollments.filter(
                    status='active',
                    academic_session=current_session
                ).count(),
                'total_periods': 0
            }
        classes_data[class_obj.id]['subjects'].append(assignment.subject)
        classes_data[class_obj.id]['total_periods'] += assignment.periods_per_week

    classes_list = list(classes_data.values())

    context = {
        'title': _('My Classes'),
        'teacher': teacher,
        'current_session': current_session,
        'classes_list': classes_list,
    }

    return render(request, 'users/teacher/classes.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_class_attendance(request, class_id):
    """
    Take attendance for a specific class.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Verify teacher teaches this class
    class_obj = get_object_or_404(
        Class.objects.select_related('academic_session'),
        id=class_id,
        academic_session=current_session
    )

    # Check if teacher is assigned to this class
    has_assignment = teacher.subject_assignments.filter(
        class_assigned=class_obj,
        academic_session=current_session
    ).exists()

    if not has_assignment and not request.user.is_staff:
        messages.error(request, _("You are not assigned to teach this class."))
        return redirect('users:teacher_classes')

    # Get students in this class
    enrollments = class_obj.enrollments.filter(
        status='active',
        academic_session=current_session
    ).select_related('student__user')

    students = [enrollment.student for enrollment in enrollments]

    # Get today's date and check if attendance already exists
    from django.utils import timezone
    today = timezone.now().date()

    from apps.attendance.models import DailyAttendance, AttendanceSession
    attendance_session = AttendanceSession.objects.filter(
        academic_session=current_session,
        is_active=True
    ).first()

    if not attendance_session:
        messages.error(request, _("No active attendance session found."))
        return redirect('users:teacher_classes')

    # Check if attendance already taken today
    existing_attendance = DailyAttendance.objects.filter(
        class_obj=class_obj,
        date=today,
        attendance_session=attendance_session
    ).select_related('student')

    attendance_taken = existing_attendance.exists()
    attendance_data = {}

    if attendance_taken:
        # Load existing attendance
        for attendance in existing_attendance:
            attendance_data[attendance.student.id] = {
                'status': attendance.status,
                'check_in_time': attendance.check_in_time,
                'remarks': attendance.remarks
            }

    if request.method == 'POST':
        # Process attendance submission
        attendance_records = []

        for student in students:
            status = request.POST.get(f'status_{student.id}', 'absent')
            remarks = request.POST.get(f'remarks_{student.id}', '')

            attendance, created = DailyAttendance.objects.get_or_create(
                student=student,
                date=today,
                attendance_session=attendance_session,
                defaults={
                    'status': status,
                    'remarks': remarks,
                    'marked_by': request.user,
                    'check_in_time': timezone.now() if status in ['present', 'late'] else None
                }
            )

            if not created:
                # Update existing
                attendance.status = status
                attendance.remarks = remarks
                attendance.marked_by = request.user
                if status in ['present', 'late'] and not attendance.check_in_time:
                    attendance.check_in_time = timezone.now()
                attendance.save()

            attendance_records.append(attendance)

        messages.success(request, _("Attendance recorded successfully for {} students.").format(len(attendance_records)))
        return redirect('users:teacher_class_attendance', class_id=class_id)

    context = {
        'title': _('Take Attendance'),
        'teacher': teacher,
        'class_obj': class_obj,
        'students': students,
        'today': today,
        'attendance_taken': attendance_taken,
        'attendance_data': attendance_data,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/class_attendance.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_class_materials(request, class_id):
    """
    View and manage materials for a specific class.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Verify teacher teaches this class
    class_obj = get_object_or_404(
        Class.objects.select_related('academic_session'),
        id=class_id,
        academic_session=current_session
    )

    # Check if teacher is assigned to this class
    has_assignment = teacher.subject_assignments.filter(
        class_assigned=class_obj,
        academic_session=current_session
    ).exists()

    if not has_assignment and not request.user.is_staff:
        messages.error(request, _("You are not assigned to teach this class."))
        return redirect('users:teacher_classes')

    # Get materials for this class and teacher
    from apps.academics.models import ClassMaterial
    materials = ClassMaterial.objects.filter(
        class_assigned=class_obj,
        teacher=teacher,
        academic_session=current_session
    ).order_by('-publish_date')

    context = {
        'title': _('Class Materials'),
        'teacher': teacher,
        'class_obj': class_obj,
        'materials': materials,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/class_materials.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_material_upload(request):
    """
    Upload new material for classes.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get classes taught by this teacher
    teacher_assignments = teacher.subject_assignments.filter(
        academic_session=current_session
    ).select_related('class_assigned', 'subject')

    classes_subjects = {}
    for assignment in teacher_assignments:
        class_id = str(assignment.class_assigned.id)
        if class_id not in classes_subjects:
            classes_subjects[class_id] = {
                'class': assignment.class_assigned,
                'subjects': []
            }
        classes_subjects[class_id]['subjects'].append(assignment.subject)

    if request.method == 'POST':
        from apps.academics.forms import ClassMaterialForm
        form = ClassMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.teacher = teacher
            material.academic_session = current_session
            material.save()

            messages.success(request, _("Material uploaded successfully!"))
            return redirect('users:teacher_class_materials', class_id=material.class_assigned.id)
    else:
        from apps.academics.forms import ClassMaterialForm
        form = ClassMaterialForm()

    context = {
        'title': _('Upload Material'),
        'teacher': teacher,
        'form': form,
        'classes_subjects': classes_subjects,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/material_upload.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_students(request):
    """
    View all students taught by the teacher.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get all students taught by this teacher
    taught_classes = Class.objects.filter(
        subject_assignments__teacher=teacher,
        subject_assignments__academic_session=current_session
    ).distinct()

    enrollments = Enrollment.objects.filter(
        class_enrolled__in=taught_classes,
        status='active',
        academic_session=current_session
    ).select_related('student__user', 'class_enrolled')

    # Group students by class
    students_by_class = {}
    for enrollment in enrollments:
        class_name = enrollment.class_enrolled.name
        if class_name not in students_by_class:
            students_by_class[class_name] = []
        students_by_class[class_name].append(enrollment.student)

    context = {
        'title': _('My Students'),
        'teacher': teacher,
        'students_by_class': students_by_class,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/students.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_student_progress(request, student_id):
    """
    View detailed progress for a specific student.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    student = get_object_or_404(Student, id=student_id)

    # Verify teacher teaches this student
    teaches_student = Enrollment.objects.filter(
        student=student,
        class_enrolled__subject_assignments__teacher=teacher,
        status='active',
        academic_session=current_session
    ).exists()

    if not teaches_student and not request.user.is_staff:
        messages.error(request, _("You do not teach this student."))
        return redirect('users:teacher_students')

    # Get student's academic records
    from apps.academics.models import AcademicRecord
    academic_records = AcademicRecord.objects.filter(
        student=student,
        academic_session=current_session
    ).select_related('class_enrolled')

    # Get assessment results
    from apps.assessment.models import Result, ResultSubject
    results = Result.objects.filter(
        student=student,
        academic_class__academic_session=current_session
    ).select_related('exam_type', 'grade')

    # Get behavior records
    from apps.academics.models import BehaviorRecord
    behavior_records = BehaviorRecord.objects.filter(
        student=student
    ).select_related('reported_by').order_by('-incident_date')[:10]

    # Get attendance summary
    from apps.attendance.models import AttendanceSummary
    attendance_summary = AttendanceSummary.objects.filter(
        student=student,
        academic_session=current_session
    ).order_by('-month', '-year')[:6]

    context = {
        'title': _('Student Progress'),
        'teacher': teacher,
        'student': student,
        'academic_records': academic_records,
        'results': results,
        'behavior_records': behavior_records,
        'attendance_summary': attendance_summary,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/student_progress.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_assessment(request):
    """
    Teacher assessment overview and management.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get exams created by teacher
    from apps.assessment.models import Exam
    exams = Exam.objects.filter(
        academic_class__subject_assignments__teacher=teacher,
        academic_session=current_session
    ).select_related('subject', 'exam_type', 'academic_class').distinct()

    # Get assignments created by teacher
    from apps.assessment.models import Assignment
    assignments = Assignment.objects.filter(
        teacher=teacher,
        academic_session=current_session,
        student__isnull=True  # Template assignments
    ).select_related('subject', 'academic_class')

    # Get pending grading
    pending_grading = Assignment.objects.filter(
        teacher=teacher,
        student__isnull=False,
        submission_status__in=['submitted', 'late'],
        graded_date__isnull=True
    ).select_related('student__user', 'subject')

    context = {
        'title': _('Assessment Management'),
        'teacher': teacher,
        'exams': exams,
        'assignments': assignments,
        'pending_grading': pending_grading,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/assessment.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_timetable(request):
    """
    View teacher's timetable/schedule.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get teacher's timetable
    from apps.academics.models import Timetable
    timetable_entries = Timetable.objects.filter(
        teacher=teacher,
        academic_session=current_session
    ).select_related('class_assigned', 'subject').order_by('day_of_week', 'period_number')

    # Group by day
    timetable_by_day = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    for day in days:
        day_entries = timetable_entries.filter(day_of_week=day)
        if day_entries.exists():
            timetable_by_day[day] = list(day_entries)

    context = {
        'title': _('My Timetable'),
        'teacher': teacher,
        'timetable_by_day': timetable_by_day,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/timetable.html', context)


@login_required
@user_passes_test(lambda u: u.user_roles.filter(role__role_type='teacher').exists(), login_url=reverse_lazy('users:dashboard'))
def teacher_communication(request):
    """
    Teacher communication hub for parent interactions.
    """
    teacher = request.user.teacher_profile
    current_session = AcademicSession.objects.filter(is_current=True).first()

    # Get recent messages
    from apps.communication.models import Message
    sent_messages = Message.objects.filter(
        sender=request.user
    ).select_related('recipients').order_by('-created_at')[:10]

    received_messages = Message.objects.filter(
        recipients=request.user
    ).select_related('sender').order_by('-created_at')[:10]

    # Get students' parents for messaging
    taught_classes = Class.objects.filter(
        subject_assignments__teacher=teacher,
        subject_assignments__academic_session=current_session
    ).distinct()

    # Get parent contacts
    from apps.users.models import ParentStudentRelationship
    parent_relationships = ParentStudentRelationship.objects.filter(
        student__enrollments__class_enrolled__in=taught_classes,
        status='active'
    ).select_related('parent__user', 'student__user').distinct()

    context = {
        'title': _('Communication'),
        'teacher': teacher,
        'sent_messages': sent_messages,
        'received_messages': received_messages,
        'parent_relationships': parent_relationships,
        'current_session': current_session,
    }

    return render(request, 'users/teacher/communication.html', context)
