import logging
from .middleware import get_current_institution, get_user_accessible_institutions
from .models import Institution

logger = logging.getLogger(__name__)


def tenant_context(request):
    """
    Context processor for tenant/single-tenancy information.
    In single-tenant mode, always returns Excellent Academy.
    """
    current_inst = get_current_institution()
    user_institutions = get_user_accessible_institutions(request.user) if request.user.is_authenticated else Institution.objects.none()

    return {
        'tenant_institution': current_inst,
        'user_institutions': user_institutions,
        'multi_tenant_enabled': False,
        'single_tenant_mode': True,
    }


def current_institution(request):
    """
    Context processor to add current institution information to all template contexts.
    In single-tenant mode, this is always Excellent Academy.
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
