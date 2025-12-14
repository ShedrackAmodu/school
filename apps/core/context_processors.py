import logging
from .middleware import get_current_institution, get_user_accessible_institutions
from .models import Institution

logger = logging.getLogger(__name__)


def tenant_context(request):
    """
    Context processor for tenant/multi-tenancy information (legacy function).
    """
    current_inst = get_current_institution()
    user_institutions = []

    if request.user.is_authenticated:
        user_institutions = get_user_accessible_institutions(request.user)

    return {
        'tenant_institution': current_inst,
        'user_institutions': user_institutions,
        'multi_tenant_enabled': True,
    }


def current_institution(request):
    """
    Context processor to add current institution information to all template contexts.
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
