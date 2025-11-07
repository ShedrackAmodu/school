from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AuditLog



@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for AuditLog model.
    """
    list_display = ('user', 'action', 'model_name', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp', 'user')
    search_fields = ('user__email', 'model_name', 'object_id', 'ip_address')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'details', 
                      'ip_address', 'user_agent', 'timestamp', 'created_at', 'updated_at')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        (_('Audit Information'), {
            'fields': ('user', 'action', 'model_name', 'object_id', 'timestamp')
        }),
        (_('Technical Details'), {
            'fields': ('details', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        (_('System Metadata'), {
            'fields': ('status', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion only for superusers."""
        return request.user.is_superuser
