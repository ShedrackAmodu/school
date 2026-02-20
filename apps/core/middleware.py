import threading
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .models import Institution


# Thread-local storage for current institution
_local = threading.local()


def get_default_institution():
    """Return the primary institution for this deployment.

    This no longer assumes a pre-created default institution code. If any
    active Institution exists, return the first one; otherwise return None.
    """
    return Institution.objects.filter(is_active=True).first()


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware for single-tenant mode. Always sets the same institution.
    """

    def process_request(self, request):
        """Set the default institution for this request."""
        institution = get_default_institution()

        if institution:
            _local.current_institution = institution
            request.institution = institution
        else:
            _local.current_institution = None
            request.institution = None

        return None

    def process_response(self, request, response):
        """Clean up thread-local storage after request processing."""
        if hasattr(_local, 'current_institution'):
            del _local.current_institution
        return response


def get_current_institution():
    """
    Get the current institution from thread-local storage.
    In single-tenant mode, this returns the configured institution (if any).
    """
    return getattr(_local, 'current_institution', None)


def set_current_institution(institution):
    """
    Manually set the current institution in thread-local storage.
    (Generally not needed in single-tenant mode)
    """
    _local.current_institution = institution


def user_can_access_institution(user, institution):
    """
    In single-tenant mode, all authenticated users can access the single institution.
    """
    return user.is_authenticated


def filter_queryset_by_institution(queryset, user, institution_field='institution'):
    """
    In single-tenant mode, filter by the default institution only.
    """
    default_inst = get_default_institution()
    if default_inst:
        filter_kwargs = {f'{institution_field}': default_inst}
        return queryset.filter(**filter_kwargs)
    return queryset


def get_user_accessible_institutions(user):
    """
    In single-tenant mode, return all active institutions (single site typically).
    """
    return Institution.objects.filter(is_active=True)
