from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.views import View
import json

from .models import SystemConfig, Institution, InstitutionConfig
from .forms import (
    SystemConfigForm, SystemConfigBulkUpdateForm,
    InstitutionForm, InstitutionConfigForm, InstitutionConfigOverrideForm
)


class SystemConfigListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List view for System Configurations with filtering and search.
    """
    model = SystemConfig
    template_name = 'core/config/list.html'
    context_object_name = 'configs'
    paginate_by = 20
    permission_required = 'core.view_systemconfig'

    def get_queryset(self):
        queryset = SystemConfig.objects.all()

        # Apply filters
        config_type = self.request.GET.get('config_type')
        status = self.request.GET.get('status')
        is_public = self.request.GET.get('is_public')
        search = self.request.GET.get('search')

        if config_type and config_type != 'all':
            queryset = queryset.filter(config_type=config_type)

        if status and status != 'all':
            queryset = queryset.filter(status=status)

        if is_public and is_public != 'all':
            queryset = queryset.filter(is_public=is_public == 'true')

        if search:
            queryset = queryset.filter(
                Q(key__icontains=search) |
                Q(description__icontains=search) |
                Q(value__icontains=search)
            )

        return queryset.order_by('config_type', 'key')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options
        context['config_types'] = SystemConfig.ConfigType.choices
        context['status_choices'] = SystemConfig.Status.choices

        # Add current filter values
        context['current_filters'] = {
            'config_type': self.request.GET.get('config_type', ''),
            'status': self.request.GET.get('status', ''),
            'is_public': self.request.GET.get('is_public', ''),
            'search': self.request.GET.get('search', ''),
        }

        # Add statistics
        context['total_configs'] = SystemConfig.objects.count()
        context['active_configs'] = SystemConfig.objects.filter(status='active').count()

        return context


class SystemConfigCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for System Configuration.
    """
    model = SystemConfig
    form_class = SystemConfigForm
    template_name = 'core/config/form.html'
    permission_required = 'core.add_systemconfig'

    def get_success_url(self):
        messages.success(self.request, _('System configuration created successfully!'))
        return reverse_lazy('core:config_list')

    def form_valid(self, form):
        # Set created_by if the model had such a field
        return super().form_valid(form)


class SystemConfigUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for System Configuration.
    """
    model = SystemConfig
    form_class = SystemConfigForm
    template_name = 'core/config/form.html'
    permission_required = 'core.change_systemconfig'

    def get_success_url(self):
        messages.success(self.request, _('System configuration updated successfully!'))
        return reverse_lazy('core:config_list')


class SystemConfigDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for System Configuration.
    """
    model = SystemConfig
    template_name = 'core/config/detail.html'
    context_object_name = 'config'
    permission_required = 'core.view_systemconfig'


class SystemConfigDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for System Configuration.
    """
    model = SystemConfig
    template_name = 'core/config/confirm_delete.html'
    permission_required = 'core.delete_systemconfig'

    def get_success_url(self):
        messages.success(self.request, _('System configuration deleted successfully!'))
        return reverse_lazy('core:config_list')


class SystemConfigBulkUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Bulk update view for multiple System Configurations.
    """
    permission_required = 'core.change_systemconfig'

    def get(self, request, *args, **kwargs):
        config_ids = request.GET.getlist('config_ids')
        if not config_ids:
            messages.error(request, _('No configurations selected for bulk update.'))
            return redirect('core:config_list')

        configs = SystemConfig.objects.filter(id__in=config_ids)
        form = SystemConfigBulkUpdateForm(configs=configs)

        context = {
            'form': form,
            'configs': configs,
            'page_title': _('Bulk Update Configurations'),
        }

        return render(request, 'core/config/bulk_update.html', context)

    def post(self, request, *args, **kwargs):
        config_ids = request.POST.getlist('config_ids')
        configs = SystemConfig.objects.filter(id__in=config_ids)
        form = SystemConfigBulkUpdateForm(request.POST, configs=configs)

        if form.is_valid():
            updated_count = 0
            for config in configs:
                field_name = f"config_{config.id}"
                if field_name in form.cleaned_data:
                    new_value = form.cleaned_data[field_name]
                    if new_value != config.value:
                        config.value = new_value
                        config.save()
                        updated_count += 1

            messages.success(
                request,
                _(f'Successfully updated {updated_count} configuration(s).')
            )
            return redirect('core:config_list')
        else:
            context = {
                'form': form,
                'configs': configs,
                'page_title': _('Bulk Update Configurations'),
            }
            return render(request, 'core/config/bulk_update.html', context)


class SystemConfigDashboardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Dashboard view showing configuration statistics and categories.
    """
    permission_required = 'core.view_systemconfig'

    def get(self, request, *args, **kwargs):
        # Get configuration statistics by type
        config_stats = {}
        for config_type, display_name in SystemConfig.ConfigType.choices:
            count = SystemConfig.objects.filter(config_type=config_type).count()
            active_count = SystemConfig.objects.filter(
                config_type=config_type, status='active'
            ).count()
            config_stats[config_type] = {
                'total': count,
                'active': active_count,
                'inactive': count - active_count,
                'display_name': display_name,
            }

        # Recent changes (last 10)
        recent_configs = SystemConfig.objects.order_by('-updated_at')[:10]

        # Public vs private configs
        public_configs = SystemConfig.objects.filter(is_public=True).count()
        private_configs = SystemConfig.objects.filter(is_public=False).count()

        context = {
            'config_stats': config_stats,
            'recent_configs': recent_configs,
            'public_configs': public_configs,
            'private_configs': private_configs,
            'total_configs': SystemConfig.objects.count(),
            'page_title': _('Configuration Dashboard'),
        }

        return render(request, 'core/config/dashboard.html', context)


def get_config_value(request, config_key):
    """
    API endpoint to get a configuration value by key.
    """
    try:
        config = SystemConfig.objects.get(key=config_key, status='active')
        return JsonResponse({
            'key': config.key,
            'value': config.value,
            'config_type': config.config_type,
            'description': config.description,
        })
    except SystemConfig.DoesNotExist:
        return JsonResponse({'error': 'Configuration not found'}, status=404)


def validate_config_value(request):
    """
    API endpoint to validate configuration value format.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    value = request.POST.get('value', '')
    config_type = request.POST.get('config_type', '')

    try:
        # Basic JSON validation
        if value.strip().startswith(('{', '[', '"')):
            json.loads(value)
            is_valid = True
            error_message = ''
        else:
            # Try to parse as simple values
            import ast
            ast.literal_eval(value)
            is_valid = True
            error_message = ''
    except (json.JSONDecodeError, ValueError, SyntaxError) as e:
        is_valid = False
        error_message = str(e)

    return JsonResponse({
        'is_valid': is_valid,
        'error_message': error_message,
    })


def export_configs(request):
    """
    Export system configurations to JSON format.
    """
    configs = SystemConfig.objects.all().values(
        'key', 'value', 'config_type', 'description',
        'is_public', 'is_encrypted', 'status'
    )

    data = {
        'exported_at': request.user.get_full_name() if request.user.is_authenticated else 'System',
        'configurations': list(configs)
    }

    response = JsonResponse(data, safe=False)
    response['Content-Disposition'] = 'attachment; filename="system_configs.json"'
    return response


def import_configs(request):
    """
    Import system configurations from JSON file.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if 'config_file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    config_file = request.FILES['config_file']

    try:
        data = json.load(config_file)
        configs_data = data.get('configurations', [])

        imported_count = 0
        updated_count = 0

        for config_data in configs_data:
            key = config_data.get('key')
            if not key:
                continue

            config, created = SystemConfig.objects.get_or_create(
                key=key,
                defaults=config_data
            )

            if not created:
                # Update existing config
                for field, value in config_data.items():
                    if field in ['value', 'config_type', 'description', 'is_public', 'is_encrypted', 'status']:
                        setattr(config, field, value)
                config.save()
                updated_count += 1
            else:
                imported_count += 1

        return JsonResponse({
            'success': True,
            'imported': imported_count,
            'updated': updated_count,
        })

    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': f'Invalid file format: {str(e)}'}, status=400)


# Institution Management Views

class InstitutionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List view for Institutions with filtering and search.
    """
    model = Institution
    template_name = 'core/institutions/list.html'
    context_object_name = 'institutions'
    paginate_by = 20
    permission_required = 'core.view_institution'

    def get_queryset(self):
        queryset = Institution.objects.all()

        # Apply filters
        institution_type = self.request.GET.get('institution_type')
        ownership_type = self.request.GET.get('ownership_type')
        status = self.request.GET.get('status')
        is_active = self.request.GET.get('is_active')
        search = self.request.GET.get('search')

        if institution_type and institution_type != 'all':
            queryset = queryset.filter(institution_type=institution_type)

        if ownership_type and ownership_type != 'all':
            queryset = queryset.filter(ownership_type=ownership_type)

        if status and status != 'all':
            queryset = queryset.filter(status=status)

        if is_active and is_active != 'all':
            queryset = queryset.filter(is_active=is_active == 'true')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(short_name__icontains=search) |
                Q(city__icontains=search) |
                Q(country__icontains=search)
            )

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options
        context['institution_types'] = Institution.InstitutionType.choices
        context['ownership_types'] = Institution.OwnershipType.choices
        context['status_choices'] = Institution.Status.choices

        # Add current filter values
        context['current_filters'] = {
            'institution_type': self.request.GET.get('institution_type', ''),
            'ownership_type': self.request.GET.get('ownership_type', ''),
            'status': self.request.GET.get('status', ''),
            'is_active': self.request.GET.get('is_active', ''),
            'search': self.request.GET.get('search', ''),
        }

        # Add statistics
        context['total_institutions'] = Institution.objects.count()
        context['active_institutions'] = Institution.objects.filter(is_active=True).count()

        return context


class InstitutionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for Institution.
    """
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institutions/form.html'
    permission_required = 'core.add_institution'

    def get_success_url(self):
        messages.success(self.request, _('Institution created successfully!'))
        return reverse_lazy('core:institution_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class InstitutionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for Institution.
    """
    model = Institution
    form_class = InstitutionForm
    template_name = 'core/institutions/form.html'
    permission_required = 'core.change_institution'

    def get_success_url(self):
        messages.success(self.request, _('Institution updated successfully!'))
        return reverse_lazy('core:institution_list')


class InstitutionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for Institution.
    """
    model = Institution
    template_name = 'core/institutions/detail.html'
    context_object_name = 'institution'
    permission_required = 'core.view_institution'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.object

        # Add institution statistics
        context['student_count'] = institution.current_student_count
        context['staff_count'] = institution.current_staff_count
        context['utilization_rate'] = institution.utilization_rate

        # Add configuration overrides
        context['config_overrides'] = InstitutionConfig.objects.filter(
            institution=institution,
            is_active=True
        ).select_related('system_config')

        return context


class InstitutionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for Institution.
    """
    model = Institution
    template_name = 'core/institutions/confirm_delete.html'
    permission_required = 'core.delete_institution'

    def get_success_url(self):
        messages.success(self.request, _('Institution deleted successfully!'))
        return reverse_lazy('core:institution_list')


class InstitutionConfigOverrideView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    View for managing institution-specific configuration overrides.
    """
    permission_required = 'core.change_institution'

    def get(self, request, institution_id, *args, **kwargs):
        institution = get_object_or_404(Institution, id=institution_id)
        form = InstitutionConfigOverrideForm(institution=institution)

        context = {
            'institution': institution,
            'form': form,
            'page_title': _('Configuration Overrides'),
        }

        return render(request, 'core/institutions/config_overrides.html', context)

    def post(self, request, institution_id, *args, **kwargs):
        institution = get_object_or_404(Institution, id=institution_id)
        form = InstitutionConfigOverrideForm(request.POST, institution=institution)

        if form.is_valid():
            updated_count = 0
            created_count = 0

            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('config_') and value:
                    config_id = field_name.replace('config_', '')
                    try:
                        system_config = SystemConfig.objects.get(id=config_id)

                        # Check if override already exists
                        institution_config, created = InstitutionConfig.objects.get_or_create(
                            institution=institution,
                            system_config=system_config,
                            defaults={
                                'override_value': value,
                                'is_active': True
                            }
                        )

                        if not created:
                            # Update existing override
                            if institution_config.override_value != value:
                                institution_config.override_value = value
                                institution_config.save()
                                updated_count += 1
                        else:
                            created_count += 1

                    except SystemConfig.DoesNotExist:
                        continue

            messages.success(
                request,
                _(f'Successfully created {created_count} and updated {updated_count} configuration override(s).')
            )
            return redirect('core:institution_detail', pk=institution_id)
        else:
            context = {
                'institution': institution,
                'form': form,
                'page_title': _('Configuration Overrides'),
            }
            return render(request, 'core/institutions/config_overrides.html', context)


class SuperAdminDashboardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Super Administrator dashboard showing system-wide metrics and institution overview.
    """
    permission_required = 'core.view_institution'  # Could be more specific

    def get(self, request, *args, **kwargs):
        # Institution statistics
        total_institutions = Institution.objects.count()
        active_institutions = Institution.objects.filter(is_active=True).count()
        inactive_institutions = total_institutions - active_institutions

        # System-wide user statistics
        from apps.users.models import User
        total_users = User.objects.filter(is_active=True).count()

        # Configuration statistics
        total_configs = SystemConfig.objects.count()
        active_configs = SystemConfig.objects.filter(status='active').count()

        # Recent institution changes
        recent_institutions = Institution.objects.order_by('-updated_at')[:5]

        # System health indicators
        from apps.analytics.models import KPIMeasurement, KPI
        system_kpis = KPI.objects.filter(category='system', status='active')[:6]
        kpi_data = {}
        for kpi in system_kpis:
            latest_measurement = KPIMeasurement.objects.filter(kpi=kpi).order_by('-measured_at').first()
            if latest_measurement:
                kpi_data[kpi.id] = latest_measurement

        # Recent audit logs
        from apps.audit.models import AuditLog
        recent_audits = AuditLog.objects.order_by('-timestamp')[:10]

        context = {
            'total_institutions': total_institutions,
            'active_institutions': active_institutions,
            'inactive_institutions': inactive_institutions,
            'total_users': total_users,
            'total_configs': total_configs,
            'active_configs': active_configs,
            'recent_institutions': recent_institutions,
            'system_kpis': system_kpis,
            'kpi_data': kpi_data,
            'recent_audits': recent_audits,
            'page_title': _('Super Administrator Dashboard'),
        }

        return render(request, 'core/dashboard/super_admin.html', context)


