import logging
from .middleware import get_current_institution
from .models import Institution

logger = logging.getLogger(__name__)


def tenant_context(request):
    """
    Context processor for tenancy information.
    Returns all active institutions (single-tenant deployments will typically have one).
    """
    current_inst = get_current_institution()

    return {
        'tenant_institution': current_inst,
        'user_institutions': Institution.objects.filter(is_active=True),
        'multi_tenant_enabled': False,
        'single_tenant_mode': True,
        'can_switch_institutions': False,
    }


def current_institution(request):
    """
    Context processor to add current institution to all template contexts.
    Attempts to use the institution set on the request; falls back to first active institution.
    """
    try:
        institution = get_current_institution()
        if not institution:
            institution = Institution.objects.filter(is_active=True).first()

        if institution:
            return {
                'current_institution': institution,
                'institution_code': institution.code,
                'institution_name': institution.name,
                'institution_theme': getattr(institution, 'theme', None),
            }

        return {
            'current_institution': None,
            'institution_code': None,
            'institution_name': None,
            'institution_theme': None,
        }
    except Exception as e:
        logger.warning(f"Error in current_institution context processor: {e}")
        return {
            'current_institution': None,
            'institution_code': None,
            'institution_name': None,
            'institution_theme': None,
        }
