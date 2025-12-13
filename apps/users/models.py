
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import secrets
import string
from apps.core.models import CoreBaseModel, AddressModel, ContactModel




class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """
    def get_admin_users(self):
        """Simple method to get all admin users for your custom admin panel"""
        return self.filter(is_staff=True)

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError(_('The Email field must be set'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with admin permissions.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with email as primary identifier.
    """
    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    # Remove username field, use email instead
    username = None
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        help_text=_('Primary email address for communication')
    )

    # Additional fields
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    )
    mobile = models.CharField(
        _('mobile number'),
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text=_('Primary mobile number for SMS notifications')
    )

    # Verification fields
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Designates whether the user has verified their email address')
    )
    email_verified_at = models.DateTimeField(_('email verified at'), null=True, blank=True)
    verification_token = models.CharField(_('verification token'), max_length=100, blank=True)

    # Security fields
    last_login_ip = models.GenericIPAddressField(_('last login IP'), null=True, blank=True)
    current_login_ip = models.GenericIPAddressField(_('current login IP'), null=True, blank=True)
    login_count = models.PositiveIntegerField(_('login count'), default=0)



    # Preferences
    language = models.CharField(
        _('language'),
        max_length=10,
        default='en',
        choices=[
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('ar', _('Arabic')),
        ],
        help_text=_('Preferred language for the interface')
    )
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='UTC',
        help_text=_('User\'s preferred timezone')
    )

    # Override AbstractUser fields to make optional
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['last_login']),
        ]

    def __str__(self):
        return self.email

    def get_initials(self):
        """Return initials for the user (e.g. 'JD' for John Doe)."""
        parts = []

        if self.first_name:
            parts.append(self.first_name.strip())
        if self.last_name:
            parts.append(self.last_name.strip())
        if parts:
            initials = ''.join([p[0].upper() for p in parts if p])
            return initials[:2]
        # fallback to email username part
        if self.email:
            name_part = self.email.split('@', 1)[0]
            return name_part[:2].upper()
        return ''

    @property
    def full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Return display name (full name)."""
        return self.full_name

    def verify_email(self):
        """Mark user's email as verified."""
        self.is_verified = True
        self.email_verified_at = timezone.now()
        self.verification_token = ''
        self.save()

    def increment_login_count(self):
        """Increment login count and update IP addresses."""
        self.login_count += 1
        self.last_login_ip = self.current_login_ip
        self.current_login_ip = None  # Will be set during login
        self.save()

    def is_admin_user(self):
        """Simple check if user can access admin panel"""
        return self.is_staff or self.is_superuser

    def make_random_password(self, length=12):
        """
        Generate a random password for the user.
        """
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(characters) for i in range(length))
        self.set_password(password)
        self.save()
        return password


