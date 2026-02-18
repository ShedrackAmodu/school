# apps/finance/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db import models
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.conf import settings
from decimal import Decimal
import json
import logging
import uuid

from .models import FeeStructure, FeeDiscount, Invoice, InvoiceItem, Payment, Expense, FinancialReport, PaystackPayment, PaystackWebhookEvent, PaymentMethod

logger = logging.getLogger(__name__)
from .forms import FeeStructureForm, FeeDiscountForm, InvoiceForm, InvoiceItemForm, PaymentForm, ExpenseForm, FinancialReportForm
from .services import get_paystack_service, get_payment_service, get_webhook_service
from apps.academics.models import AcademicSession, Student, Class
from apps.users.models import User, Role
from apps.audit.models import AuditLog
from apps.core.models import Institution


# =============================================================================
# MIXINS AND BASE CLASSES
# =============================================================================

class FinanceAccessMixin(LoginRequiredMixin):
    """Base mixin for finance app access control."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user has finance-related role or is staff/admin
        user_roles = request.user.user_roles.all()
        finance_roles = ['accountant', 'admin', 'principal', 'super_admin']
        
        if not any(role.role.role_type in finance_roles for role in user_roles):
            if not request.user.is_staff:
                messages.error(request, _("You don't have permission to access finance resources."))
                return redirect('users:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class AccountantRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is an accountant, staff, or admin."""

    def test_func(self):
        user = self.request.user
        if user.is_staff:
            return True
        
        # Check if user has accountant role
        return user.user_roles.filter(role__role_type='accountant').exists()


# =============================================================================
# DASHBOARD VIEWS
# =============================================================================

