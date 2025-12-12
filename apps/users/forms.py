# apps/users/forms.py

from django import forms
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.academics.models import AcademicSession

from .models import User, UserProfile, Role, UserRole, LoginHistory, PasswordHistory, ParentStudentRelationship, StudentApplication, StaffApplication


class UserCreationForm(forms.ModelForm):
    """
    Form for creating new users with enhanced validation.
    """
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter password')
        }),
        help_text=_("Password must be at least 8 characters long and contain letters and numbers.")
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm password')
        }),
        help_text=_("Enter the same password as above, for verification.")
    )

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'mobile', 
            'is_active', 'is_staff', 'is_superuser'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('user@example.com')
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last name')
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+1234567890')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'email': _('Required. A valid email address that will be used for login.'),
            'mobile': _('Optional. International format recommended.'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = User.objects.normalize_email(email)
            if User.objects.filter(email=email).exists():
                raise ValidationError(
                    _("A user with this email address already exists.")
                )
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _("The two password fields didn't match.")
            )
        
        # Validate password strength
        if password1:
            try:
                validate_password(password1)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating existing user information.
    """
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'mobile',
            'language', 'timezone', 'is_active', 'is_staff', 
            'is_superuser', 'is_verified', 'status'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'  # Email shouldn't be changed easily
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'language': forms.Select(attrs={
                'class': 'form-control'
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = User.objects.normalize_email(email)
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError(
                    _("A user with this email address already exists.")
                )
        return email


class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """
    class Meta:
        model = UserProfile
        fields = [
            'date_of_birth', 'gender', 'nationality', 'identification_number',
            'employee_id', # Added employee_id
            'profile_picture', 'bio', 'website', 'facebook', 'twitter', 'linkedin',
            'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country',
            'phone', 'mobile', 'email', 'emergency_contact', 'emergency_phone',
            'email_notifications', 'sms_notifications', 'push_notifications'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'identification_number': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Tell us about yourself...')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://example.com')
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://facebook.com/username')
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://twitter.com/username')
            }),
            'linkedin': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://linkedin.com/in/username')
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Street address, P.O. box')
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Apartment, suite, unit, building, floor, etc.')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City')
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('State/Province/Region')
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Postal code')
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Country')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Landline phone number')
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Mobile number')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Alternative email address')
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Emergency contact name')
            }),
            'emergency_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Emergency contact phone number')
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Employee ID'),
                'readonly': 'readonly' # Employee ID should be generated, not manually entered
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'push_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            if date_of_birth > timezone.now().date():
                raise ValidationError(
                    _("Date of birth cannot be in the future.")
                )
            
            # Calculate age
            today = timezone.now().date()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            
            if age < 13:
                raise ValidationError(
                    _("User must be at least 13 years old.")
                )
        
        return date_of_birth

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            # Validate file size (5MB limit)
            max_size = 5 * 1024 * 1024
            if profile_picture.size > max_size:
                raise ValidationError(
                    _("Profile picture size must not exceed 5MB.")
                )
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if profile_picture.content_type not in allowed_types:
                raise ValidationError(
                    _("Only JPEG, PNG, GIF, and WebP images are allowed.")
                )
        
        return profile_picture