class Role(CoreBaseModel):
    """
    Model for defining user roles and permissions.
    """
    class RoleType(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('Super Administrator')
        ADMIN = 'admin', _('Administrator')
        PRINCIPAL = 'principal', _('Principal')
        DEPARTMENT_HEAD = 'department_head', _('Department Head')
        COUNSELOR = 'counselor', _('School Counselor')
        TEACHER = 'teacher', _('Teacher')
        STUDENT = 'student', _('Student')
        PARENT = 'parent', _('Parent')
        ACCOUNTANT = 'accountant', _('Accountant')
        LIBRARIAN = 'librarian', _('Librarian')
        DRIVER = 'driver', _('Driver')
        SUPPORT = 'support', _('Support Staff')
        TRANSPORT_MANAGER = 'transport_manager', _('Transport Manager')
        HOSTEL_WARDEN = 'hostel_warden', _('Hostel Warden')

    STAFF_ROLES = [
        RoleType.SUPER_ADMIN, RoleType.ADMIN, RoleType.PRINCIPAL,
        RoleType.DEPARTMENT_HEAD, RoleType.COUNSELOR, RoleType.TEACHER,
        RoleType.ACCOUNTANT, RoleType.LIBRARIAN, RoleType.DRIVER,
        RoleType.SUPPORT, RoleType.TRANSPORT_MANAGER, RoleType.HOSTEL_WARDEN
    ]

    name = models.CharField(_('role name'), max_length=50, unique=True)
    role_type = models.CharField(
        _('role type'),
        max_length=20,
        choices=RoleType.choices,
        unique=True
    )
    description = models.TextField(_('description'), blank=True)
    permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('permissions'),
        blank=True,
        related_name='roles'
    )
    is_system_role = models.BooleanField(_('is system role'), default=False)
    hierarchy_level = models.PositiveIntegerField(
        _('hierarchy level'),
        default=0,
        help_text=_('Higher number indicates higher authority (0 = lowest)')
    )

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['-hierarchy_level', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure system roles cannot be modified."""
        # Track original values for audit logging
        if self.pk:
            try:
                original = Role.objects.get(pk=self.pk)
                self._original_name = original.name
                self._original_role_type = original.role_type
                self._original_hierarchy_level = original.hierarchy_level
                self._original_status = original.status

                # Check system role constraints only if this is an update (not creation)
                if self.is_system_role:
                    if original.name != self.name or original.role_type != self.role_type:
                        raise ValueError(_("System roles cannot be modified."))
            except Role.DoesNotExist:
                # Object doesn't exist yet (during creation)
                pass

        super().save(*args, **kwargs)


class UserProfile(CoreBaseModel, AddressModel, ContactModel):
    """
    Extended profile information for users.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )
    
    # Personal Information
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    GENDER_CHOICES = [
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other')),
        ('prefer_not_to_say', _('Prefer not to say')),
    ]
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True
    )
    nationality = models.CharField(_('nationality'), max_length=100, blank=True)
    identification_number = models.CharField(
        _('identification number'),
        max_length=50,
        blank=True,
        help_text=_('National ID, Passport number, etc.')
    )
    
    # Profile Image
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profiles/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text=_('Profile picture (recommended size: 200x200 pixels)')
    )
    
    # Employee ID (for staff members)
    employee_id = models.CharField(
        _('employee ID'),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Unique identifier for staff members')
    )

    # Biography
    bio = models.TextField(_('biography'), blank=True)
    
    # Social Media
    website = models.URLField(_('website'), blank=True)
    facebook = models.URLField(_('facebook'), blank=True)
    twitter = models.URLField(_('twitter'), blank=True)
    linkedin = models.URLField(_('linkedin'), blank=True)
    
    # Settings
    email_notifications = models.BooleanField(_('email notifications'), default=True)
    sms_notifications = models.BooleanField(_('SMS notifications'), default=False)
    push_notifications = models.BooleanField(_('push notifications'), default=True)
    
    # Metadata
    last_profile_update = models.DateTimeField(_('last profile update'), auto_now=True)

    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['identification_number']),
        ]

    def __str__(self):
        return f"Profile of {self.user}"

    @property
    def age(self):
        """Calculate age from date of birth."""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class UserRole(CoreBaseModel):
    """
    Model for assigning roles to users with context (e.g., which school/class).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('user')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('role')
    )
    is_primary = models.BooleanField(
        _('is primary role'),
        default=False,
        help_text=_('Designates the primary role for this user')
    )

    # Context fields (optional, for role-specific context)
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('academic session')
    )
    # Additional context fields can be added based on role type
    context_id = models.CharField(
        _('context ID'),
        max_length=100,
        blank=True,
        help_text=_('Role context identifier (e.g., class_id for teachers)')
    )

    class Meta:
        verbose_name = _('User Role')
        verbose_name_plural = _('User Roles')
        unique_together = ['user', 'role', 'context_id']
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_primary']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user} - {self.role}"

    def save(self, *args, **kwargs):
        """Ensure only one primary role per user per academic session."""
        # Track original values for audit logging
        if self.pk:
            try:
                original = UserRole.objects.get(pk=self.pk)
                self._original_is_primary = original.is_primary
            except UserRole.DoesNotExist:
                pass

        if self.is_primary:
            # Set all other roles for this user in the same context as non-primary
            UserRole.objects.filter(
                user=self.user,
                academic_session=self.academic_session,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class UserRoleActivity(CoreBaseModel):
    """
    Model for tracking user role assignment and removal activities.
    """
    class ActionType(models.TextChoices):
        ASSIGNED = 'assigned', _('Role Assigned')
        REMOVED = 'removed', _('Role Removed')
        SET_PRIMARY = 'set_primary', _('Set as Primary')
        SET_SECONDARY = 'set_secondary', _('Set as Secondary')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_activities',
        verbose_name=_('affected user')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_activities',
        verbose_name=_('affected role')
    )
    action_type = models.CharField(
        _('action type'),
        max_length=15,
        choices=ActionType.choices
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_role_activities',
        verbose_name=_('performed by')
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('academic session')
    )
    details = models.TextField(_('details'), blank=True, help_text=_('Additional context about the change'))

    class Meta:
        verbose_name = _('User Role Activity')
        verbose_name_plural = _('User Role Activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['role', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action_type}: {self.user} - {self.role} (by {self.performed_by})"

    @property
    def action_description(self):
        """Return a human-readable description of the action."""
        if self.action_type == self.ActionType.ASSIGNED:
            return _("was assigned the role")
        elif self.action_type == self.ActionType.REMOVED:
            return _("was removed from the role")
        elif self.action_type == self.ActionType.SET_PRIMARY:
            return _("had their role set as primary")
        elif self.action_type == self.ActionType.SET_SECONDARY:
            return _("had their role set as secondary")
        return self.action_type

    @classmethod
    def log_activity(cls, user, role, action_type, performed_by=None, academic_session=None, details=""):
        """
        Class method to log a user role activity.
        """
        return cls.objects.create(
            user=user,
            role=role,
            action_type=action_type,
            performed_by=performed_by,
            academic_session=academic_session,
            details=details
        )


class LoginHistory(CoreBaseModel):
    """
    Model for tracking user login history.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name=_('user'),
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(_('IP address'))
    user_agent = models.TextField(_('user agent'), blank=True)
    location = models.CharField(_('location'), max_length=255, blank=True)
    login_method = models.CharField(
        _('login method'),
        max_length=20,
        choices=[
            ('password', _('Password')),
            ('sso', _('Single Sign-On')),
            ('token', _('Token')),
        ],
        default='password'
    )
    was_successful = models.BooleanField(_('was successful'), default=True)
    failure_reason = models.CharField(_('failure reason'), max_length=100, blank=True)
    session_key = models.CharField(_('session key'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Login History')
        verbose_name_plural = _('Login History')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        status = "Success" if self.was_successful else "Failed"
        return f"{self.user} - {self.created_at} - {status}"


class PasswordHistory(CoreBaseModel):
    """
    Model for storing password history to enforce password policies.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_history',
        verbose_name=_('user')
    )
    password_hash = models.CharField(_('password hash'), max_length=255)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changed_passwords',
        verbose_name=_('changed by')
    )
    change_reason = models.CharField(
        _('change reason'),
        max_length=20,
        choices=[
            ('initial', _('Initial Setup')),
            ('regular', _('Regular Change')),
            ('compromise', _('Suspected Compromise')),
            ('reset', _('Password Reset')),
        ],
        default='regular'
    )

    class Meta:
        verbose_name = _('Password History')
        verbose_name_plural = _('Password History')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.created_at}"


class UserSession(CoreBaseModel):
    """
    Model for tracking active user sessions.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('user')
    )
    session_key = models.CharField(_('session key'), max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(_('IP address'))
    user_agent = models.TextField(_('user agent'), blank=True)
    last_activity = models.DateTimeField(_('last activity'), auto_now=True)
    expires_at = models.DateTimeField(_('expires at'))

    class Meta:
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"{self.user} - {self.session_key}"

    @property
    def is_expired(self):
        """Check if session has expired."""
        return timezone.now() > self.expires_at


class ParentStudentRelationship(CoreBaseModel):
    """
    Model for managing parent-student relationships.
    """
    class RelationshipType(models.TextChoices):
        FATHER = 'father', _('Father')
        MOTHER = 'mother', _('Mother')
        GUARDIAN = 'guardian', _('Guardian')
        SIBLING = 'sibling', _('Sibling')
        OTHER = 'other', _('Other')

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='children_relationships',
        verbose_name=_('parent'),
        limit_choices_to={'user_roles__role__role_type': Role.RoleType.PARENT}
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='parent_relationships',
        verbose_name=_('student'),
        limit_choices_to={'user_roles__role__role_type': Role.RoleType.STUDENT}
    )
    relationship_type = models.CharField(
        _('relationship type'),
        max_length=20,
        choices=RelationshipType.choices
    )
    is_primary_contact = models.BooleanField(
        _('is primary contact'),
        default=False,
        help_text=_('Designates the primary contact for the student')
    )
    can_pickup = models.BooleanField(
        _('can pickup student'),
        default=True,
        help_text=_('Can this person pickup the student from school?')
    )
    emergency_contact_order = models.PositiveIntegerField(
        _('emergency contact order'),
        default=0,
        help_text=_('Order in which to contact in emergencies (0 = first)')
    )

    class Meta:
        verbose_name = _('Parent-Student Relationship')
        verbose_name_plural = _('Parent-Student Relationships')
        unique_together = ['parent', 'student', 'relationship_type']
        ordering = ['emergency_contact_order', 'relationship_type']
        indexes = [
            models.Index(fields=['parent', 'is_primary_contact']),
            models.Index(fields=['student', 'relationship_type']),
        ]

    def __str__(self):
        return f"{self.parent} - {self.relationship_type} - {self.student}"

    def save(self, *args, **kwargs):
        """Ensure only one primary contact per student."""
        if self.is_primary_contact:
            ParentStudentRelationship.objects.filter(
                student=self.student,
                is_primary_contact=True
            ).exclude(pk=self.pk).update(is_primary_contact=False)
        super().save(*args, **kwargs)

# Application Models

class StudentApplication(CoreBaseModel):
    """
    Model for student applications.
    """
    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        UNDER_REVIEW = 'under_review', _('Under Review')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        WAITLISTED = 'waitlisted', _('Waitlisted')

    class GradeLevel(models.TextChoices):
        PRESCHOOL = 'preschool', _('Preschool')
        KINDERGARTEN = 'kindergarten', _('Kindergarten')
        GRADE_1 = 'grade_1', _('Grade 1')
        GRADE_2 = 'grade_2', _('Grade 2')
        GRADE_3 = 'grade_3', _('Grade 3')
        GRADE_4 = 'grade_4', _('Grade 4')
        GRADE_5 = 'grade_5', _('Grade 5')
        GRADE_6 = 'grade_6', _('Grade 6')
        GRADE_7 = 'grade_7', _('Grade 7')
        GRADE_8 = 'grade_8', _('Grade 8')
        GRADE_9 = 'grade_9', _('Grade 9')
        GRADE_10 = 'grade_10', _('Grade 10')
        GRADE_11 = 'grade_11', _('Grade 11')
        GRADE_12 = 'grade_12', _('Grade 12')

    # Personal Information
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)
    date_of_birth = models.DateField(_('date of birth'))
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=UserProfile.GENDER_CHOICES
    )
    nationality = models.CharField(_('nationality'), max_length=100)
    
    # Contact Information
    email = models.EmailField(_('email address'))
    phone = models.CharField(_('phone number'), max_length=20)
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state/province'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20)
    country = models.CharField(_('country'), max_length=100)
    
    # Academic Information
    grade_applying_for = models.CharField(
        _('grade applying for'),
        max_length=20,
        choices=GradeLevel.choices
    )
    previous_school = models.CharField(_('previous school'), max_length=200, blank=True)
    previous_grade = models.CharField(_('previous grade'), max_length=20, blank=True)
    academic_achievements = models.TextField(_('academic achievements'), blank=True)
    
    # Parent/Guardian Information
    parent_first_name = models.CharField(_("parent's first name"), max_length=100)
    parent_last_name = models.CharField(_("parent's last name"), max_length=100)
    parent_email = models.EmailField(_("parent's email"))
    parent_phone = models.CharField(_("parent's phone"), max_length=20)
    parent_relationship = models.CharField(
        _('relationship to student'),
        max_length=20,
        choices=ParentStudentRelationship.RelationshipType.choices
    )
    
    # Documents
    birth_certificate = models.FileField(
        _('birth certificate'),
        upload_to='student_applications/birth_certificates/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload birth certificate (PDF, JPG, PNG)')
    )
    previous_school_transcript = models.FileField(
        _('previous school transcript'),
        upload_to='student_applications/transcripts/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload academic transcript from previous school (PDF)')
    )
    recommendation_letter = models.FileField(
        _('recommendation letter'),
        upload_to='student_applications/recommendations/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload recommendation letter (PDF, DOC, DOCX)')
    )
    medical_report = models.FileField(
        _('medical report'),
        upload_to='student_applications/medical_reports/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload medical report if applicable (PDF)')
    )

    # Additional Information
    medical_conditions = models.TextField(_('medical conditions'), blank=True)
    special_needs = models.TextField(_('special needs'), blank=True)
    extracurricular_interests = models.TextField(_('extracurricular interests'), blank=True)
    
    # Application Details
    application_status = models.CharField(
        _('application status'),
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('academic session')
    )
    application_date = models.DateTimeField(_('application date'), auto_now_add=True)
    
    # Review Information
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_student_applications',
        verbose_name=_('reviewed by')
    )
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)
    review_notes = models.TextField(_('review notes'), blank=True)
    
    # System fields
    application_number = models.CharField(
        _('application number'),
        max_length=20,
        unique=True,
        blank=True
    )
    user_account = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_application',
        verbose_name=_('user account')
    )

    class Meta:
        verbose_name = _('Student Application')
        verbose_name_plural = _('Student Applications')
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['application_status', 'application_date']),
            models.Index(fields=['email']),
            models.Index(fields=['application_number']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.grade_applying_for}"

    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self.generate_application_number()
        super().save(*args, **kwargs)

    def generate_application_number(self):
        """Generate unique application number."""
        prefix = "STU"
        year = timezone.now().strftime('%Y')
        last_app = StudentApplication.objects.filter(
            application_number__startswith=f"{prefix}{year}"
        ).order_by('application_number').last()
        
        if last_app:
            last_num = int(last_app.application_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
            
        return f"{prefix}{year}{new_num:04d}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def parent_full_name(self):
        return f"{self.parent_first_name} {self.parent_last_name}"

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class StaffApplication(CoreBaseModel):
    """
    Model for staff applications.
    """
    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        UNDER_REVIEW = 'under_review', _('Under Review')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        INTERVIEW_SCHEDULED = 'interview_scheduled', _('Interview Scheduled')

    class PositionType(models.TextChoices):
        FULL_TIME = 'full_time', _('Full Time')
        PART_TIME = 'part_time', _('Part Time')
        CONTRACT = 'contract', _('Contract')
        VOLUNTEER = 'volunteer', _('Volunteer')

    # Personal Information
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)
    date_of_birth = models.DateField(_('date of birth'))
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=UserProfile.GENDER_CHOICES
    )
    nationality = models.CharField(_('nationality'), max_length=100)
    
    # Contact Information
    email = models.EmailField(_('email address'))
    phone = models.CharField(_('phone number'), max_length=20)
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state/province'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20)
    country = models.CharField(_('country'), max_length=100)
    
    # Professional Information
    position_applied_for = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        limit_choices_to={'role_type__in': Role.STAFF_ROLES, 'status': 'active'},
        verbose_name=_('position applied for')
    )
    position_type = models.CharField(
        _('position type'),
        max_length=20,
        choices=PositionType.choices,
        default=PositionType.FULL_TIME
    )
    expected_salary = models.DecimalField(
        _('expected salary'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Educational Background
    highest_qualification = models.CharField(_('highest qualification'), max_length=200)
    qualified_institution = models.CharField(_('institution'), max_length=200)
    year_graduated = models.PositiveIntegerField(_('year graduated'))
    
    # Professional Experience
    years_of_experience = models.PositiveIntegerField(_('years of experience'), default=0)
    previous_employer = models.CharField(_('previous employer'), max_length=200, blank=True)
    previous_position = models.CharField(_('previous position'), max_length=200, blank=True)
    
    # Documents
    cv = models.FileField(
        _('curriculum vitae'),
        upload_to='staff_applications/cvs/%Y/%m/%d/',
        help_text=_('Upload your CV (PDF, DOC, DOCX)')
    )
    cover_letter = models.FileField(
        _('cover letter'),
        upload_to='staff_applications/cover_letters/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload your cover letter (optional)')
    )
    certificates = models.FileField(
        _('certificates'),
        upload_to='staff_applications/certificates/%Y/%m/%d/',
        blank=True,
        help_text=_('Upload relevant certificates (optional)')
    )
    
    # References
    reference1_name = models.CharField(_('reference 1 name'), max_length=100)
    reference1_position = models.CharField(_('reference 1 position'), max_length=100)
    reference1_contact = models.CharField(_('reference 1 contact'), max_length=100)
    
    reference2_name = models.CharField(_('reference 2 name'), max_length=100, blank=True)
    reference2_position = models.CharField(_('reference 2 position'), max_length=100, blank=True)
    reference2_contact = models.CharField(_('reference 2 contact'), max_length=100, blank=True)
    
    # Application Details
    application_status = models.CharField(
        _('application status'),
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('academic session')
    )
    application_date = models.DateTimeField(_('application date'), auto_now_add=True)
    
    # Review Information
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_staff_applications',
        verbose_name=_('reviewed by')
    )
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)
    review_notes = models.TextField(_('review notes'), blank=True)
    interview_date = models.DateTimeField(_('interview date'), null=True, blank=True)
    
    # System fields
    application_number = models.CharField(
        _('application number'),
        max_length=20,
        unique=True,
        blank=True
    )
    user_account = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_application',
        verbose_name=_('user account')
    )

    class Meta:
        verbose_name = _('Staff Application')
        verbose_name_plural = _('Staff Applications')
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['application_status', 'application_date']),
            models.Index(fields=['email']),
            models.Index(fields=['application_number']),
            models.Index(fields=['position_applied_for']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position_applied_for}"

    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self.generate_application_number()
        super().save(*args, **kwargs)

    def generate_application_number(self):
        """Generate unique application number using SequenceGenerator."""
        from apps.core.models import SequenceGenerator
        sequence, created = SequenceGenerator.objects.get_or_create(
            sequence_type=SequenceGenerator.SequenceType.STAFF_APPLICATION,
            defaults={'prefix': 'STA', 'padding': 4, 'reset_frequency': 'yearly'}
        )
        return sequence.get_next_number()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

    def clean(self):
        """Validate file types and sizes."""
        from django.core.exceptions import ValidationError
        
        # CV validation
        if self.cv:
            valid_extensions = ['.pdf', '.doc', '.docx']
            ext = str(self.cv.name).lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise ValidationError({'cv': _('Only PDF, DOC, and DOCX files are allowed for CV.')})
            
            if self.cv.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValidationError({'cv': _('CV file size must not exceed 5MB.')})

