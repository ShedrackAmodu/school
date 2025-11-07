from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views


urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # Home page redirect - based on authentication status
    path('', RedirectView.as_view(pattern_name='users:guest_home'), name='home'),
    
    # Users app (authentication, profiles, user management)
    path('users/', include('apps.users.urls')),
    
    # Academic app (students, classes, attendance, grades)
    path('academics/', include('apps.academics.urls')),

    # Health app (health records, appointments, medications)
    path('health/', include('apps.health.urls')),

    # Communication app (messages, notifications, chat, announcements)
    path('communication/', include('apps.communication.urls', namespace='communication')),
    path('audit/', include('apps.audit.urls')),
    path('analytics/', include('apps.analytics.urls')),

     # Finance app (fees, payments, payroll)
     path('finance/', include('apps.finance.urls')),
     path('library/', include('apps.library.urls')),

     # Activities app (extracurricular activities, sports, clubs)
     path('activities/', include('apps.activities.urls', namespace='activities')),

      # Transport app (buses, routes, tracking)
     path('transport/', include('apps.transport.urls')),
     path('hostels/', include('apps.hostels.urls')),
     path('assessment/', include('apps.assessment.urls', namespace='assessment')),
     path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    
    # Support app (help desk, tickets)
    path('support/', include('apps.support.urls', namespace='support')),

    # Core app (system configuration, utilities)
    path('core/', include('apps.core.urls', namespace='core')),

     # API routes (for future REST API development)
#     path('api/', include('apps.api.urls')),
]

# # Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
      ] + urlpatterns

# Admin site customization
admin.site.site_header = 'Nexus Intelligence School Management System Administration'
admin.site.site_title = 'NEXUS Admin'
admin.site.index_title = 'Welcome to Nexus School Management System'