class RoleForm(forms.ModelForm):
    """
    Form for creating and updating roles.
    """
    class Meta:
        model = Role
        fields = [
            'name', 'role_type', 'description', 'permissions',
            'is_system_role', 'hierarchy_level', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Role name')
            }),
            'role_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Role description and responsibilities')
            }),
            'permissions': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 10
            }),
            'is_system_role': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'disabled': 'disabled'  # System roles shouldn't be modified via form
            }),
            'hierarchy_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        help_texts = {
            'hierarchy_level': _('Higher number indicates higher authority (0 = lowest)'),
            'is_system_role': _('System roles are created automatically and cannot be modified.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # System roles should not be editable
        if self.instance and self.instance.is_system_role:
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['role_type'].widget.attrs['disabled'] = True
            self.fields['is_system_role'].widget.attrs['disabled'] = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate role names
            duplicate_roles = Role.objects.filter(name=name)
            if self.instance.pk:
                duplicate_roles = duplicate_roles.exclude(pk=self.instance.pk)
            
            if duplicate_roles.exists():
                raise ValidationError(
                    _("A role with this name already exists.")
                )
        return name

    def clean_role_type(self):
        role_type = self.cleaned_data.get('role_type')
        if role_type:
            # Check for duplicate role types
            duplicate_roles = Role.objects.filter(role_type=role_type)
            if self.instance.pk:
                duplicate_roles = duplicate_roles.exclude(pk=self.instance.pk)
            
            if duplicate_roles.exists():
                raise ValidationError(
                    _("A role with this type already exists.")
                )
        return role_type

    def clean_is_system_role(self):
        # Prevent modification of system role flag
        if self.instance and self.instance.is_system_role:
            return True
        return self.cleaned_data.get('is_system_role')


class UserRoleAssignmentForm(forms.ModelForm):
    """
    Form for assigning roles to users.
    """
    class Meta:
        model = UserRole
        fields = [
            'user', 'role', 'is_primary', 'academic_session', 'context_id'
        ]
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'academic_session': forms.Select(attrs={
                'class': 'form-control'
            }),
            'context_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., class_id, department_id')
            }),
        }
        help_texts = {
            'is_primary': _('Designates the primary role for this user'),
            'context_id': _('Role context identifier (e.g., class_id for teachers)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(status='active')

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        role = cleaned_data.get('role')
        academic_session = cleaned_data.get('academic_session')
        context_id = cleaned_data.get('context_id')
        is_primary = cleaned_data.get('is_primary')

        # Check for duplicate role assignments
        if user and role and academic_session:
            duplicate_assignments = UserRole.objects.filter(
                user=user,
                role=role,
                academic_session=academic_session,
                context_id=context_id
            )
            if self.instance.pk:
                duplicate_assignments = duplicate_assignments.exclude(pk=self.instance.pk)
            
            if duplicate_assignments.exists():
                raise ValidationError(
                    _("This user already has this role assignment for the selected context.")
                )

        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with enhanced styling and validation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'placeholder': _(f'Enter {self.fields[field_name].label.lower()}')
            })


