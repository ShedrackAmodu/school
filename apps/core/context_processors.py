from .middleware import get_current_institution


def tenant_context(request):
    """
    Context processor to add current institution information to all templates.
    """
    institution = get_current_institution()

    context = {
        'current_institution': institution,
        'institution_name': institution.name if institution else None,
        'institution_code': institution.code if institution else None,
        'institution_short_name': institution.short_name if institution else None,
    }

    # Add branding information if institution exists
    if institution:
        context.update({
            'institution_logo': institution.logo if hasattr(institution, 'logo') else None,
            'institution_theme': getattr(institution, 'theme', {}).get('primary_color', '#007bff'),
            'institution_timezone': institution.timezone,
            'institution_website': institution.website,
            'institution_email': institution.email,
            'institution_phone': institution.phone,
        })

    return context