class DashboardView(LoginRequiredMixin, AccountantRequiredMixin, View):
    """Accountant dashboard showing financial overview."""

    def get(self, request):
        current_session = AcademicSession.objects.filter(is_current=True).first()

        # Fee Collection Summary
        total_invoiced = Invoice.objects.filter(
            academic_session=current_session
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        total_paid = Invoice.objects.filter(
            academic_session=current_session
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')

        total_outstanding = total_invoiced - total_paid

        # Recent Invoices
        recent_invoices = Invoice.objects.filter(
            academic_session=current_session
        ).select_related('student__user').order_by('-issue_date')[:8]

        # Recent Payments
        recent_payments = Payment.objects.filter(
            invoice__academic_session=current_session,
            status=Payment.PaymentStatus.COMPLETED,
        ).select_related('student__user', 'invoice').order_by('-payment_date')[:8]

        # Expense Summary (current month)
        now = timezone.now()
        total_expenses = Expense.objects.filter(
            expense_date__year=now.year,
            expense_date__month=now.month,
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # Overdue Invoices count
        overdue_invoices_count = Invoice.objects.filter(
            academic_session=current_session,
            due_date__lt=now.date(),
            status__in=['issued', 'partial'],
        ).count()

        # ── Monthly collection data for chart (real data) ─────────────────
        monthly_collection = []
        for month in range(1, 13):
            month_invoiced = Invoice.objects.filter(
                academic_session=current_session,
                issue_date__year=now.year,
                issue_date__month=month,
            ).aggregate(v=Sum('total_amount'))['v'] or 0
            month_paid = Invoice.objects.filter(
                academic_session=current_session,
                issue_date__year=now.year,
                issue_date__month=month,
            ).aggregate(v=Sum('amount_paid'))['v'] or 0
            monthly_collection.append({
                'month': month,
                'invoiced': float(month_invoiced),
                'paid': float(month_paid),
            })

        context = {
            'title': _('Accountant Dashboard'),
            'current_session': current_session,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'recent_invoices': recent_invoices,
            'recent_payments': recent_payments,
            'total_expenses': total_expenses,
            'overdue_invoices_count': overdue_invoices_count,
            'monthly_collection': monthly_collection,
        }
        return render(request, 'finance/dashboard/accountant_dashboard.html', context)


# =============================================================================
# FEE STRUCTURE VIEWS
# =============================================================================

class FeeStructureListView(FinanceAccessMixin, ListView):
    """List all fee structures."""
    model = FeeStructure
    template_name = 'finance/fee_structures/fee_structure_list.html'
    context_object_name = 'fee_structures'
    paginate_by = 10

    def get_queryset(self):
        queryset = FeeStructure.objects.select_related('academic_session', 'applicable_class').order_by('-academic_session__start_date', 'fee_type')
        
        session_id = self.request.GET.get('session')
        fee_type = self.request.GET.get('fee_type')

        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_sessions'] = AcademicSession.objects.filter(status='active')
        context['fee_types'] = FeeStructure.FeeType.choices
        return context


class FeeStructureDetailView(FinanceAccessMixin, DetailView):
    """Detail view for a fee structure."""
    model = FeeStructure
    template_name = 'finance/fee_structures/fee_structure_detail.html'
    context_object_name = 'fee_structure'


class FeeStructureCreateView(AccountantRequiredMixin, CreateView):
    """Create a new fee structure."""
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = 'finance/fee_structures/fee_structure_form.html'
    success_url = reverse_lazy('finance:fee_structure_list')

    def form_valid(self, form):
        messages.success(self.request, _('Fee structure created successfully.'))
        return super().form_valid(form)


class FeeStructureUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing fee structure."""
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = 'finance/fee_structures/fee_structure_form.html'
    success_url = reverse_lazy('finance:fee_structure_list')

    def form_valid(self, form):
        messages.success(self.request, _('Fee structure updated successfully.'))
        return super().form_valid(form)


class FeeStructureDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete a fee structure."""
    model = FeeStructure
    template_name = 'finance/fee_structures/fee_structure_confirm_delete.html'
    success_url = reverse_lazy('finance:fee_structure_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Fee structure deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# FEE DISCOUNT VIEWS
# =============================================================================

class FeeDiscountListView(FinanceAccessMixin, ListView):
    """List all fee discounts."""
    model = FeeDiscount
    template_name = 'finance/fee_discounts/fee_discount_list.html'
    context_object_name = 'fee_discounts'
    paginate_by = 10

    def get_queryset(self):
        queryset = FeeDiscount.objects.prefetch_related('applicable_fee_types').order_by('-start_date')
        
        category = self.request.GET.get('category')
        is_active = self.request.GET.get('is_active')

        if category:
            queryset = queryset.filter(category=category)
        if is_active:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = FeeDiscount.DiscountCategory.choices
        return context


class FeeDiscountDetailView(FinanceAccessMixin, DetailView):
    """Detail view for a fee discount."""
    model = FeeDiscount
    template_name = 'finance/fee_discounts/fee_discount_detail.html'
    context_object_name = 'fee_discount'


class FeeDiscountCreateView(AccountantRequiredMixin, CreateView):
    """Create a new fee discount."""
    model = FeeDiscount
    form_class = FeeDiscountForm
    template_name = 'finance/fee_discounts/fee_discount_form.html'
    success_url = reverse_lazy('finance:fee_discount_list')

    def form_valid(self, form):
        messages.success(self.request, _('Fee discount created successfully.'))
        return super().form_valid(form)


class FeeDiscountUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing fee discount."""
    model = FeeDiscount
    form_class = FeeDiscountForm
    template_name = 'finance/fee_discounts/fee_discount_form.html'
    success_url = reverse_lazy('finance:fee_discount_list')

    def form_valid(self, form):
        messages.success(self.request, _('Fee discount updated successfully.'))
        return super().form_valid(form)


class FeeDiscountDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete a fee discount."""
    model = FeeDiscount
    template_name = 'finance/fee_discounts/fee_discount_confirm_delete.html'
    success_url = reverse_lazy('finance:fee_discount_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Fee discount deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# INVOICE VIEWS
# =============================================================================

class InvoiceListView(FinanceAccessMixin, ListView):
    """List all invoices."""
    model = Invoice
    template_name = 'finance/invoices/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        queryset = Invoice.objects.select_related('student__user', 'academic_session').order_by('-issue_date')
        
        session_id = self.request.GET.get('session')
        student_id = self.request.GET.get('student')
        status = self.request.GET.get('status')

        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_sessions'] = AcademicSession.objects.filter(status='active')
        context['students'] = Student.objects.filter(status='active').select_related('user')
        context['invoice_statuses'] = Invoice.InvoiceStatus.choices
        return context


class InvoiceDetailView(FinanceAccessMixin, DetailView):
    """Detail view for an invoice."""
    model = Invoice
    template_name = 'finance/invoices/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice_items'] = self.object.items.select_related('fee_structure')
        context['payments'] = self.object.payments.select_related('received_by')
        return context


class InvoiceCreateView(AccountantRequiredMixin, CreateView):
    """Create a new invoice."""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'finance/invoices/invoice_form.html'
    success_url = reverse_lazy('finance:invoice_list')

    def form_valid(self, form):
        messages.success(self.request, _('Invoice created successfully.'))
        return super().form_valid(form)


class InvoiceUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing invoice."""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'finance/invoices/invoice_form.html'
    success_url = reverse_lazy('finance:invoice_list')

    def form_valid(self, form):
        messages.success(self.request, _('Invoice updated successfully.'))
        return super().form_valid(form)


class InvoiceDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete an invoice."""
    model = Invoice
    template_name = 'finance/invoices/invoice_confirm_delete.html'
    success_url = reverse_lazy('finance:invoice_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Invoice deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# PAYMENT VIEWS
# =============================================================================

class PaymentListView(FinanceAccessMixin, ListView):
    """List all payments."""
    model = Payment
    template_name = 'finance/payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 10

    def get_queryset(self):
        queryset = Payment.objects.select_related('invoice', 'student__user', 'received_by').order_by('-payment_date')
        
        session_id = self.request.GET.get('session')
        student_id = self.request.GET.get('student')
        payment_method = self.request.GET.get('payment_method')
        status = self.request.GET.get('status')

        if session_id:
            queryset = queryset.filter(invoice__academic_session_id=session_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_sessions'] = AcademicSession.objects.filter(status='active')
        context['students'] = Student.objects.filter(status='active').select_related('user')
        context['payment_methods'] = Payment.PaymentMethod.choices
        context['payment_statuses'] = Payment.PaymentStatus.choices
        return context


class PaymentDetailView(FinanceAccessMixin, DetailView):
    """Detail view for a payment."""
    model = Payment
    template_name = 'finance/payments/payment_detail.html'
    context_object_name = 'payment'


class PaymentGatewayView(FinanceAccessMixin, View):
    """
    View for handling Paystack payment gateway redirection and processing.
    """
    def get(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        paystack_service = get_paystack_service()
        payment_service = get_payment_service()

        # Create payment record
        payment = payment_service.create_payment_from_invoice(
            invoice=invoice,
            amount=invoice.balance_due,
            payment_method='paystack',
            customer_email=invoice.student.user.email,
            metadata={
                'invoice_id': str(invoice.id),
                'student_id': str(invoice.student.id),
                'institution_id': str(invoice.institution.id),
                'payment_type': 'invoice_payment'
            }
        )

        # Generate unique reference
        reference = f"INV-{invoice.invoice_number}-{payment.payment_number}"

        try:
            # Initialize payment with Paystack
            payment_data = paystack_service.initialize_payment(
                email=invoice.student.user.email,
                amount=invoice.balance_due,
                reference=reference,
                metadata=payment.paystack_metadata,
                callback_url=request.build_absolute_uri(reverse_lazy('finance:payment_callback', kwargs={'reference': reference}))
            )

            # Create PaystackPayment record
            paystack_payment = payment_service.create_paystack_payment(
                payment=payment,
                paystack_reference=reference,
                authorization_url=payment_data['authorization_url'],
                access_code=payment_data['access_code']
            )

            # Update payment with Paystack details
            payment.paystack_payment_id = reference
            payment.paystack_transaction_reference = reference
            payment.save()

            # Redirect to Paystack authorization URL
            return redirect(payment_data['authorization_url'])

        except Exception as e:
            messages.error(request, _(f"Failed to initialize payment: {str(e)}"))
            return redirect('finance:invoice_detail', pk=invoice_pk)


class PaymentCallbackView(View):
    """
    View for handling Paystack payment callback.
    """
    def get(self, request, reference):
        paystack_service = get_paystack_service()
        payment_service = get_payment_service()

        try:
            # Verify payment with Paystack
            verification_data = paystack_service.verify_payment(reference)

            if verification_data.get('status') == 'success':
                # Process payment verification
                payment, paystack_payment = payment_service.process_payment_verification(
                    reference, verification_data
                )
                messages.success(request, _('Payment completed successfully!'))
                return redirect('finance:payment_success', pk=payment.pk)
            else:
                messages.error(request, _('Payment verification failed. Please try again or contact support.'))
                from django.urls import reverse
                return redirect(reverse('finance:payment_failed_generic') + f'?reference={reference}')

        except Exception as e:
            logger.error(f"PaymentCallbackView error for reference {reference}: {e}")
            messages.error(request, _('Payment processing encountered an error. Please contact support.'))
            from django.urls import reverse
            return redirect(reverse('finance:payment_failed_generic') + f'?reference={reference}')


class PaymentSuccessView(FinanceAccessMixin, DetailView):
    """View for successful payment confirmation."""
    model = Payment
    template_name = 'finance/payments/payment_success.html'
    context_object_name = 'payment'


class PaymentFailedView(FinanceAccessMixin, View):
    """View for failed payment confirmation."""
    def get(self, request, pk):
        context = {
            'reference': pk,
            'title': _('Payment Failed')
        }
        return render(request, 'finance/payments/payment_failed.html', context)


class PaymentCancelView(FinanceAccessMixin, View):
    """View for cancelled payment confirmation."""
    def get(self, request, pk):
        context = {
            'reference': pk,
            'title': _('Payment Cancelled')
        }
        return render(request, 'finance/payments/payment_cancelled.html', context)


class PaymentCreateView(AccountantRequiredMixin, CreateView):
    """Create a new payment."""
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payments/payment_form.html'
    success_url = reverse_lazy('finance:payment_list')

    def form_valid(self, form):
        messages.success(self.request, _('Payment recorded successfully.'))
        return super().form_valid(form)


class PaymentUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing payment."""
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payments/payment_form.html'
    success_url = reverse_lazy('finance:payment_list')

    def form_valid(self, form):
        messages.success(self.request, _('Payment updated successfully.'))
        return super().form_valid(form)


class PaymentDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete a payment."""
    model = Payment
    template_name = 'finance/payments/payment_confirm_delete.html'
    success_url = reverse_lazy('finance:payment_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Payment deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# PAYSTACK PAYMENT VIEWS (STUDENT/PARENT FACING)
# =============================================================================

class StudentPaymentListView(LoginRequiredMixin, ListView):
    """View for students/parents to see their payment history."""
    model = Payment
    template_name = 'finance/student/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 10

    def get_queryset(self):
        # Only show payments for the logged-in student
        if hasattr(self.request.user, 'student_profile'):
            return Payment.objects.filter(
                student=self.request.user.student_profile
            ).select_related('invoice', 'invoice__academic_session').order_by('-payment_date')
        else:
            return Payment.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            # Calculate summary statistics
            total_paid = Payment.objects.filter(
                student=student,
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            
            total_pending = Payment.objects.filter(
                student=student,
                status__in=['pending', 'failed']
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

            context.update({
                'total_paid': total_paid,
                'total_pending': total_pending,
            })
        return context


class StudentInvoicePaymentView(LoginRequiredMixin, View):
    """View for students/parents to pay an invoice."""
    def get(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        student = request.user.student_profile

        # Verify that the invoice belongs to the student
        if invoice.student != student:
            messages.error(request, _('You do not have permission to view this invoice.'))
            return redirect('finance:student_payment_list')

        context = {
            'invoice': invoice,
            'student': student,
            'title': _('Pay Invoice')
        }
        return render(request, 'finance/student/pay_invoice.html', context)

    def post(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        student = request.user.student_profile

        # Verify that the invoice belongs to the student
        if invoice.student != student:
            messages.error(request, _('You do not have permission to pay this invoice.'))
            return redirect('finance:student_payment_list')

        paystack_service = get_paystack_service()
        payment_service = get_payment_service()

        # Create payment record
        payment = payment_service.create_payment_from_invoice(
            invoice=invoice,
            amount=invoice.balance_due,
            payment_method='paystack',
            customer_email=student.user.email,
            metadata={
                'invoice_id': str(invoice.id),
                'student_id': str(student.id),
                'institution_id': str(invoice.institution.id),
                'payment_type': 'invoice_payment'
            }
        )

        # Generate unique reference
        reference = f"INV-{invoice.invoice_number}-{payment.payment_number}"

        try:
            # Initialize payment with Paystack
            payment_data = paystack_service.initialize_payment(
                email=student.user.email,
                amount=invoice.balance_due,
                reference=reference,
                metadata=payment.paystack_metadata,
                callback_url=request.build_absolute_uri(reverse_lazy('finance:payment_callback', kwargs={'reference': reference}))
            )

            # Create PaystackPayment record
            paystack_payment = payment_service.create_paystack_payment(
                payment=payment,
                paystack_reference=reference,
                authorization_url=payment_data['authorization_url'],
                access_code=payment_data['access_code']
            )

            # Update payment with Paystack details
            payment.paystack_payment_id = reference
            payment.paystack_transaction_reference = reference
            payment.save()

            # Redirect to Paystack authorization URL
            return redirect(payment_data['authorization_url'])

        except Exception as e:
            messages.error(request, _(f"Failed to initialize payment: {str(e)}"))
            return redirect('finance:student_invoice_payment', invoice_pk=invoice_pk)


# =============================================================================
# EXPENSE VIEWS
# =============================================================================

class ExpenseListView(FinanceAccessMixin, ListView):
    """List all expenses."""
    model = Expense
    template_name = 'finance/expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 10

    def get_queryset(self):
        queryset = Expense.objects.select_related('approved_by', 'paid_by', 'receipt_attachment').order_by('-expense_date')
        
        category = self.request.GET.get('category')
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')

        if category:
            queryset = queryset.filter(category=category)
        if year:
            queryset = queryset.filter(expense_date__year=year)
        if month:
            queryset = queryset.filter(expense_date__month=month)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expense_categories'] = Expense.ExpenseCategory.choices
        context['years'] = Expense.objects.dates('expense_date', 'year').order_by('-date')
        context['months'] = [
            (i, timezone.datetime(1, i, 1).strftime('%B')) for i in range(1, 13)
        ]
        return context


class ExpenseDetailView(FinanceAccessMixin, DetailView):
    """Detail view for an expense."""
    model = Expense
    template_name = 'finance/expenses/expense_detail.html'
    context_object_name = 'expense'


class ExpenseCreateView(AccountantRequiredMixin, CreateView):
    """Create a new expense."""
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expenses/expense_form.html'
    success_url = reverse_lazy('finance:expense_list')

    def form_valid(self, form):
        messages.success(self.request, _('Expense created successfully.'))
        return super().form_valid(form)


class ExpenseUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing expense."""
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expenses/expense_form.html'
    success_url = reverse_lazy('finance:expense_list')

    def form_valid(self, form):
        messages.success(self.request, _('Expense updated successfully.'))
        return super().form_valid(form)


class ExpenseDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete an expense."""
    model = Expense
    template_name = 'finance/expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('finance:expense_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Expense deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# FINANCIAL REPORT VIEWS
# =============================================================================

class FinancialReportListView(FinanceAccessMixin, ListView):
    """List all financial reports."""
    model = FinancialReport
    template_name = 'finance/reports/financial_report_list.html'
    context_object_name = 'reports'
    paginate_by = 10

    def get_queryset(self):
        queryset = FinancialReport.objects.select_related('academic_session', 'generated_by').order_by('-created_at')
        
        report_type = self.request.GET.get('report_type')
        session_id = self.request.GET.get('session')
        is_published = self.request.GET.get('is_published')

        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if session_id:
            queryset = queryset.filter(academic_session_id=session_id)
        if is_published:
            queryset = queryset.filter(is_published=(is_published == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_types'] = FinancialReport.ReportType.choices
        context['academic_sessions'] = AcademicSession.objects.filter(status='active')
        return context


class FinancialReportDetailView(FinanceAccessMixin, DetailView):
    """Detail view for a financial report."""
    model = FinancialReport
    template_name = 'finance/reports/financial_report_detail.html'
    context_object_name = 'report'


class FinancialReportCreateView(AccountantRequiredMixin, CreateView):
    """Create a new financial report."""
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/reports/financial_report_form.html'
    success_url = reverse_lazy('finance:financial_report_list')

    def form_valid(self, form):
        form.instance.generated_by = self.request.user
        messages.success(self.request, _('Financial report created successfully.'))
        return super().form_valid(form)


class FinancialReportUpdateView(AccountantRequiredMixin, UpdateView):
    """Update an existing financial report."""
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/reports/financial_report_form.html'
    success_url = reverse_lazy('finance:financial_report_list')

    def form_valid(self, form):
        messages.success(self.request, _('Financial report updated successfully.'))
        return super().form_valid(form)


class FinancialReportDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete a financial report."""
    model = FinancialReport
    template_name = 'finance/reports/financial_report_confirm_delete.html'
    success_url = reverse_lazy('finance:financial_report_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('Financial report deleted successfully.'))
        return super().post(request, *args, **kwargs)


# =============================================================================
# PAYSTACK WEBHOOK VIEWS
# =============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    """View for handling Paystack webhook events."""
    
    def post(self, request):
        import hashlib
        import hmac

        # Get webhook signature from headers
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        if not signature:
            return HttpResponseBadRequest("Missing webhook signature")

        # Verify webhook signature
        webhook_secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')
        if webhook_secret:
            computed_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                request.body,
                hashlib.sha512
            ).hexdigest()

            if not hmac.compare_digest(signature, computed_signature):
                return HttpResponseBadRequest("Invalid webhook signature")

        try:
            # Parse webhook data
            webhook_data = json.loads(request.body)
            event_type = webhook_data.get('event')
            event_data = webhook_data.get('data', {})
            event_reference = event_data.get('reference')
            event_timestamp = timezone.now()

            # Process webhook event
            webhook_service = get_webhook_service()
            webhook_event, success = webhook_service.process_webhook_event(
                event_type, event_data, event_reference, event_timestamp
            )

            if success:
                return JsonResponse({'status': 'success'}, status=200)
            else:
                return JsonResponse({'status': 'failed', 'message': 'Webhook processing failed'}, status=500)

        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON data")
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return HttpResponseBadRequest(f"Webhook processing error: {str(e)}")


# =============================================================================
# API & AJAX VIEWS
# =============================================================================

class ReceiptDownloadView(FinanceAccessMixin, View):
    """View for downloading payment receipts."""
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        # TODO: Implement receipt generation and download
        messages.info(request, _(f"Receipt download for Payment ID {pk}. (Placeholder)"))
        return HttpResponse(_("Receipt Download Placeholder"))

class APIInvoiceListView(FinanceAccessMixin, ListView):
    """API to list invoices (placeholder for a more robust API)."""
    model = Invoice
    def get(self, request, *args, **kwargs):
        invoices = self.get_queryset()
        data = [{'invoice_number': inv.invoice_number, 'total_amount': str(inv.total_amount)} for inv in invoices]
        return JsonResponse(data, safe=False)

class APIPaymentStatusView(FinanceAccessMixin, View):
    """API to get payment status (placeholder)."""
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        data = {
            'payment_number': payment.payment_number,
            'status': payment.get_status_display(),
            'amount': str(payment.amount),
            'invoice_number': payment.invoice.invoice_number
        }
        return JsonResponse(data)

class GenerateInvoiceAPIView(AccountantRequiredMixin, View):
    """API to generate invoices for students based on fee structures."""

    def post(self, request):
        import json
        from django.db import transaction

        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids')
            academic_session_id = data.get('academic_session_id')
            billing_period = data.get('billing_period')
            issue_date_str = data.get('issue_date')
            due_date_str = data.get('due_date')

            if not all([student_ids, academic_session_id, billing_period, issue_date_str, due_date_str]):
                return JsonResponse({'success': False, 'message': _('Missing required fields.')}, status=400)

            academic_session = get_object_or_404(AcademicSession, id=academic_session_id)
            students = Student.objects.filter(id__in=student_ids, status='active')
            
            issue_date = timezone.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%d').date()

            generated_invoices = []
            with transaction.atomic():
                for student in students:
                    # Check if an invoice for this student and billing period already exists
                    existing_invoice = Invoice.objects.filter(
                        student=student,
                        academic_session=academic_session,
                        billing_period=billing_period
                    ).first()

                    if existing_invoice:
                        generated_invoices.append({
                            'student': student.user.get_full_name(),
                            'status': 'skipped',
                            'reason': _('Invoice already exists for this period.')
                        })
                        continue

                    # Get applicable fee structures for the student's current class
                    current_enrollment = student.enrollments.filter(
                        academic_session=academic_session,
                        enrollment_status='active'
                    ).first()

                    if not current_enrollment:
                        generated_invoices.append({
                            'student': student.user.get_full_name(),
                            'status': 'skipped',
                            'reason': _('Student not enrolled in an active class for this session.')
                        })
                        continue

                    applicable_fees = FeeStructure.objects.filter(
                        Q(academic_session=academic_session),
                        Q(applicable_class=current_enrollment.class_enrolled) | Q(applicable_class__isnull=True),
                        status='active'
                    )

                    if not applicable_fees.exists():
                        generated_invoices.append({
                            'student': student.user.get_full_name(),
                            'status': 'skipped',
                            'reason': _('No applicable fee structures found.')
                        })
                        continue

                    # Create invoice
                    invoice = Invoice.objects.create(
                        student=student,
                        academic_session=academic_session,
                        billing_period=billing_period,
                        issue_date=issue_date,
                        due_date=due_date,
                        status=Invoice.InvoiceStatus.ISSUED,
                        total_amount=Decimal('0.00'), # Will be updated by items
                        subtotal=Decimal('0.00'),
                        total_tax=Decimal('0.00'),
                        total_discount=Decimal('0.00'),
                    )

                    invoice_subtotal = Decimal('0.00')
                    invoice_total_tax = Decimal('0.00')
                    invoice_total_discount = Decimal('0.00')

                    for fee in applicable_fees:
                        # Calculate discounts
                        discount_amount = Decimal('0.00')
                        if fee.discount_eligible:
                            applicable_discounts = FeeDiscount.objects.filter(
                                applicable_fee_types=fee,
                                is_active=True,
                                start_date__lte=issue_date,
                                end_date__gte=issue_date
                            )
                            for discount in applicable_discounts:
                                if discount.is_applicable(student, fee): # Custom logic in FeeDiscount model
                                    discount_amount += discount.calculate_discount_amount(fee.amount)
                        
                        # Ensure discount doesn't exceed fee amount
                        discount_amount = min(discount_amount, fee.amount)

                        # Calculate tax
                        tax_amount = (fee.amount - discount_amount) * (fee.tax_rate / Decimal('100.00'))
                        
                        line_total = fee.amount + tax_amount - discount_amount

                        InvoiceItem.objects.create(
                            invoice=invoice,
                            fee_structure=fee,
                            quantity=1,
                            unit_price=fee.amount,
                            tax_rate=fee.tax_rate,
                            discount_amount=discount_amount,
                            line_total=line_total,
                            description=fee.description
                        )
                        invoice_subtotal += fee.amount
                        invoice_total_tax += tax_amount
                        invoice_total_discount += discount_amount
                    
                    invoice.subtotal = invoice_subtotal
                    invoice.total_tax = invoice_total_tax
                    invoice.total_discount = invoice_total_discount
                    invoice.total_amount = invoice_subtotal + invoice_total_tax - invoice_total_discount
                    invoice.balance_due = invoice.total_amount
                    invoice.save() # This will also generate invoice_number

                    generated_invoices.append({
                        'student': student.user.get_full_name(),
                        'status': 'created',
                        'invoice_number': invoice.invoice_number,
                        'total_amount': str(invoice.total_amount)
                    })
            
            return JsonResponse({'success': True, 'message': _('Invoices generated successfully.'), 'results': generated_invoices})

        except AcademicSession.DoesNotExist:
            return JsonResponse({'success': False, 'message': _('Academic session not found.')}, status=404)
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': _('One or more students not found.')}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': _('Invalid JSON data.')}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class GetStudentOutstandingFeesAPIView(FinanceAccessMixin, View):
    """API to get outstanding fees for a specific student."""

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)
        current_session = AcademicSession.objects.filter(is_current=True).first()

        if not current_session:
            return JsonResponse({'success': False, 'message': _('No current academic session found.')}, status=404)

        outstanding_invoices = Invoice.objects.filter(
            student=student,
            academic_session=current_session,
            balance_due__gt=Decimal('0.00'),
            status__in=['issued', 'partial', 'overdue']
        ).order_by('due_date')

        fees_data = []
        total_outstanding = Decimal('0.00')
        for invoice in outstanding_invoices:
            fees_data.append({
                'invoice_number': invoice.invoice_number,
                'billing_period': invoice.billing_period,
                'due_date': invoice.due_date.strftime('%Y-%m-%d'),
                'total_amount': str(invoice.total_amount),
                'amount_paid': str(invoice.amount_paid),
                'balance_due': str(invoice.balance_due),
                'is_overdue': invoice.is_overdue,
                'days_overdue': invoice.days_overdue,
                'late_fee_calculated': str(invoice.calculate_late_fee()),
            })
            total_outstanding += invoice.balance_due

        return JsonResponse({
            'success': True,
            'student_name': student.user.get_full_name(),
            'total_outstanding': str(total_outstanding),
            'fees': fees_data
        })


class GetExpenseSummaryAPIView(FinanceAccessMixin, View):
    """API to get a summary of expenses for a given period."""

    def get(self, request):
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        category = request.GET.get('category')

        if not all([start_date_str, end_date_str]):
            return JsonResponse({'success': False, 'message': _('Start date and end date are required.')}, status=400)

        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()

        expenses = Expense.objects.filter(
            expense_date__range=[start_date, end_date]
        )

        if category:
            expenses = expenses.filter(category=category)

        total_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        category_summary = expenses.values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')

        summary_data = []
        for item in category_summary:
            summary_data.append({
                'category': dict(Expense.ExpenseCategory.choices).get(item['category'], item['category']),
                'total': str(item['total'])
            })

        return JsonResponse({
            'success': True,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'total_expenses': str(total_amount),
            'category_summary': summary_data
        })


class GetInvoiceDetailsAPIView(FinanceAccessMixin, View):
    """API to get details of a single invoice."""
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        data = {
            'success': True,
            'invoice_number': invoice.invoice_number,
            'student_id': str(invoice.student.pk),
            'total_amount': str(invoice.total_amount),
            'amount_paid': str(invoice.amount_paid),
            'balance_due': str(invoice.balance_due),
            'issue_date': invoice.issue_date.strftime('%Y-%m-%d'),
            'due_date': invoice.due_date.strftime('%Y-%m-%d'),
            'status': invoice.get_status_display(),
        }
        return JsonResponse(data)


class PublishFinancialReportAPIView(AccountantRequiredMixin, View):
    """API to publish a financial report."""
    def post(self, request, pk):
        report = get_object_or_404(FinancialReport, pk=pk)
        if report.is_published:
            return JsonResponse({'success': False, 'message': _('Report is already published.')}, status=400)

        report.is_published = True
        report.published_at = timezone.now()
        report.save()
        messages.success(request, _(f'Financial report "{report.title}" published successfully.'))
        return JsonResponse({'success': True, 'message': _('Report published successfully.')})


# =============================================================================
# PAYSTACK AJAX API ENDPOINTS (called by Paystack inline popup JS)
# =============================================================================

@login_required
def paystack_initialize(request):
    """
    AJAX POST: Initialize a Paystack payment for an invoice.
    Expects JSON: { invoice_id, amount, email }
    Returns JSON: { success, reference, access_code } or { success, error }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        invoice_id = data.get('invoice_id')
        amount = Decimal(str(data.get('amount', 0)))
        email = data.get('email', request.user.email).strip()

        if not invoice_id or amount <= 0 or not email:
            return JsonResponse({'success': False, 'error': 'invoice_id, amount and email are required'}, status=400)

        invoice = get_object_or_404(Invoice, pk=invoice_id)

        # Basic permission check
        if hasattr(request.user, 'student_profile'):
            if invoice.student != request.user.student_profile:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        if amount > invoice.balance_due:
            return JsonResponse({'success': False, 'error': 'Amount exceeds balance due'}, status=400)

        # Create a pending payment record first
        payment = Payment.objects.create(
            invoice=invoice,
            student=invoice.student,
            amount=amount,
            payment_method=Payment.PaymentMethod.PAYSTACK,
            payment_date=timezone.now().date(),
            status=Payment.PaymentStatus.PENDING,
            paystack_customer_email=email,
            paystack_metadata={
                'invoice_id': str(invoice.pk),
                'student_id': str(invoice.student.pk),
                'source': 'inline_popup'
            }
        )

        # Build unique reference
        hex_suffix = uuid.uuid4().hex[:6].upper()
        reference = "SCH-" + str(invoice.invoice_number) + "-" + str(payment.pk) + "-" + hex_suffix
        payment.paystack_transaction_reference = reference
        payment.save(update_fields=['paystack_transaction_reference'])

        paystack_service = get_paystack_service()
        meta = {
            'payment_id': str(payment.pk),
            'invoice_id': str(invoice.pk),
            'student_name': invoice.student.user.get_full_name(),
            'invoice_number': invoice.invoice_number,
        }
        payment_data = paystack_service.initialize_payment(
            email=email,
            amount=amount,
            reference=reference,
            metadata=meta,
        )

        # Create PaystackPayment tracking record
        ps_create_kwargs = {
            'payment': payment,
            'paystack_reference': reference,
            'customer_email': email,
            'paystack_amount': amount,
            'paystack_currency': 'NGN',
        }
        access_code = payment_data.get('access_code', '')
        auth_url = payment_data.get('authorization_url', '')
        if access_code:
            ps_create_kwargs['paystack_access_code'] = access_code
        if auth_url:
            ps_create_kwargs['paystack_authorization_url'] = auth_url
        PaystackPayment.objects.create(**ps_create_kwargs)

        return JsonResponse({
            'success': True,
            'reference': reference,
            'access_code': payment_data.get('access_code'),
            'authorization_url': payment_data.get('authorization_url'),
        })

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        logger.error(f"paystack_initialize error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def paystack_verify(request):
    """
    AJAX GET: Verify a Paystack payment by reference.
    Query param: reference
    Returns JSON: { success, payment_id, redirect_url } or { success: false, error }
    """
    reference = request.GET.get('reference', '').strip()
    if not reference:
        return JsonResponse({'success': False, 'error': 'reference is required'}, status=400)

    try:
        paystack_service = get_paystack_service()
        verification_data = paystack_service.verify_payment(reference)

        if verification_data.get('status') == 'success':
            payment_service = get_payment_service()
            payment, paystack_payment = payment_service.process_payment_verification(
                reference, verification_data
            )
            # Use reverse() for a correct, namespaced URL
            redirect_url = reverse('finance:payment_success', kwargs={'pk': payment.pk})
            return JsonResponse({
                'success': True,
                'payment_id': str(payment.pk),
                'amount': str(payment.amount),
                'redirect_url': redirect_url,
            })
        else:
            pstatus = verification_data.get('status', 'unknown')
            return JsonResponse({
                'success': False,
                'error': 'Payment status: ' + str(pstatus)
            }, status=400)

    except Exception as e:
        logger.error('paystack_verify error: %s', str(e))
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# STUDENT FEE VIEWS
# =============================================================================

class StudentInvoiceListView(LoginRequiredMixin, ListView):
    """View for students to see their invoices."""
    model = Invoice
    template_name = 'finance/student/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        # Only show invoices for the logged-in student
        if hasattr(self.request.user, 'student_profile'):
            queryset = Invoice.objects.filter(
                student=self.request.user.student_profile
            ).select_related('academic_session').order_by('-issue_date')

            # Filter by status if provided
            status = self.request.GET.get('status')
            if status:
                queryset = queryset.filter(status=status)

            return queryset
        else:
            # If user is not a student, return empty queryset
            return Invoice.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice_statuses'] = Invoice.InvoiceStatus.choices

        # Calculate summary statistics
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            current_session = AcademicSession.objects.filter(is_current=True).first()

            if current_session:
                # Total outstanding amount
                outstanding_invoices = Invoice.objects.filter(
                    student=student,
                    academic_session=current_session,
                    balance_due__gt=Decimal('0.00')
                )
                total_outstanding = outstanding_invoices.aggregate(
                    Sum('balance_due')
                )['balance_due__sum'] or Decimal('0.00')

                # Recent payments
                recent_payments = Payment.objects.filter(
                    student=student
                ).select_related('invoice').order_by('-payment_date')[:5]

                context.update({
                    'total_outstanding': total_outstanding,
                    'recent_payments': recent_payments,
                    'current_session': current_session,
                })

        return context


# =============================================================================
# STUDENT FEE DASHBOARD (full overview with balance + all invoices)
# =============================================================================

class StudentFeeDashboardView(LoginRequiredMixin, View):
    """Full fee dashboard for students/parents. Shows balances + invoices + history."""

    def get(self, request):
        from django.conf import settings as django_settings

        # Determine student
        student = getattr(request.user, 'student_profile', None)
        if student is None:
            # Parent viewing child — support multi-child later; take first linked child
            parent = getattr(request.user, 'parent_profile', None)
            if parent:
                child_id = request.GET.get('child')
                if child_id:
                    student = get_object_or_404(Student, pk=child_id)
                else:
                    student = parent.children.filter(status='active').first()

        if student is None:
            messages.error(request, _('No student profile found for your account.'))
            return redirect('users:dashboard')

        current_session = AcademicSession.objects.filter(is_current=True).first()

        # All invoices for this student
        all_invoices_qs = Invoice.objects.filter(
            student=student
        ).select_related('academic_session').order_by('-issue_date')

        status_filter = request.GET.get('status', 'all')
        if status_filter == 'unpaid':
            all_invoices_qs = all_invoices_qs.filter(
                status__in=['issued', 'partial', 'overdue']
            )
        elif status_filter == 'paid':
            all_invoices_qs = all_invoices_qs.filter(status='paid')

        # Paginate
        paginator = Paginator(all_invoices_qs, 10)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        # Aggregates (all time)
        agg = Invoice.objects.filter(student=student).aggregate(
            total_invoiced=Sum('total_amount'),
            total_paid=Sum('amount_paid'),
            total_balance=Sum('balance_due'),
        )
        total_invoiced = agg['total_invoiced'] or Decimal('0.00')
        total_paid = agg['total_paid'] or Decimal('0.00')
        total_balance = agg['total_balance'] or Decimal('0.00')

        overdue_invoices = Invoice.objects.filter(
            student=student,
            due_date__lt=timezone.now().date(),
            balance_due__gt=Decimal('0.00'),
        )
        overdue_count = overdue_invoices.count()

        # Payment history
        payment_history = Payment.objects.filter(
            student=student
        ).select_related('invoice').order_by('-payment_date')[:20]

        context = {
            'student': student,
            'current_session': current_session,
            'invoices': page_obj,
            'page_obj': page_obj,
            'status_filter': status_filter,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_balance': total_balance,
            'overdue_invoices': overdue_invoices,
            'overdue_count': overdue_count,
            'payment_history': payment_history,
        }
        return render(request, 'finance/student/student_fee_dashboard.html', context)


# =============================================================================
# PAY INVOICE VIEW (student-facing, serves the inline Paystack popup page)
# =============================================================================

class PayInvoiceView(LoginRequiredMixin, View):
    """Student/parent pay-invoice page that serves the Paystack inline popup."""

    def get(self, request, pk):
        from django.conf import settings as django_settings

        invoice = get_object_or_404(Invoice, pk=pk)

        # Permission check — student owns invoice OR parent owns child
        if hasattr(request.user, 'student_profile'):
            if invoice.student != request.user.student_profile:
                messages.error(request, _('You do not have permission to view this invoice.'))
                return redirect('finance:student_dashboard')
        elif hasattr(request.user, 'parent_profile'):
            parent = request.user.parent_profile
            if invoice.student not in parent.children.all():
                messages.error(request, _('You do not have permission to view this invoice.'))
                return redirect('finance:student_dashboard')
        elif not request.user.is_staff:
            messages.error(request, _('Permission denied.'))
            return redirect('users:dashboard')

        paystack_public_key = getattr(
            django_settings, 'PAYSTACK_PUBLIC_KEY', ''
        )
        context = {
            'invoice': invoice,
            'paystack_public_key': paystack_public_key,
            'allow_bank_transfer': getattr(django_settings, 'FINANCE_ALLOW_BANK_TRANSFER', False),
        }
        return render(request, 'finance/student/pay_invoice.html', context)


# =============================================================================
# GENERIC SUCCESS / FAILED (no pk — used by AJAX verify redirect)
# =============================================================================

class GenericPaymentSuccessView(LoginRequiredMixin, View):
    """Generic payment success page — most recent payment for logged-in student."""

    def get(self, request):
        payment = None
        ref = request.GET.get('reference')
        if ref:
            payment = Payment.objects.filter(
                paystack_transaction_reference=ref
            ).select_related('invoice').first()
        if payment is None and hasattr(request.user, 'student_profile'):
            payment = Payment.objects.filter(
                student=request.user.student_profile,
                status=Payment.PaymentStatus.COMPLETED
            ).select_related('invoice').order_by('-payment_date').first()

        context = {
            'payment': payment,
        }
        return render(request, 'finance/payments/payment_success.html', context)


class GenericPaymentFailedView(LoginRequiredMixin, View):
    """Generic payment failed page."""

    def get(self, request):
        reference = request.GET.get('reference', '')
        context = {
            'reference': reference,
            'title': _('Payment Failed'),
        }
        return render(request, 'finance/payments/payment_failed.html', context)