class SchoolAdminDashboardView(LoginRequiredMixin, View):
    """
    School Administrator dashboard showing school-specific metrics and operations overview.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user has school admin role
        is_school_admin = user.user_roles.filter(
            role__role_type__in=['admin', 'principal']
        ).exists()

        if not is_school_admin and not user.is_staff:
            messages.error(request, _("You don't have permission to access the school administrator dashboard."))
            return redirect('users:dashboard')

        # Check if user is a principal for role-specific content
        is_principal = user.user_roles.filter(role__role_type='principal').exists()

        # Get current academic session
        from apps.academics.models import AcademicSession
        current_session = AcademicSession.objects.filter(is_current=True).first()

        # School Statistics
        total_students = 0
        total_teachers = 0
        total_classes = 0
        total_subjects = 0

        if current_session:
            from apps.academics.models import Student, Teacher, Class, Subject
            total_students = Student.objects.filter(status='active').count()
            total_teachers = Teacher.objects.filter(status='active').count()
            total_classes = Class.objects.filter(status='active').count()
            total_subjects = Subject.objects.filter(status='active').count()

        # Financial Overview
        from apps.finance.models import Invoice, Payment, Expense
        total_revenue = 0
        total_expenses = 0
        pending_payments = 0

        if current_session:
            # Calculate total revenue from paid invoices
            paid_invoices = Invoice.objects.filter(
                academic_session=current_session,
                status='paid'
            )
            total_revenue = sum(invoice.amount_paid for invoice in paid_invoices)

            # Calculate total expenses
            expenses = Expense.objects.filter(
                academic_session=current_session,
                status='active'
            )
            total_expenses = sum(expense.amount for expense in expenses)

            # Calculate pending payments
            pending_invoices = Invoice.objects.filter(
                academic_session=current_session,
                status__in=['issued', 'partial']
            )
            pending_payments = sum(invoice.balance_due for invoice in pending_invoices)

        # Attendance Overview
        attendance_rate = 0
        if current_session:
            from apps.attendance.models import AttendanceSummary
            # Get average attendance for current month
            current_month = timezone.now().month
            current_year = timezone.now().year

            monthly_summaries = AttendanceSummary.objects.filter(
                academic_session=current_session,
                month=current_month,
                year=current_year
            )

            if monthly_summaries.exists():
                total_percentage = sum(summary.attendance_percentage for summary in monthly_summaries)
                attendance_rate = round(total_percentage / monthly_summaries.count(), 1)

        # Recent Applications
        from apps.users.models import StudentApplication, StaffApplication
        pending_student_applications = StudentApplication.objects.filter(
            application_status__in=['pending', 'under_review']
        ).order_by('-application_date')[:5]

        pending_staff_applications = StaffApplication.objects.filter(
            application_status__in=['pending', 'under_review']
        ).order_by('-application_date')[:5]

        # Recent Announcements
        from apps.communication.models import Announcement
        recent_announcements = Announcement.objects.filter(
            is_published=True,
            status='active'
        ).order_by('-published_at')[:5]

        # System Health
        from apps.analytics.models import KPIMeasurement, KPI
        school_kpis = KPI.objects.filter(
            category__in=['academic', 'financial', 'operational'],
            status='active'
        )[:8]

        kpi_data = {}
        for kpi in school_kpis:
            latest_measurement = KPIMeasurement.objects.filter(kpi=kpi).order_by('-measured_at').first()
            if latest_measurement:
                kpi_data[kpi.id] = latest_measurement

        # Principal-specific data
        principal_stats = {}
        if is_principal:
            # Academic performance metrics
            from apps.assessment.models import Result
            if current_session:
                # Average class performance
                results = Result.objects.filter(
                    academic_session=current_session,
                    exam_type__is_final=True
                )
                if results.exists():
                    avg_percentage = results.aggregate(avg=models.Avg('percentage'))['avg']
                    principal_stats['avg_class_performance'] = round(avg_percentage or 0, 1)

                # Students at risk (below 50%)
                at_risk_count = results.filter(percentage__lt=50).count()
                principal_stats['students_at_risk'] = at_risk_count

            # Behavior incidents this month
            from apps.academics.models import BehaviorRecord
            current_month = timezone.now().replace(day=1)
            next_month = (current_month + timezone.timedelta(days=32)).replace(day=1)
            monthly_incidents = BehaviorRecord.objects.filter(
                incident_date__gte=current_month,
                incident_date__lt=next_month
            ).count()
            principal_stats['monthly_behavior_incidents'] = monthly_incidents

            # Academic warnings
            from apps.academics.models import AcademicWarning
            active_warnings = AcademicWarning.objects.filter(
                is_resolved=False
            ).count()
            principal_stats['active_academic_warnings'] = active_warnings

        # Quick Actions Data
        quick_stats = {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_classes': total_classes,
            'total_subjects': total_subjects,
            'attendance_rate': attendance_rate,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'pending_payments': pending_payments,
            'pending_student_apps': pending_student_applications.count(),
            'pending_staff_apps': pending_staff_applications.count(),
        }

        context = {
            'current_session': current_session,
            'quick_stats': quick_stats,
            'pending_student_applications': pending_student_applications,
            'pending_staff_applications': pending_staff_applications,
            'recent_announcements': recent_announcements,
            'school_kpis': school_kpis,
            'kpi_data': kpi_data,
            'is_principal': is_principal,
            'principal_stats': principal_stats,
            'page_title': _('Principal Dashboard') if is_principal else _('School Administrator Dashboard'),
        }

        # Use different template for principal
        template_name = 'principal/principal_dashboard.html' if is_principal else 'core/dashboard/school_admin.html'
        return render(request, template_name, context)


class PrincipalPerformanceMonitoringView(LoginRequiredMixin, View):
    """
    Principal view for monitoring academic performance across the school.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user is a principal
        if not user.user_roles.filter(role__role_type='principal').exists() and not user.is_staff:
            messages.error(request, _("You don't have permission to access this page."))
            return redirect('users:dashboard')

        from apps.academics.models import AcademicSession, Class, Student
        from apps.assessment.models import Result, Exam
        from apps.analytics.models import KPIMeasurement, KPI

        current_session = AcademicSession.objects.filter(is_current=True).first()

        # Performance data
        performance_data = {
            'grade_distribution': {},
            'subject_performance': {},
            'class_performance': [],
            'trends': []
        }

        if current_session:
            # Grade distribution
            results = Result.objects.filter(
                academic_session=current_session,
                exam_type__is_final=True
            ).select_related('grade')

            grade_counts = {}
            for result in results:
                grade_name = result.grade.grade if result.grade else 'No Grade'
                grade_counts[grade_name] = grade_counts.get(grade_name, 0) + 1

            performance_data['grade_distribution'] = grade_counts

            # Subject-wise performance
            from django.db.models import Avg
            subject_performance = Result.objects.filter(
                academic_session=current_session
            ).values('result__subject__name').annotate(
                avg_percentage=Avg('percentage')
            ).order_by('-avg_percentage')

            performance_data['subject_performance'] = list(subject_performance)

            # Class performance
            class_performance = Result.objects.filter(
                academic_session=current_session,
                exam_type__is_final=True
            ).values('academic_class__name').annotate(
                avg_percentage=Avg('percentage'),
                student_count=models.Count('student', distinct=True)
            ).order_by('-avg_percentage')

            performance_data['class_performance'] = list(class_performance)

        # Academic KPIs
        academic_kpis = KPI.objects.filter(
            category='academic',
            status='active'
        )[:10]

        kpi_data = {}
        for kpi in academic_kpis:
            latest_measurement = KPIMeasurement.objects.filter(kpi=kpi).order_by('-measured_at').first()
            if latest_measurement:
                kpi_data[kpi.id] = latest_measurement

        context = {
            'current_session': current_session,
            'performance_data': performance_data,
            'academic_kpis': academic_kpis,
            'kpi_data': kpi_data,
            'page_title': _('Academic Performance Monitoring'),
        }

        return render(request, 'principal/principal_performance_monitoring.html', context)