# Permission synchronization utilities
def sync_user_permissions(user):
    """
    Synchronize user's Django permissions based on their active roles.
    This ensures that PermissionRequiredMixin checks work correctly.
    """
    from django.contrib.auth.models import Permission

    # Get all permissions from user's active roles
    role_permissions = Permission.objects.filter(
        roles__user_roles__user=user,
        roles__user_roles__status='active'
    ).distinct()

    # Update user's permissions
    user.user_permissions.set(role_permissions)
    user.save()

    return role_permissions.count()


def sync_all_user_permissions():
    """
    Synchronize permissions for all users based on their roles.
    Useful for initial setup or bulk updates.
    """
    users_updated = 0
    for user in User.objects.all():
        permissions_count = sync_user_permissions(user)
        if permissions_count > 0:
            users_updated += 1

    return users_updated


# Utility functions for guardian notifications
def get_student_guardians(student_user):
    """
    Get all guardians (parents) for a student user.
    Returns a QuerySet of User objects who are guardians of the student.
    """
    return User.objects.filter(
        children_relationships__student=student_user,
        children_relationships__status='active'
    ).distinct()


def notify_guardians_profile_update(student_user, guardians, changed_fields):
    """
    Send notifications to guardians when a student updates their profile.
    """
    from apps.communication.views import create_notification
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.utils.html import strip_tags

    student_name = student_user.get_full_name() or student_user.email
    changed_fields_str = ', '.join([field.replace('_', ' ').title() for field in changed_fields])

    # Create in-app notifications for each guardian
    for guardian in guardians:
        try:
            create_notification(
                user=guardian,
                title=f'Profile Update: {student_name}',
                message=f'{student_name} has updated their profile. Changed fields: {changed_fields_str}',
                notification_type='info',
                priority='medium',
                action_url=f'/users/profile/{student_user.id}/',
                related_model='users.UserProfile',
                related_object_id=str(student_user.profile.id)
            )
        except Exception as e:
            # Log error but don't fail the entire process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create notification for guardian {guardian.id}: {e}")

    # Send email notifications
    subject = f'Profile Update Notification - {student_name}'

    for guardian in guardians:
        try:
            if guardian.profile.email_notifications:
                context = {
                    'guardian': guardian,
                    'student': student_user,
                    'student_name': student_name,
                    'changed_fields': changed_fields,
                    'changed_fields_str': changed_fields_str,
                    'school_name': getattr(settings, 'SCHOOL_NAME', 'Our School'),
                    'profile_url': f"{settings.SITE_URL}/users/profile/{student_user.id}/" if hasattr(settings, 'SITE_URL') else '#',
                }

                # Try to use email template if it exists
                try:
                    from apps.communication.models import EmailTemplate
                    template = EmailTemplate.objects.filter(
                        name='guardian_profile_update',
                        is_active=True
                    ).first()

                    if template:
                        subject, html_message, text_message = template.render_template(context)
                    else:
                        # Fallback to basic template
                        html_message = render_to_string('users/emails/guardian_profile_update.html', context)
                        text_message = strip_tags(html_message)
                except:
                    # Fallback if template system fails
                    html_message = f"""
                    <h2>Profile Update Notification</h2>
                    <p>Dear {guardian.get_full_name() or guardian.email},</p>
                    <p>Your child {student_name} has updated their profile information.</p>
                    <p><strong>Changed fields:</strong> {changed_fields_str}</p>
                    <p>Please review the changes and contact the school if you have any concerns.</p>
                    <p>Best regards,<br>{getattr(settings, 'SCHOOL_NAME', 'School Administration')}</p>
                    """
                    text_message = strip_tags(html_message)

                send_mail(
                    subject,
                    text_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [guardian.email],
                    html_message=html_message,
                    fail_silently=True,
                )
        except Exception as e:
            # Log error but don't fail the entire process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email to guardian {guardian.id}: {e}")


