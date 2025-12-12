import threading
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from .models import Institution


# Thread-local storage for current institution
_local = threading.local()


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to handle multi-tenancy by identifying the current institution
    from request context (subdomain, session, or user profile).
    """

    def process_request(self, request):
        """
        Set the current institution for this request.
        Priority order:
        1. Subdomain (e.g., school1.domain.com)
        2. Session institution
        3. User's primary institution
        4. Default institution (if configured)
        """
        institution = None

        # Check subdomain
        institution = self._get_institution_from_subdomain(request)

        # If no subdomain match, check session
        if not institution:
            institution = self._get_institution_from_session(request)

        # If still no match, check user profile
        if not institution and request.user.is_authenticated:
            institution = self._get_institution_from_user(request.user)

        # Set the current institution in thread-local storage
        if institution:
            _local.current_institution = institution
            # Also store in request for convenience
            request.institution = institution
            # Store in session for persistence across requests
            request.session['current_institution_id'] = str(institution.id)
            request.session.modified = True
        else:
            # No institution found - store None
            _local.current_institution = None
            request.institution = None
            # Clear session institution if it exists
            if 'current_institution_id' in request.session:
                del request.session['current_institution_id']

        return None

    def process_response(self, request, response):
        """
        Clean up thread-local storage after request processing.
        """
        if hasattr(_local, 'current_institution'):
            del _local.current_institution
        return response

    def _get_institution_from_subdomain(self, request):
        """
        Extract institution from subdomain.
        Expected format: institution-code.domain.com
        """
        host = request.get_host().lower()
        domain = getattr(settings, 'TENANT_DOMAIN', 'localhost')

        # Remove port if present
        if ':' in host:
            host = host.split(':')[0]

        # Check if host ends with our domain
        if host.endswith(domain):
            subdomain = host.replace(f'.{domain}', '').replace(domain, '')

            if subdomain and subdomain != 'www':
                try:
                    return Institution.objects.get(
                        code__iexact=subdomain,
                        is_active=True
                    )
                except Institution.DoesNotExist:
                    pass

        return None

    def _get_institution_from_session(self, request):
        """
        Get institution from session if stored.
        """
        institution_id = request.session.get('current_institution_id')
        if institution_id:
            try:
                return Institution.objects.get(
                    id=institution_id,
                    is_active=True
                )
            except Institution.DoesNotExist:
                # Clean up invalid session data
                if 'current_institution_id' in request.session:
                    del request.session['current_institution_id']

        return None

    def _get_institution_from_user(self, user):
        """
        Get institution from user's current or primary institution via InstitutionUser relationship.
        """
        from .models import InstitutionUser

        # First try to get current session institution from related field
        # Since we can't add foreign keys directly to User model due to circular imports,
        # we'll get the active institution from the session or user's primary institution

        # Try to find the user's primary institution through InstitutionUser
        try:
            primary_membership = InstitutionUser.objects.filter(
                user=user,
                is_primary=True,
                institution__is_active=True
            ).select_related('institution').first()

            if primary_membership:
                return primary_membership.institution
        except:
            pass

        # If no primary found, get the first active institution the user belongs to
        try:
            membership = InstitutionUser.objects.filter(
                user=user,
                institution__is_active=True
            ).select_related('institution').first()

            if membership:
                return membership.institution
        except:
            pass

        return None


def get_current_institution():
    """
    Get the current institution from thread-local storage.
    Returns None if no institution is set.
    """
    return getattr(_local, 'current_institution', None)


def set_current_institution(institution):
    """
    Manually set the current institution in thread-local storage.
    Use with caution - typically handled by middleware.
    """
    _local.current_institution = institution