class PrincipalTeacherManagementView(LoginRequiredMixin, View):
    """
    Principal view for managing and monitoring teachers.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user is a principal
        if not user.user_roles.filter(role__role_type='principal').exists() and not user.is_staff:
            messages.error(request, _("You don't have permission to access this page."))
            return redirect('users:dashboard')

        from apps.academics.models import AcademicSession, Teacher, SubjectAssignment, Class
        from apps.assessment.models import Mark

        current_session = AcademicSession.objects.filter(is_current=True).first()

        # Teacher data
        teachers_data = []

        if current_session:
            teachers = Teacher.objects.filter(status='active')

            for teacher in teachers:
                # Get teacher's assignments
                assignments = SubjectAssignment.objects.filter(
                    teacher=teacher,
                    academic_session=current_session
                ).select_related('subject', 'class_assigned')

                # Calculate workload (total periods per week)
                total_periods = sum(assignment.periods_per_week for assignment in assignments)

                # Get classes taught
                classes_taught = assignments.values_list('class_assigned__name', flat=True).distinct()

                # Performance metrics (average student performance in teacher's classes)
                teacher_marks = Mark.objects.filter(
                    exam__academic_class__subject_assignments__teacher=teacher,
                    exam__academic_session=current_session
                ).aggregate(avg_percentage=models.Avg('percentage'))

                avg_performance = teacher_marks['avg_percentage'] or 0

                teachers_data.append({
                    'teacher': teacher,
                    'assignments': assignments,
                    'total_periods': total_periods,
                    'classes_count': len(classes_taught),
                    'classes_list': list(classes_taught),
                    'avg_student_performance': round(avg_performance, 1),
                    'subjects': assignments.values_list('subject__name', flat=True).distinct()
                })

        context = {
            'current_session': current_session,
            'teachers_data': teachers_data,
            'page_title': _('Teacher Management & Performance'),
        }

        return render(request, 'principal/principal_teacher_management.html', context)


class PrincipalStudentWelfareView(LoginRequiredMixin, View):
    """
    Principal view for monitoring student welfare and behavior.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user is a principal
        if not user.user_roles.filter(role__role_type='principal').exists() and not user.is_staff:
            messages.error(request, _("You don't have permission to access this page."))
            return redirect('users:dashboard')

        from apps.academics.models import AcademicSession, BehaviorRecord, AcademicWarning, Student
        from apps.attendance.models import AttendanceSummary

        current_session = AcademicSession.objects.filter(is_current=True).first()

        # Behavior and welfare data
        welfare_data = {
            'recent_incidents': [],
            'active_warnings': [],
            'attendance_issues': [],
            'behavior_trends': {}
        }

        if current_session:
            # Recent behavior incidents (last 30 days)
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            recent_incidents = BehaviorRecord.objects.filter(
                incident_date__gte=thirty_days_ago
            ).select_related('student', 'reported_by').order_by('-incident_date')[:20]

            welfare_data['recent_incidents'] = recent_incidents

            # Active academic warnings
            active_warnings = AcademicWarning.objects.filter(
                is_resolved=False
            ).select_related('student', 'issued_by').order_by('issued_date')[:20]

            welfare_data['active_warnings'] = active_warnings

            # Students with attendance issues (< 75% this month)
            current_month = timezone.now().month
            current_year = timezone.now().year

            attendance_issues = AttendanceSummary.objects.filter(
                academic_session=current_session,
                month=current_month,
                year=current_year,
                attendance_percentage__lt=75
            ).select_related('student').order_by('attendance_percentage')[:20]

            welfare_data['attendance_issues'] = attendance_issues

            # Behavior trends by category (last 6 months)
            six_months_ago = timezone.now() - timezone.timedelta(days=180)
            behavior_trends = BehaviorRecord.objects.filter(
                incident_date__gte=six_months_ago
            ).values('incident_category').annotate(
                count=models.Count('id')
            ).order_by('-count')

            welfare_data['behavior_trends'] = {item['incident_category']: item['count'] for item in behavior_trends}

        context = {
            'current_session': current_session,
            'welfare_data': welfare_data,
            'page_title': _('Student Welfare & Behavior Management'),
        }

        return render(request, 'principal/principal_student_welfare.html', context)