# Signal handlers for user management
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create user profile when a new user is created.
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Automatically save user profile when user is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=UserRole)
def auto_map_user_to_institution(sender, instance, created, **kwargs):
    """
    Automatically map users to institutions when roles are assigned.
    """
    from apps.core.models import Institution, InstitutionUser

    # Only process if this is a staff role that requires institution mapping
    staff_role_types = [
        'super_admin', 'admin', 'principal', 'department_head', 'counselor',
        'teacher', 'accountant', 'librarian', 'driver', 'support',
        'transport_manager', 'hostel_warden'
    ]

    if instance.role.role_type in staff_role_types:
        # Check if user is already mapped to an institution
        existing_mapping = InstitutionUser.objects.filter(
            user=instance.user,
            is_primary=True
        ).first()

        if not existing_mapping:
            # Try to find an appropriate institution
            # First, check if there are any active institutions
            default_institution = Institution.objects.filter(
                is_active=True
            ).first()

            if default_institution:
                # Create institution-user mapping
                institution_user, created = InstitutionUser.objects.get_or_create(
                    user=instance.user,
                    institution=default_institution,
                    defaults={
                        'is_primary': True,
                        'employee_id': f'{instance.role.role_type}_{default_institution.code}_{instance.user.id}',
                    }
                )

                if created:
                    # Update user profile with employee ID
                    if hasattr(instance.user, 'profile') and instance.user.profile:
                        instance.user.profile.employee_id = institution_user.employee_id
                        instance.user.profile.save()

