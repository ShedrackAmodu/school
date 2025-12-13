from django.contrib.auth.mixins import AccessMixin
from django.http import Http404
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .middleware import (
    get_current_institution,
    user_can_access_institution,
    filter_queryset_by_institution,
    get_user_accessible_institutions
)


class InstitutionAccessMixin(AccessMixin):
    """
    Mixin to ensure user has access to the current institution.
    Should be used with views that operate within institution context.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        institution = get_current_institution()

        if not institution:
            # No institution context - redirect to institution selection
            messages.warning(request, _("Please select an institution to continue."))
            return redirect('core:institution_select')

        # Check if user can access this institution
        if not user_can_access_institution(request.user, institution):
            messages.error(request, _("You don't have permission to access this institution."))
            return redirect('users:dashboard')

        return super().dispatch(request, *args, **kwargs)


class InstitutionPermissionMixin(InstitutionAccessMixin):
    """
    Mixin that filters querysets by institution and ensures user permissions.
    Use for views that list or manipulate institution-specific data.
    """

    def get_queryset(self):
        """
        Filter queryset to only show records from institutions the user can access.
        """
        queryset = super().get_queryset()
        return filter_queryset_by_institution(queryset, self.request.user)

    def form_valid(self, form):
        """
        Ensure the form instance is saved with the current institution.
        Assumes the model has an 'institution' field.
        """
        form.instance.institution = get_current_institution()
        return super().form_valid(form)


class InstitutionAdminMixin(InstitutionAccessMixin):
    """
    Mixin for views that require institution admin privileges.
    """

    def dispatch(self, request, *args, **kwargs):
        # First check institution access
        result = super().dispatch(request, *args, **kwargs)
        if not isinstance(result, type(None)):
            return result  # Permission denied or redirect

        # Check if user has admin role in current institution
        institution = get_current_institution()
        user_roles = request.user.user_roles.filter(
            role__hierarchy_level__gte=70,  # Principal level and above
            academic_session__is_current=True
        )

        if not user_roles.exists():
            messages.error(request, _("You need institution admin privileges to access this page."))
            return redirect('users:dashboard')

        return super().dispatch(request, *args, **kwargs)


class SuperAdminMixin(AccessMixin):
    """
    Mixin for views that require super admin (platform-level) privileges.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_superuser:
            messages.error(request, _("You need super administrator privileges to access this page."))
            return redirect('users:dashboard')

        return super().dispatch(request, *args, **kwargs)


class InstitutionFormMixin:
    """
    Mixin for forms that need institution field handling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.pop('user', None)

        # If user is not super admin, limit institution choices
        if self.user and not self.user.is_superuser:
            from .models import InstitutionUser
            accessible_institutions = InstitutionUser.objects.filter(
                user=self.user,
                institution__is_active=True
            ).values_list('institution', flat=True)

            if 'institution' in self.fields:
                self.fields['institution'].queryset = self.fields['institution'].queryset.filter(
                    id__in=accessible_institutions
                )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set institution for new instances if not set
        if not getattr(instance, 'institution', None):
            if self.user and self.user.is_superuser:
                # Super admin can have instances without institution (for global config)
                pass
            else:
                # Set to current institution for regular users
                current_institution = get_current_institution()
                if current_institution:
                    instance.institution = current_institution

        if commit:
            instance.save()
        return instance


class MultiInstitutionMixin:
    """
    Mixin for views that need to handle multiple institutions (e.g., super admin dashboard).
    Adds context data for institution switching.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # Add accessible institutions
        context['accessible_institutions'] = get_user_accessible_institutions(user)
        context['current_institution'] = get_current_institution()

        # Add institution switcher flag
        context['can_switch_institutions'] = user.is_superuser or context['accessible_institutions'].count() > 1

        return context


def institution_required(view_func):
    """
    Decorator to ensure user has access to current institution.
    Usage: @institution_required
    def my_view(request):
        pass
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        institution = get_current_institution()
        if not institution:
            messages.warning(request, _("Please select an institution to continue."))
            return redirect('core:institution_select')

        if not user_can_access_institution(request.user, institution):
            messages.error(request, _("You don't have permission to access this institution."))
            return redirect('users:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def institution_admin_required(view_func):
    """
    Decorator to ensure user has institution admin privileges.
    """
    def wrapper(request, *args, **kwargs):
        # First check institution access
        result = institution_required(lambda r: None)(request, *args, **kwargs)
        if result:
            return result

        # Check admin role
        institution = get_current_institution()
        user_roles = request.user.user_roles.filter(
            role__hierarchy_level__gte=70,
            academic_session__is_current=True
        )

        if not user_roles.exists():
            messages.error(request, _("You need institution admin privileges to access this page."))
            return redirect('users:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def super_admin_required(view_func):
    """
    Decorator to ensure user has super admin privileges.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        if not request.user.is_superuser:
            messages.error(request, _("You need super administrator privileges to access this page."))
            return redirect('users:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper
