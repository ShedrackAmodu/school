# apps/finance/urls.py

from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # ── ACCOUNTANT DASHBOARD ─────────────────────────────────────────────────
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # ── STUDENT FEE DASHBOARD ────────────────────────────────────────────────
    path('student/dashboard/', views.StudentFeeDashboardView.as_view(), name='student_dashboard'),
    path('student/invoices/', views.StudentInvoiceListView.as_view(), name='student_invoices'),
    path('student/payments/', views.StudentPaymentListView.as_view(), name='student_payment_list'),

    # ── PAY INVOICE (student-facing, inline Paystack popup) ──────────────────
    path('student/invoices/<uuid:pk>/pay/', views.PayInvoiceView.as_view(), name='pay_invoice'),
    path('student/invoices/<uuid:invoice_pk>/pay-legacy/', views.StudentInvoicePaymentView.as_view(), name='student_invoice_payment'),

    # ── PAYSTACK AJAX ENDPOINTS ───────────────────────────────────────────────
    path('api/paystack/initialize/', views.paystack_initialize, name='paystack_initialize'),
    path('api/paystack/verify/', views.paystack_verify, name='paystack_verify'),
    path('payments/callback/<str:reference>/', views.PaymentCallbackView.as_view(), name='payment_callback'),
    path('webhooks/paystack/', views.PaystackWebhookView.as_view(), name='paystack_webhook'),

    # ── INVOICE MANAGEMENT ───────────────────────────────────────────────────
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:pk>/update/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/<uuid:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<uuid:invoice_pk>/gateway/', views.PaymentGatewayView.as_view(), name='payment_gateway'),

    # ── PAYMENT MANAGEMENT ───────────────────────────────────────────────────
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<uuid:pk>/update/', views.PaymentUpdateView.as_view(), name='payment_update'),
    path('payments/<uuid:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    path('payments/<uuid:pk>/receipt/', views.ReceiptDownloadView.as_view(), name='receipt_download'),
    path('payments/<uuid:pk>/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payments/<uuid:pk>/failed/', views.PaymentFailedView.as_view(), name='payment_failed'),
    path('payments/<uuid:pk>/cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),
    # generic success / failed without PK (redirected from Paystack verify)
    path('payment/success/', views.GenericPaymentSuccessView.as_view(), name='payment_success_generic'),
    path('payment/failed/', views.GenericPaymentFailedView.as_view(), name='payment_failed_generic'),

    # ── FEE STRUCTURES ───────────────────────────────────────────────────────
    path('fee-structures/', views.FeeStructureListView.as_view(), name='fee_structure_list'),
    path('fee-structures/create/', views.FeeStructureCreateView.as_view(), name='fee_structure_create'),
    path('fee-structures/<uuid:pk>/', views.FeeStructureDetailView.as_view(), name='fee_structure_detail'),
    path('fee-structures/<uuid:pk>/update/', views.FeeStructureUpdateView.as_view(), name='fee_structure_update'),
    path('fee-structures/<uuid:pk>/delete/', views.FeeStructureDeleteView.as_view(), name='fee_structure_delete'),
    # legacy aliases
    path('fee-structures/list/', views.FeeStructureListView.as_view(), name='feestructure_list'),
    path('fee-structures/<uuid:pk>/detail/', views.FeeStructureDetailView.as_view(), name='feestructure_detail'),

    # ── FEE DISCOUNTS ────────────────────────────────────────────────────────
    path('fee-discounts/', views.FeeDiscountListView.as_view(), name='fee_discount_list'),
    path('fee-discounts/create/', views.FeeDiscountCreateView.as_view(), name='fee_discount_create'),
    path('fee-discounts/<uuid:pk>/', views.FeeDiscountDetailView.as_view(), name='fee_discount_detail'),
    path('fee-discounts/<uuid:pk>/update/', views.FeeDiscountUpdateView.as_view(), name='fee_discount_update'),
    path('fee-discounts/<uuid:pk>/delete/', views.FeeDiscountDeleteView.as_view(), name='fee_discount_delete'),
    # legacy aliases
    path('fee-discounts/list/', views.FeeDiscountListView.as_view(), name='feediscount_list'),

    # ── EXPENSES ─────────────────────────────────────────────────────────────
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/create/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<uuid:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('expenses/<uuid:pk>/update/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('expenses/<uuid:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),

    # ── FINANCIAL REPORTS ────────────────────────────────────────────────────
    path('reports/', views.FinancialReportListView.as_view(), name='financial_report_list'),
    path('reports/create/', views.FinancialReportCreateView.as_view(), name='financial_report_create'),
    path('reports/<uuid:pk>/', views.FinancialReportDetailView.as_view(), name='financial_report_detail'),
    path('reports/<uuid:pk>/update/', views.FinancialReportUpdateView.as_view(), name='financial_report_update'),
    path('reports/<uuid:pk>/delete/', views.FinancialReportDeleteView.as_view(), name='financial_report_delete'),
    # legacy aliases
    path('reports/list/', views.FinancialReportListView.as_view(), name='financialreport_list'),

    # ── API / AJAX ENDPOINTS ─────────────────────────────────────────────────
    path('api/invoices/generate/', views.GenerateInvoiceAPIView.as_view(), name='api_generate_invoices'),
    path('api/invoices/', views.APIInvoiceListView.as_view(), name='api_invoice_list'),
    path('api/invoices/<uuid:pk>/details/', views.GetInvoiceDetailsAPIView.as_view(), name='api_invoice_details'),
    path('api/students/<uuid:student_id>/outstanding-fees/', views.GetStudentOutstandingFeesAPIView.as_view(), name='api_student_outstanding_fees'),
    path('api/expenses/summary/', views.GetExpenseSummaryAPIView.as_view(), name='api_expense_summary'),
    path('api/reports/<uuid:pk>/publish/', views.PublishFinancialReportAPIView.as_view(), name='api_publish_report'),
    path('api/payments/<uuid:payment_id>/status/', views.APIPaymentStatusView.as_view(), name='api_payment_status'),
]
