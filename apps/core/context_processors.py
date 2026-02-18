import logging
from .middleware import get_current_institution
from .models import Institution

logger = logging.getLogger(__name__)


def tenant_context(request):
    """
    Context processor for single-tenancy information.
    Always returns Excellent Academy as the only institution.
    """
    current_inst = get_current_institution()

    return {
        'tenant_institution': current_inst,
        'user_institutions': Institution.objects.filter(code='EXCELLENT_ACADEMY', is_active=True),
        'multi_tenant_enabled': False,
        'single_tenant_mode': True,
        'can_switch_institutions': False,
    }


def current_institution(request):
    """
    Context processor to add current institution (Excellent Academy) to all template contexts.
    In single-tenant mode this is always Excellent Academy.
    """
    try:
        institution = get_current_institution()
        if institution:
            return {
                'current_institution': institution,
                'institution_code': institution.code,
                'institution_name': institution.name,
                'institution_theme': getattr(institution, 'theme', None),
            }
        else:
            # Fallback: try to load directly
            try:
                institution = Institution.objects.get(code='EXCELLENT_ACADEMY', is_active=True)
                return {
                    'current_institution': institution,
                    'institution_code': institution.code,
                    'institution_name': institution.name,
                    'institution_theme': None,
                }
            except Institution.DoesNotExist:
                pass

        return {
            'current_institution': None,
            'institution_code': 'EXCELLENT_ACADEMY',
            'institution_name': 'Excellent Academy',
            'institution_theme': None,
        }
    except Exception as e:
        logger.warning(f"Error in current_institution context processor: {e}")
        return {
            'current_institution': None,
            'institution_code': 'EXCELLENT_ACADEMY',
            'institution_name': 'Excellent Academy',
            'institution_theme': None,
        }