@receiver(post_save, sender=UserRole)
def sync_permissions_on_role_save(sender, instance, **kwargs):
    """
    Sync user permissions when a role is assigned or updated.
    """
    sync_user_permissions(instance.user)


@receiver(post_delete, sender=UserRole)
def sync_permissions_on_role_delete(sender, instance, **kwargs):
    """
    Sync user permissions when a role is removed.
    """
    sync_user_permissions(instance.user)


@receiver(post_save, sender=UserProfile)
def notify_guardians_on_profile_update(sender, instance, created, **kwargs):
    """
    Notify guardians when a student updates their profile.
    """
    if created:
        # Don't notify on profile creation
        return

    # Check if the user is a student
    if not instance.user.user_roles.filter(role__role_type=Role.RoleType.STUDENT).exists():
        return

    # Get the previous profile state from the database
    try:
        previous_profile = UserProfile.objects.get(pk=instance.pk)
    except UserProfile.DoesNotExist:
        return

    # Check if any meaningful fields changed
    meaningful_fields = [
        'date_of_birth', 'gender', 'nationality',
        'identification_number', 'bio', 'website', 'facebook', 'twitter', 'linkedin'
    ]

    changed_fields = []
    for field in meaningful_fields:
        old_value = getattr(previous_profile, field)
        new_value = getattr(instance, field)
        if old_value != new_value:
            changed_fields.append(field)

    # Also check address fields if they exist
    address_fields = ['address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country']
    for field in address_fields:
        if hasattr(instance, field):
            old_value = getattr(previous_profile, field)
            new_value = getattr(instance, field)
            if old_value != new_value:
                changed_fields.append(field)

    # If profile picture changed
    if previous_profile.profile_picture != instance.profile_picture:
        changed_fields.append('profile_picture')

    # Only notify if there were actual changes
    if not changed_fields:
        return

    # Get guardians and send notifications
    guardians = get_student_guardians(instance.user)
    if guardians:
        notify_guardians_profile_update(instance.user, guardians, changed_fields)
