# apps/core/admin.py

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from .models import (SystemConfig, SequenceGenerator)

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for SystemConfig model.
    """
    list_display = ('key', 'config_type', 'is_public', 'is_encrypted', 'status')
    list_filter = ('config_type', 'is_public', 'is_encrypted', 'status', 'created_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Configuration Details'), {
            'fields': ('key', 'value', 'config_type', 'description')
        }),
        (_('Security & Visibility'), {
            'fields': ('is_public', 'is_encrypted'),
            'classes': ('collapse',)
        }),
        (_('System Metadata'), {
            'fields': ('status', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make key read-only for existing objects."""
        if obj:
            return self.readonly_fields + ('key', 'config_type')
        return self.readonly_fields


@admin.register(SequenceGenerator)
class SequenceGeneratorAdmin(admin.ModelAdmin):
    """
    Admin interface for SequenceGenerator model.
    """
    list_display = ('sequence_type', 'prefix', 'suffix', 'last_number', 'padding', 'reset_frequency', 'status')
    list_filter = ('reset_frequency', 'status')
    search_fields = ('sequence_type',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Sequence Configuration'), {
            'fields': ('sequence_type', 'prefix', 'suffix', 'padding', 'reset_frequency')
        }),
        (_('Current State'), {
            'fields': ('last_number',),
            'classes': ('collapse',)
        }),
        (_('System Metadata'), {
            'fields': ('status', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make sequence_type read-only for existing objects."""
        if obj:
            return self.readonly_fields + ('sequence_type',)
        return self.readonly_fields


# Register Permission model if not already registered
if not admin.site.is_registered(Permission):
    @admin.register(Permission)
    class PermissionAdmin(admin.ModelAdmin):
        """
        Admin interface for Django Permission model.
        """
        list_display = ('name', 'content_type', 'codename')
        list_filter = ('content_type',)
        search_fields = ('name', 'codename')
        
        def has_add_permission(self, request):
            """Prevent manual creation of permissions."""
            return False
        
        def has_change_permission(self, request, obj=None):
            """Prevent modification of permissions."""
            return False
        
        def has_delete_permission(self, request, obj=None):
            """Prevent deletion of permissions."""
            return False


class CoreAdminSite(admin.AdminSite):
    """
    Custom admin site for Core app.
    """
    site_header = _('Core Administration')
    site_title = _('Core Admin')
    index_title = _('Core Management')


# Create instance of custom admin site
core_admin_site = CoreAdminSite(name='core_admin')

# Register models with custom admin site
core_admin_site.register(SystemConfig, SystemConfigAdmin)
core_admin_site.register(SequenceGenerator, SequenceGeneratorAdmin)
core_admin_site.register(Permission, PermissionAdmin)