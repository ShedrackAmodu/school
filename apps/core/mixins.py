from django.contrib.auth.mixins import AccessMixin
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
    Mixin to ensure user has access to the current institution (Excellence Academy).
    In single-tenant mode, all authenticated users have access.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        institution = get_current_institution()

        if not institution:
            # In single-tenant mode, if no institution is found it's a setup issue.
            # Redirect to dashboard with error instead of an institution-select page.
            messages.error(
                request,
                _("System configuration error: Excellence Academy institution not found. "
                  "Please run: python manage.py migrate")
            )
            return redirect('users:dashboard')

        return super().dispatch(request, *args, **kwargs)


class InstitutionPermissionMixin(InstitutionAccessMixin):
    """
    Mixin that filters querysets by the single institution (Excellence Academy).
    """

    def get_queryset(self):
        """Filter queryset to only show records from Excellence Academy."""
        queryset = super().get_queryset()
        return filter_queryset_by_institution(queryset, self.request.user)

    def form_valid(self, form):
        """Ensure the form instance is saved with Excellence Academy as institution."""
        form.instance.institution = get_current_institution()
        return super().form_valid(form)


class InstitutionAdminMixin(InstitutionAccessMixin):
    """
    Mixin for views that require institution admin privileges.
    """

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        # If super returned a redirect (permission denied), pass it through
        if hasattr(result, 'status_code') and result.status_code in (301, 302):
            return result

        # Check if user has admin role in current institution
        user_roles = request.user.user_roles.filter(
            role__hierarchy_level__gte=70,  # Principal level and above
            academic_session__is_current=True
        )

        if not user_roles.exists() and not request.user.is_superuser:
            messages.error(request, _("You need institution admin privileges to access this page."))
            return redirect('users:dashboard')

        return result


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
    In single-tenant mode, always assigns Excellence Academy.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.pop('user', None) if 'user' in kwargs else getattr(self, 'user', None)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Always set institution to Excellence Academy for new instances
        if not getattr(instance, 'institution_id', None):
            current_institution = get_current_institution()
            if current_institution:
                instance.institution = current_institution

        if commit:
            instance.save()
        return instance


class MultiInstitutionMixin:
    """
    Mixin for views that previously handled multiple institutions.
    In single-tenant mode, always returns Excellence Academy only.
    Institution switching is always disabled.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        institution = get_current_institution()

        # In single-tenant mode: only one institution, no switching
        context['accessible_institutions'] = get_user_accessible_institutions(user)
        context['current_institution'] = institution
        # Always False in single-tenant mode
        context['can_switch_institutions'] = False

        return context


def institution_required(view_func):
    """
    Decorator to ensure user has access to current institution.
    In single-tenant mode, redirects to dashboard if institution not configured.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        institution = get_current_institution()
        if not institution:
            messages.error(
                request,
                _("System configuration error: Excellence Academy institution not found.")
            )
            return redirect('users:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def institution_admin_required(view_func):
    """
    Decorator to ensure user has institution admin privileges.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        institution = get_current_institution()
        if not institution:
            messages.error(request, _("System configuration error: institution not found."))
            return redirect('users:dashboard')

        # Check admin role
        user_roles = request.user.user_roles.filter(
            role__hierarchy_level__gte=70,
            academic_session__is_current=True
        )

        if not user_roles.exists() and not request.user.is_superuser:
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