class CustomSetPasswordForm(SetPasswordForm):
    """
    Custom set password form for password reset confirmation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'placeholder': _(f'Enter {self.fields[field_name].label.lower()}')
            })


class ParentStudentRelationshipForm(forms.ModelForm):
    """
    Form for managing parent-student relationships.
    """
    class Meta:
        model = ParentStudentRelationship
        fields = [
            'parent', 'student', 'relationship_type',
            'is_primary_contact', 'can_pickup', 'emergency_contact_order'
        ]
        widgets = {
            'parent': forms.Select(attrs={
                'class': 'form-control'
            }),
            'student': forms.Select(attrs={
                'class': 'form-control'
            }),
            'relationship_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_primary_contact': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_pickup': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'emergency_contact_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10
            }),
        }
        help_texts = {
            'is_primary_contact': _('Designates the primary contact for the student'),
            'can_pickup': _('Can this person pickup the student from school?'),
            'emergency_contact_order': _('Order in which to contact in emergencies (0 = first)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit choices to users with appropriate roles
        from apps.users.models import Role
        parent_role = Role.objects.filter(role_type=Role.RoleType.PARENT).first()
        student_role = Role.objects.filter(role_type=Role.RoleType.STUDENT).first()
        
        if parent_role:
            self.fields['parent'].queryset = User.objects.filter(
                user_roles__role=parent_role,
                is_active=True
            ).distinct()
        
        if student_role:
            self.fields['student'].queryset = User.objects.filter(
                user_roles__role=student_role,
                is_active=True
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        student = cleaned_data.get('student')
        relationship_type = cleaned_data.get('relationship_type')

        if parent and student:
            # Prevent duplicate relationships
            duplicate_relationships = ParentStudentRelationship.objects.filter(
                parent=parent,
                student=student,
                relationship_type=relationship_type
            )
            if self.instance.pk:
                duplicate_relationships = duplicate_relationships.exclude(pk=self.instance.pk)
            
            if duplicate_relationships.exists():
                raise ValidationError(
                    _("This relationship already exists.")
                )
            
            # Prevent self-relationship
            if parent == student:
                raise ValidationError(
                    _("A user cannot have a relationship with themselves.")
                )

        return cleaned_data


class LoginHistorySearchForm(forms.Form):
    """
    Form for searching and filtering login history.
    """
    DATE_RANGE_CHOICES = [
        ('', _('Any Time')),
        ('today', _('Today')),
        ('week', _('This Week')),
        ('month', _('This Month')),
        ('year', _('This Year')),
        ('custom', _('Custom Range')),
    ]

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label=_('User'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    was_successful = forms.ChoiceField(
        choices=[('', _('All')), ('true', _('Successful')), ('false', _('Failed'))],
        required=False,
        label=_('Login Status'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    login_method = forms.ChoiceField(
        choices=[('', _('All Methods'))] + list(LoginHistory._meta.get_field('login_method').choices),
        required=False,
        label=_('Login Method'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        required=False,
        label=_('Date Range'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        label=_('From Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    end_date = forms.DateField(
        required=False,
        label=_('To Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    ip_address = forms.GenericIPAddressField(
        required=False,
        label=_('IP Address'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('192.168.1.1')
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if date_range == 'custom':
            if not start_date or not end_date:
                raise ValidationError(
                    _('Both start date and end date are required for custom date range.')
                )
            if start_date > end_date:
                raise ValidationError(
                    _('Start date cannot be after end date.')
                )

        return cleaned_data


class UserBulkActionForm(forms.Form):
    """
    Form for performing bulk actions on users.
    """
    ACTION_CHOICES = [
        ('activate', _('Activate selected users')),
        ('deactivate', _('Deactivate selected users')),
        ('assign_role', _('Assign role to selected users')),
        ('remove_role', _('Remove role from selected users')),
        ('send_email', _('Send email to selected users')),
    ]

    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': 10
        })
    )
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(status='active'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    email_subject = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Email subject')
        })
    )
    email_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': _('Email message')
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        role = cleaned_data.get('role')
        email_subject = cleaned_data.get('email_subject')
        email_message = cleaned_data.get('email_message')

        if action == 'assign_role' and not role:
            raise ValidationError({
                'role': _('Role is required for assign role action.')
            })
        elif action == 'remove_role' and not role:
            raise ValidationError({
                'role': _('Role is required for remove role action.')
            })
        elif action == 'send_email':
            if not email_subject:
                raise ValidationError({
                    'email_subject': _('Email subject is required for send email action.')
                })
            if not email_message:
                raise ValidationError({
                    'email_message': _('Email message is required for send email action.')
                })

        return cleaned_data


class UserImportForm(forms.Form):
    """
    Form for bulk importing users from CSV/Excel file.
    """
    csv_file = forms.FileField(
        label=_('File'),
        help_text=_('Upload a CSV or Excel file with user data. Required columns: email, first_name, last_name'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    send_welcome_email = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Send welcome email to new users'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    generate_passwords = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Generate random passwords for new users'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # Validate file type
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = None
            for ext in allowed_extensions:
                if csv_file.name.lower().endswith(ext):
                    file_extension = ext
                    break

            if not file_extension:
                raise ValidationError(
                    _("Only CSV (.csv) and Excel (.xlsx, .xls) files are allowed.")
                )

            # Validate file size (10MB limit)
            max_size = 10 * 1024 * 1024
            if csv_file.size > max_size:
                raise ValidationError(
                    _("File size must not exceed 10MB.")
                )

        return csv_file


class UserExportForm(forms.Form):
    """
    Form for exporting user data.
    """
    FORMAT_CHOICES = [
        ('csv', _('CSV')),
        ('excel', _('Excel')),
        ('json', _('JSON')),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    include_inactive = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Include inactive users'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    fields_to_export = forms.MultipleChoiceField(
        choices=[
            ('email', _('Email')),
            ('first_name', _('First Name')),
            ('last_name', _('Last Name')),
            ('mobile', _('Mobile')),
            ('is_active', _('Active Status')),
            ('is_staff', _('Staff Status')),
            ('created_at', _('Created Date')),
            ('last_login', _('Last Login')),
        ],
        initial=['email', 'first_name', 'last_name', 'mobile', 'is_active'],
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': 8
        }),
        label=_('Fields to Export')
    )
    
# apps/users/forms.py (ADD TO EXISTING forms.py)

class StudentApplicationForm(forms.ModelForm):
    """
    Form for student applications with enhanced validation.
    """
    confirm_email = forms.EmailField(
        label=_('Confirm Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm your email address')
        })
    )
    confirm_parent_email = forms.EmailField(
        label=_("Confirm Parent's Email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _("Confirm parent's email address")
        })
    )
    
    class Meta:
        model = StudentApplication
        fields = [
            # Personal Information
            'first_name', 'last_name', 'date_of_birth', 'gender', 'nationality',

            # Contact Information
            'email', 'confirm_email', 'phone', 'address', 'city', 'state',
            'postal_code', 'country',

            # Academic Information
            'grade_applying_for', 'previous_school', 'previous_grade',
            'academic_achievements',

            # Parent/Guardian Information
            'parent_first_name', 'parent_last_name', 'parent_email',
            'confirm_parent_email', 'parent_phone', 'parent_relationship',

            # Documents
            'birth_certificate', 'previous_school_transcript', 'recommendation_letter', 'medical_report',

            # Additional Information
            'medical_conditions', 'special_needs', 'extracurricular_interests',

            # Application Details
            'academic_session'
        ]
        widgets = {
            # Personal Information
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last name')
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nationality')
            }),
            
            # Contact Information
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('student@example.com')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+1234567890')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Full address')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City')
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('State/Province')
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Postal code')
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Country')
            }),
            
            # Academic Information
            'grade_applying_for': forms.Select(attrs={
                'class': 'form-control'
            }),
            'previous_school': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Previous school name')
            }),
            'previous_grade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Previous grade completed')
            }),
            'academic_achievements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Academic achievements, awards, etc.')
            }),
            
            # Parent/Guardian Information
            'parent_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Parent's first name")
            }),
            'parent_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _("Parent's last name")
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('parent@example.com')
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+1234567890')
            }),
            'parent_relationship': forms.Select(attrs={
                'class': 'form-control'
            }),

            # Documents
            'birth_certificate': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'previous_school_transcript': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
            'recommendation_letter': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'medical_report': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),

            # Additional Information
            'medical_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Any medical conditions we should know about')
            }),
            'special_needs': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Any special educational needs')
            }),
            'extracurricular_interests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Sports, arts, clubs, etc.')
            }),
            
            # Application Details
            'academic_session': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        help_texts = {
            'date_of_birth': _('Format: YYYY-MM-DD'),
            'academic_achievements': _('List any academic awards, honors, or special achievements'),
            'medical_conditions': _('This information will be kept confidential'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.academics.models import AcademicSession
        # Only show active academic sessions
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(
            status='active'
        )

        # Make academic session optional
        self.fields['academic_session'].required = False

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        parent_email = cleaned_data.get('parent_email')
        confirm_parent_email = cleaned_data.get('confirm_parent_email')
        date_of_birth = cleaned_data.get('date_of_birth')
        academic_session = cleaned_data.get('academic_session')
        parent_first_name = cleaned_data.get('parent_first_name')
        parent_last_name = cleaned_data.get('parent_last_name')

        # Academic session validation - REMOVED: now optional
        # if not academic_session:
        #     self.add_error('academic_session', _('Please select an academic session.'))

        # Email confirmation validation
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', _('Email addresses do not match.'))

        if parent_email and confirm_parent_email and parent_email != confirm_parent_email:
            self.add_error('confirm_parent_email', _("Parent's email addresses do not match."))

        # Age validation
        if date_of_birth:
            today = timezone.now().date()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )

            # Validate minimum age for school (typically 3+)
            if age < 3:
                self.add_error('date_of_birth', _('Student must be at least 3 years old.'))

            # Validate reasonable maximum age (typically 25 for high school)
            if age > 25:
                self.add_error('date_of_birth', _('Please contact admissions for applicants over 25 years old.'))

        # Check for duplicate applications
        if email and not self.instance.pk:
            existing_app = StudentApplication.objects.filter(
                email=email,
                application_status__in=['pending', 'under_review']
            ).exists()
            if existing_app:
                self.add_error('email', _('An application with this email is already pending review.'))

        # Validate parent names don't look like email addresses
        if parent_first_name and "@" in parent_first_name:
            self.add_error('parent_first_name', _("Parent's first name cannot be an email address."))
        if parent_last_name and "@" in parent_last_name:
            self.add_error('parent_last_name', _("Parent's last name cannot be an email address."))

        # Auto-fill parent names if parent email matches student email
        if parent_email and email and parent_email.lower() == email.lower():
            # If parent email is same as student email, they might be the same person
            # Auto-fill parent names or enforce proper names
            if not parent_first_name:
                cleaned_data['parent_first_name'] = "Parent"
            if not parent_last_name:
                # Use student's last name for parent
                cleaned_data['parent_last_name'] = cleaned_data.get('last_name', "Guardian")

        return cleaned_data

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Basic phone validation
            if len(phone) < 10:
                raise forms.ValidationError(_('Please enter a valid phone number.'))
        return phone

    def clean_parent_phone(self):
        phone = self.cleaned_data.get('parent_phone')
        if phone:
            if len(phone) < 10:
                raise forms.ValidationError(_('Please enter a valid phone number.'))
        return phone

    def clean_birth_certificate(self):
        birth_certificate = self.cleaned_data.get('birth_certificate')
        if birth_certificate:
            # File type validation
            valid_types = ['application/pdf', 'image/jpeg', 'image/png']
            if birth_certificate.content_type not in valid_types:
                raise forms.ValidationError(_('Only PDF, JPG, and PNG files are allowed for birth certificate.'))

            # File size validation (5MB)
            if birth_certificate.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Birth certificate file size must not exceed 5MB.'))

        return birth_certificate

    def clean_previous_school_transcript(self):
        transcript = self.cleaned_data.get('previous_school_transcript')
        if transcript:
            # File type validation
            if transcript.content_type != 'application/pdf':
                raise forms.ValidationError(_('Only PDF files are allowed for school transcript.'))

            # File size validation (5MB)
            if transcript.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Transcript file size must not exceed 5MB.'))

        return transcript

    def clean_recommendation_letter(self):
        recommendation = self.cleaned_data.get('recommendation_letter')
        if recommendation:
            # File type validation
            valid_types = ['application/pdf', 'application/msword',
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if recommendation.content_type not in valid_types:
                raise forms.ValidationError(_('Only PDF, DOC, and DOCX files are allowed for recommendation letter.'))

            # File size validation (5MB)
            if recommendation.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Recommendation letter file size must not exceed 5MB.'))

        return recommendation

    def clean_medical_report(self):
        medical_report = self.cleaned_data.get('medical_report')
        if medical_report:
            # File type validation
            if medical_report.content_type != 'application/pdf':
                raise forms.ValidationError(_('Only PDF files are allowed for medical report.'))

            # File size validation (5MB)
            if medical_report.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Medical report file size must not exceed 5MB.'))

        return medical_report

    def save(self, commit=True):
        """
        Custom save method to handle the confirmation fields
        """
        # Remove confirmation fields before saving
        self.cleaned_data.pop('confirm_email', None)
        self.cleaned_data.pop('confirm_parent_email', None)
        return super().save(commit=commit)


class StaffApplicationForm(forms.ModelForm):
    """
    Form for staff applications with file upload validation.
    """
    confirm_email = forms.EmailField(
        label=_('Confirm Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm your email address')
        })
    )
    
    class Meta:
        model = StaffApplication
        fields = [
            # Personal Information
            'first_name', 'last_name', 'date_of_birth', 'gender', 'nationality',
            
            # Contact Information
            'email', 'confirm_email', 'phone', 'address', 'city', 'state',
            'postal_code', 'country',
            
            # Professional Information
            'position_applied_for', 'position_type', 'expected_salary',
            
            # Educational Background
            'highest_qualification', 'institution', 'year_graduated',
            
            # Professional Experience
            'years_of_experience', 'previous_employer', 'previous_position',

            # Documents
            'cv', 'cover_letter', 'certificates',

            # References
            'reference1_name', 'reference1_position', 'reference1_contact',
            'reference2_name', 'reference2_position', 'reference2_contact',
            
            # Application Details
            'academic_session'
        ]
        widgets = {
            # Personal Information
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last name')
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nationality')
            }),
            
            # Contact Information
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('applicant@example.com')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+1234567890')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Full address')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City')
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('State/Province')
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Postal code')
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Country')
            }),
            
            # Professional Information
            'position_applied_for': forms.Select(attrs={
                'class': 'form-control'
            }),
            'position_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'expected_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Expected salary')
            }),
            
            # Educational Background
            'highest_qualification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Highest degree or qualification')
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Name of institution')
            }),
            'year_graduated': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Year graduated'),
                'min': 1950,
                'max': timezone.now().year
            }),
            
            # Professional Experience
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 50
            }),
            'previous_employer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Previous employer')
            }),
            'previous_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Previous position')
            }),
            
            # Documents
            'cv': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'cover_letter': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'certificates': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            
            # References
            'reference1_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 1 full name')
            }),
            'reference1_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 1 position')
            }),
            'reference1_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 1 email or phone')
            }),
            'reference2_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 2 full name (optional)')
            }),
            'reference2_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 2 position (optional)')
            }),
            'reference2_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference 2 email or phone (optional)')
            }),
            
            # Application Details
            'academic_session': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        help_texts = {
            'cv': _('Upload your CV (PDF, DOC, DOCX, max 5MB)'),
            'cover_letter': _('Upload your cover letter (optional)'),
            'certificates': _('Upload relevant certificates (optional)'),
            'expected_salary': _('Enter your expected salary (optional)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.academics.models import AcademicSession

        # Only show active academic sessions
        self.fields['academic_session'].queryset = AcademicSession.objects.filter(
            status='active'
        )

        # FIX: Populate position_applied_for with ALL active staff roles
        self.fields['position_applied_for'].queryset = Role.objects.filter(
            role_type__in=Role.STAFF_ROLES,
            status='active'
        ).order_by('name')

        # Make academic session optional, but CV required
        self.fields['academic_session'].required = False
        self.fields['cv'].required = True

        # Add empty label for dropdowns
        self.fields['position_applied_for'].empty_label = _("Select a position")
        self.fields['academic_session'].empty_label = _("Select academic session")
        self.fields['position_type'].empty_label = _("Select position type")
        self.fields['gender'].empty_label = _("Select gender")

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        date_of_birth = cleaned_data.get('date_of_birth')
        year_graduated = cleaned_data.get('year_graduated')
        years_of_experience = cleaned_data.get('years_of_experience')
        academic_session = cleaned_data.get('academic_session')

        # Academic session validation - REMOVED: now optional
        # if not academic_session:
        #     self.add_error('academic_session', _('Please select an academic session.'))

        # Email confirmation validation
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', _('Email addresses do not match.'))

        # Age validation (minimum working age)
        if date_of_birth:
            today = timezone.now().date()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            
            if age < 18:
                self.add_error('date_of_birth', _('Applicant must be at least 18 years old.'))
            
            if age > 70:
                self.add_error('date_of_birth', _('Please contact HR for applicants over 70 years old.'))

        # Year graduated validation
        if year_graduated:
            current_year = timezone.now().year
            if year_graduated > current_year:
                self.add_error('year_graduated', _('Year graduated cannot be in the future.'))
            
            if year_graduated < 1950:
                self.add_error('year_graduated', _('Please enter a valid graduation year.'))

        # Experience validation
        if years_of_experience and years_of_experience > 50:
            self.add_error('years_of_experience', _('Please enter a reasonable number of years of experience.'))

        # Check for duplicate applications
        if email and not self.instance.pk:
            existing_app = StaffApplication.objects.filter(
                email=email,
                application_status__in=['pending', 'under_review']
            ).exists()
            if existing_app:
                self.add_error('email', _('An application with this email is already pending review.'))

        return cleaned_data

    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if cv:
            # File type validation
            valid_types = ['application/pdf', 'application/msword', 
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if cv.content_type not in valid_types:
                raise forms.ValidationError(_('Only PDF, DOC, and DOCX files are allowed for CV.'))
            
            # File size validation (5MB)
            if cv.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('CV file size must not exceed 5MB.'))
        
        return cv

    def clean_cover_letter(self):
        cover_letter = self.cleaned_data.get('cover_letter')
        if cover_letter:
            valid_types = ['application/pdf', 'application/msword', 
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if cover_letter.content_type not in valid_types:
                raise forms.ValidationError(_('Only PDF, DOC, and DOCX files are allowed for cover letter.'))
            
            if cover_letter.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Cover letter file size must not exceed 5MB.'))
        
        return cover_letter

    def clean_certificates(self):
        certificates = self.cleaned_data.get('certificates')
        if certificates:
            valid_types = ['application/pdf', 'application/msword', 
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         'image/jpeg', 'image/png']
            if certificates.content_type not in valid_types:
                raise forms.ValidationError(_('Only PDF, DOC, DOCX, JPG, and PNG files are allowed for certificates.'))
            
            if certificates.size > 10 * 1024 * 1024:  # 10MB for certificates
                raise forms.ValidationError(_('Certificates file size must not exceed 10MB.'))
        
        return certificates

    def save(self, commit=True):
        """
        Custom save method to handle the confirmation field
        """
        # Remove confirmation field before saving
        self.cleaned_data.pop('confirm_email', None)
        return super().save(commit=commit)