class PrincipalCurriculumPlanningView(LoginRequiredMixin, View):
    """
    Principal view for curriculum planning and academic oversight.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user is a principal
        if not user.user_roles.filter(role__role_type='principal').exists() and not user.is_staff:
            messages.error(request, _("You don't have permission to access this page."))
            return redirect('users:dashboard')

        from apps.academics.models import AcademicSession, Subject, Class, Timetable
        from apps.assessment.models import GradingSystem, Exam

        current_session = AcademicSession.objects.filter(is_current=True).first()

        # Curriculum data
        curriculum_data = {
            'subject_enrollment': {},
            'grading_effectiveness': {},
            'timetable_utilization': {},
            'exam_schedule': []
        }

        if current_session:
            # Subject enrollment statistics
            from django.db.models import Count
            subject_enrollment = Subject.objects.filter(
                subject_assignments__academic_session=current_session
            ).annotate(
                class_count=Count('subject_assignments__class_assigned', distinct=True),
                teacher_count=Count('subject_assignments__teacher', distinct=True)
            ).values('name', 'class_count', 'teacher_count')

            curriculum_data['subject_enrollment'] = list(subject_enrollment)

            # Grading system analysis
            grading_systems = GradingSystem.objects.filter(is_active=True)
            grading_stats = {}

            for system in grading_systems:
                results_count = Exam.objects.filter(
                    exam_type__grading_system=system,
                    academic_session=current_session
                ).count()
                grading_stats[system.name] = results_count

            curriculum_data['grading_effectiveness'] = grading_stats

            # Timetable utilization
            total_slots = Timetable.objects.filter(
                academic_session=current_session
            ).count()

            used_slots = Timetable.objects.filter(
                academic_session=current_session
            ).exclude(subject__isnull=True).count()

            utilization_rate = (used_slots / total_slots * 100) if total_slots > 0 else 0
            curriculum_data['timetable_utilization'] = {
                'total_slots': total_slots,
                'used_slots': used_slots,
                'utilization_rate': round(utilization_rate, 1)
            }

            # Upcoming exams
            upcoming_exams = Exam.objects.filter(
                academic_session=current_session,
                exam_date__gte=timezone.now().date()
            ).order_by('exam_date', 'start_time')[:10]

            curriculum_data['exam_schedule'] = upcoming_exams

        context = {
            'current_session': current_session,
            'curriculum_data': curriculum_data,
            'page_title': _('Curriculum & Academic Planning'),
        }

        return render(request, 'principal/principal_curriculum_planning.html', context)


class PrincipalCommunicationView(LoginRequiredMixin, View):
    """
    Principal view for stakeholder communication and messaging.
    """
    def get(self, request, *args, **kwargs):
        user = request.user

        # Check if user is a principal
        if not user.user_roles.filter(role__role_type='principal').exists() and not user.is_staff:
            messages.error(request, _("You don't have permission to access this page."))
            return redirect('users:dashboard')

        from apps.communication.models import Announcement, Message
        from apps.users.models import User

        # Communication data
        communication_data = {
            'recent_announcements': [],
            'message_threads': [],
            'feedback_summary': {}
        }

        # Recent principal announcements
        principal_announcements = Announcement.objects.filter(
            author=user,
            is_published=True
        ).order_by('-published_at')[:10]

        communication_data['recent_announcements'] = principal_announcements

        # Recent message threads
        recent_messages = Message.objects.filter(
            sender=user
        ).order_by('-created_at')[:10]

        communication_data['message_threads'] = recent_messages

        # Feedback summary (simplified - would need proper feedback model)
        communication_data['feedback_summary'] = {
            'total_responses': 0,
            'positive_feedback': 0,
            'needs_attention': 0
        }

        context = {
            'communication_data': communication_data,
            'page_title': _('Stakeholder Communication'),
        }

        return render(request, 'principal/principal_communication.html', context)


# API endpoints for institutions

def get_institution_config_value(request, institution_code, config_key):
    """
    API endpoint to get configuration value for a specific institution.
    """
    try:
        institution = Institution.objects.get(code=institution_code, is_active=True)
        config = SystemConfig.objects.get(key=config_key, status='active')

        effective_value = config.get_value_for_institution(institution)

        return JsonResponse({
            'institution': institution.code,
            'key': config.key,
            'value': effective_value,
            'config_type': config.config_type,
            'description': config.description,
        })
    except (Institution.DoesNotExist, SystemConfig.DoesNotExist):
        return JsonResponse({'error': 'Institution or configuration not found'}, status=404)


def institution_statistics_api(request):
    """
    API endpoint for institution statistics.
    """
    institutions = Institution.objects.filter(is_active=True)

    data = {
        'total_institutions': institutions.count(),
        'institutions': []
    }

    for institution in institutions:
        data['institutions'].append({
            'id': str(institution.id),
            'code': institution.code,
            'name': institution.name,
            'student_count': institution.current_student_count,
            'staff_count': institution.current_staff_count,
            'utilization_rate': institution.utilization_rate,
            'status': institution.status,
        })

    return JsonResponse(data)


class GlobalSearchView(LoginRequiredMixin, View):
    """
    Global search view that searches across multiple models based on user query and filter.
    """
    template_name = 'core/search/results.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        filter_type = request.GET.get('filter', 'all')

        results = {
            'students': [],
            'teachers': [],
            'classes': [],
            'documents': [],
        }

        if query:
            if filter_type in ['all', 'students']:
                results['students'] = self.search_students(query)
            if filter_type in ['all', 'teachers']:
                results['teachers'] = self.search_teachers(query)
            if filter_type in ['all', 'classes']:
                results['classes'] = self.search_classes(query)
            if filter_type in ['all', 'documents']:
                results['documents'] = self.search_documents(query)

        context = {
            'query': query,
            'filter_type': filter_type,
            'results': results,
            'total_results': sum(len(res) for res in results.values()),
            'page_title': _('Search Results'),
        }

        return render(request, self.template_name, context)

    def search_students(self, query):
        """Search for students across relevant fields."""
        from apps.users.models import User

        return User.objects.filter(
            Q(user_roles__role__role_type='student') &
            (
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(profile__student_id__icontains=query) |
                Q(profile__phone_primary__icontains=query)
            )
        ).distinct().select_related('profile')[:10]

    def search_teachers(self, query):
        """Search for teachers/staff across relevant fields."""
        from apps.users.models import User

        return User.objects.filter(
            Q(user_roles__role__role_type__in=['teacher', 'staff', 'admin']) &
            (
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(profile__employee_id__icontains=query) |
                Q(profile__phone_primary__icontains=query)
            )
        ).distinct().select_related('profile')[:10]

    def search_classes(self, query):
        """Search for classes across relevant fields."""
        from apps.academics.models import Class

        return Class.objects.filter(
            Q(name__icontains=query) |
            Q(class_code__icontains=query) |
            Q(class_stream__stream_name__icontains=query)
        ).distinct().select_related('academic_session', 'class_teacher')[:10]

    def search_documents(self, query):
        """Search for documents/books across relevant fields."""
        try:
            from apps.library.models import Book, BookCopy

            # Search books
            books = Book.objects.filter(
                Q(title__icontains=query) |
                Q(isbn__icontains=query) |
                Q(authors__first_name__icontains=query) |
                Q(authors__last_name__icontains=query)
            ).distinct()[:10]

            # Search book copies for barcodes
            book_copies = BookCopy.objects.filter(
                Q(barcode__icontains=query)
            ).select_related('book')[:10]

            # Combine and deduplicate
            documents = []
            seen_books = set()

            for book in books:
                if book.id not in seen_books:
                    documents.append({
                        'type': 'book',
                        'object': book,
                        'url': reverse('library:book_detail', kwargs={'pk': book.pk})
                    })
                    seen_books.add(book.id)

            for copy in book_copies:
                if copy.book.id not in seen_books:
                    documents.append({
                        'type': 'book_copy',
                        'object': copy,
                        'url': reverse('library:book_borrow_detail', kwargs={'pk': copy.pk})
                    })
                    seen_books.add(copy.book.id)

            return documents[:10]

        except ImportError:
            # Library app not available
            return []
