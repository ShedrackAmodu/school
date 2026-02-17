from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Configuration Management URLs
    path('configs/', views.SystemConfigListView.as_view(), name='config_list'),
    path('configs/dashboard/', views.SystemConfigDashboardView.as_view(), name='config_dashboard'),
    path('configs/create/', views.SystemConfigCreateView.as_view(), name='config_create'),
    path('configs/<uuid:pk>/', views.SystemConfigDetailView.as_view(), name='config_detail'),
    path('configs/<uuid:pk>/update/', views.SystemConfigUpdateView.as_view(), name='config_update'),
    path('configs/<uuid:pk>/delete/', views.SystemConfigDeleteView.as_view(), name='config_delete'),
    path('configs/bulk-update/', views.SystemConfigBulkUpdateView.as_view(), name='config_bulk_update'),

    # Institution Details (Excellent Academy)
    path('institution/', views.InstitutionDetailView.as_view(), name='institution_detail'),
    path('principal/curriculum-planning/', views.PrincipalCurriculumPlanningView.as_view(), name='principal_curriculum_planning'),
    path('principal/communication/', views.PrincipalCommunicationView.as_view(), name='principal_communication'),

    # Global Search
    path('search/', views.GlobalSearchView.as_view(), name='global_search'),

    # API endpoints
    path('api/config/<str:config_key>/', views.get_config_value, name='get_config_value'),
    path('api/config/validate/', views.validate_config_value, name='validate_config_value'),
    path('api/configs/export/', views.export_configs, name='export_configs'),
    path('api/configs/import/', views.import_configs, name='import_configs'),

    # Institution API endpoints
    path('api/institution/<str:institution_code>/config/<str:config_key>/', views.get_institution_config_value, name='get_institution_config_value'),
    path('api/institutions/statistics/', views.institution_statistics_api, name='institution_statistics_api'),
]
