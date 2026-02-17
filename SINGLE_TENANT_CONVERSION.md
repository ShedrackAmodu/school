# Single-Tenant Conversion to Excellent Academy

## Overview
This document outlines the conversion of the NexusSMS project from a multi-tenant system to a single-tenant dedicated system for **Excellent Academy**.

## Conversion Date
February 17, 2026

## Changes Made

### 1. Database Layer
- **Created Migration**: `apps/core/migrations/0003_create_excellent_academy.py`
  - Automatically creates the Institution record for "Excellent Academy"
  - Code: `EXCELLENT_ACADEMY`
  - Institution Type: High School
  - Status: Active

### 2. Configuration Changes
**File**: `config/settings.py`

#### Removed
- `TENANT_SUBDOMAIN_ENABLED = True` → Now `False`
- `ALLOW_INSTITUTION_SWITCHING = True` → Now `False`
- `INSTITUTION_BRANDING_ENABLED = True` → Now `False`
- Multi-tenant context in middleware

#### Added
```python
SINGLE_TENANT_MODE = True
DEFAULT_INSTITUTION_CODE = 'EXCELLENT_ACADEMY'
DEFAULT_INSTITUTION_NAME = 'Excellent Academy'
TENANT_SUBDOMAIN_ENABLED = False
ALLOW_INSTITUTION_SWITCHING = False
INSTITUTION_BRANDING_ENABLED = False
TENANT_DATA_ISOLATION = False
```

### 3. Middleware Changes
**File**: `apps/core/middleware.py`

#### Simplified TenantMiddleware
- Removed subdomain detection logic
- Removed session-based institution switching
- Removed user primary institution lookup
- Now always returns "Excellent Academy" institution
- Maintains thread-local storage for backward compatibility

#### Updated Functions
- `get_default_institution()`: Returns Excellent Academy
- `get_user_accessible_institutions()`: Returns only Excellent Academy
- `user_can_access_institution()`: Returns True for all authenticated users
- `filter_queryset_by_institution()`: Filters by Excellent Academy only

### 4. Views Removal
**File**: `apps/core/views.py`

#### Removed Views
- `InstitutionListView`
- `InstitutionCreateView`
- `InstitutionUpdateView`
- `InstitutionDeleteView`
- `InstitutionConfigOverrideView`
- `InstitutionSwitcherView`

#### Simplified Views
- `InstitutionDetailView`: Now always shows Excellent Academy details

### 5. URL Routing Changes
**File**: `apps/core/urls.py`

#### Removed URLs
- `institution/select/` - Institution switcher
- `institutions/` - Institution list
- `institutions/create/` - Institution creation
- `institutions/<uuid:pk>/update/` - Institution update
- `institutions/<uuid:pk>/delete/` - Institution delete
- `institutions/<uuid:pk>/config-overrides/` - Config overrides

#### Simplified URLs
- `institution/` - Now shows Excellent Academy details

### 6. User/Forms Changes
**File**: `apps/users/forms.py`

#### Removed Forms
- `InstitutionTransferRequestForm`

#### Simplified Mixin
- `InstitutionFormMixin`: Now does nothing (single-tenant, no filtering needed)

### 7. Admin Interface Changes
**File**: `apps/users/admin.py`

#### Removed Admin Classes
- `InstitutionTransferRequestAdmin`

#### Removed Imports
- `InstitutionTransferRequest` model import removed

### 8. User URLs Changes
**File**: `apps/users/urls.py`

#### Removed URLs
- `transfer-request/` - Transfer request form
- `transfer-request/student/` - Student transfer
- `transfer-request/staff/` - Staff transfer
- `transfer-requests/` - User transfer requests list
- `transfer-request/<uuid:request_id>/` - Transfer detail
- `admin/transfer-requests/` - Admin transfer list
- `admin/transfer-request/<uuid:request_id>/approve/` - Approve transfer
- `admin/transfer-request/<uuid:request_id>/reject/` - Reject transfer
- `admin/transfer-request/<uuid:request_id>/complete/` - Complete transfer

### 9. Context Processors
**File**: `apps/core/context_processors.py`

#### Updates
- `tenant_context()`: Updated to indicate single-tenant mode
- `current_institution()`: Simplified to always return Excellent Academy

### 10. Forms/Mixins
**File**: `apps/core/forms.py`

#### Updated
- `InstitutionFormMixin`: Simplified for single-tenant mode
- No filtering by accessible institutions needed

## Preserved Components

### Models (Not Removed)
The following models remain intact to preserve database schema:
- `InstitutionTransferRequest` - Kept for backward compatibility
- `InstitutionUser` - Kept for user-institution mapping
- All models with `institution` foreign key

These models are no longer actively used but remain in the codebase to avoid complex migration issues.

### Templates
- Main functionality templates preserved
- Institution-related admin templates may need cleanup (scheduled for future maintenance)

## Migration Steps

```bash
# Run migrations to create Excellent Academy institution
python manage.py migrate

# Create a superuser for administration
python manage.py createsuperuser

# Run tests to verify functionality
python manage.py test
```

## Configuration for Production

Update these settings in `config/settings.py` for your production environment:

```python
# Database (recommend PostgreSQL for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'excellent_academy',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Email Configuration
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'

# Paystack Configuration
PAYSTACK_SECRET_KEY = 'your-secret-key'
PAYSTACK_PUBLIC_KEY = 'your-public-key'

# SMS Configuration (Termii)
TERMII_API_KEY = 'your-termii-api-key'
```

## Security Considerations

1. **Institution Variable**: While `institution_id` is no longer needed in user-facing logic, keep the Institution model for data isolation if you ever need to migrate back to multi-tenant.

2. **Audit Logging**: All changes are logged via the Audit app. Review audit logs regularly.

3. **Access Control**: Without institution switching, role-based permissions become even more critical. Ensure roles are properly configured.

## Backward Compatibility Notes

- Applications expecting `request.institution` will still work
- All models still have `institution` foreign key pointing to Excellent Academy
- Admin interface preserved where applicable

## Future Considerations

If you need to revert to multi-tenant mode:
1. The Institution and InstitutionUser models are still present
2. Middleware logic can be restored from version control
3. Views and URLs can be restored from version control

All original multi-tenant code patterns are preserved in git history.

## Testing Recommendations

1. Test all core functionality works with single institution
2. Verify user authentication and role-based access
3. Test financial transactions (Paystack integration)
4. Verify email and SMS notifications
5. Check audit logging functionality
6. Validate all report generation

## Support

For issues or questions about this conversion, refer to:
- Original multi-tenant implementation in git history
- `config/settings.py` for configuration options
- Middleware and context processor documentation
