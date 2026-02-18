# apps/finance/models.py

import logging
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
import uuid
import json

logger = logging.getLogger(__name__)

from apps.core.models import CoreBaseModel, AddressModel, ContactModel
from apps.users.models import User


class FeeStructure(CoreBaseModel):
    """
    Model for defining fee structures for different classes and categories.
    """
    class FeeType(models.TextChoices):
        TUITION = 'tuition', _('Tuition Fee')
        TRANSPORT = 'transport', _('Transport Fee')
        HOSTEL = 'hostel', _('Hostel Fee')
        LIBRARY = 'library', _('Library Fee')
        LABORATORY = 'laboratory', _('Laboratory Fee')
        EXAMINATION = 'examination', _('Examination Fee')
        SPORTS = 'sports', _('Sports Fee')
        DEVELOPMENT = 'development', _('Development Fee')
        OTHER = 'other', _('Other Fee')

    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', _('Monthly')
        QUARTERLY = 'quarterly', _('Quarterly')
        HALF_YEARLY = 'half_yearly', _('Half Yearly')
        YEARLY = 'yearly', _('Yearly')
        ONE_TIME = 'one_time', _('One Time')

    name = models.CharField(_('fee structure name'), max_length=200)
    code = models.CharField(_('fee code'), max_length=50, unique=True)
    fee_type = models.CharField(
        _('fee type'),
        max_length=20,
        choices=FeeType.choices,
        default=FeeType.TUITION
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.CASCADE,
        related_name='fee_structures',
        verbose_name=_('academic session')
    )
    applicable_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='fee_structures',
        verbose_name=_('applicable class'),
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    billing_cycle = models.CharField(
        _('billing cycle'),
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )
    due_day = models.PositiveIntegerField(
        _('due day of month'),
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        default=1
    )
    is_optional = models.BooleanField(_('is optional'), default=False)
    description = models.TextField(_('description'), blank=True)
    tax_rate = models.DecimalField(
        _('tax rate (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    late_fee_per_day = models.DecimalField(
        _('late fee per day'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    max_late_fee = models.DecimalField(
        _('maximum late fee'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_eligible = models.BooleanField(_('discount eligible'), default=False)

    class Meta:
        verbose_name = _('Fee Structure')
        verbose_name_plural = _('Fee Structures')
        ordering = ['academic_session', 'fee_type', 'applicable_class']
        indexes = [
            models.Index(fields=['academic_session', 'fee_type']),
            models.Index(fields=['applicable_class', 'billing_cycle']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['academic_session', 'fee_type', 'applicable_class'],
                name='unique_fee_structure'
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.academic_session} - {self.amount}"

    @property
    def tax_amount(self):
        """Calculate tax amount for this fee."""
        return (self.amount * self.tax_rate) / Decimal('100.00')

    @property
    def total_amount(self):
        """Calculate total amount including tax."""
        return self.amount + self.tax_amount


class FeeDiscount(CoreBaseModel):
    """
    Model for managing fee discounts and concessions.
    """
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', _('Percentage')
        FIXED_AMOUNT = 'fixed_amount', _('Fixed Amount')
        FULL_WAIVER = 'full_waiver', _('Full Waiver')

    class DiscountCategory(models.TextChoices):
        SCHOLARSHIP = 'scholarship', _('Scholarship')
        SIBLING = 'sibling', _('Sibling Discount')
        EARLY_PAYMENT = 'early_payment', _('Early Payment Discount')
        STAFF = 'staff', _('Staff Discount')
        SPECIAL_NEEDS = 'special_needs', _('Special Needs')
        OTHER = 'other', _('Other')

    name = models.CharField(_('discount name'), max_length=200)
    code = models.CharField(_('discount code'), max_length=50, unique=True)
    discount_type = models.CharField(
        _('discount type'),
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    category = models.CharField(
        _('discount category'),
        max_length=20,
        choices=DiscountCategory.choices,
        default=DiscountCategory.OTHER
    )
    value = models.DecimalField(
        _('discount value'),
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    max_discount_amount = models.DecimalField(
        _('maximum discount amount'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    applicable_fee_types = models.ManyToManyField(
        FeeStructure,
        related_name='discounts',
        verbose_name=_('applicable fee types'),
        blank=True
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_active = models.BooleanField(_('is active'), default=True)
    description = models.TextField(_('description'), blank=True)
    requirements = models.JSONField(_('requirements'), default=dict, blank=True)

    class Meta:
        verbose_name = _('Fee Discount')
        verbose_name_plural = _('Fee Discounts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_discount_type_display()}"

    def calculate_discount_amount(self, base_amount):
        """Calculate discount amount based on discount type."""
        if self.discount_type == self.DiscountType.FULL_WAIVER:
            return base_amount
        elif self.discount_type == self.DiscountType.PERCENTAGE:
            discount = (base_amount * self.value) / Decimal('100.00')
            if self.max_discount_amount and discount > self.max_discount_amount:
                return self.max_discount_amount
            return discount
        elif self.discount_type == self.DiscountType.FIXED_AMOUNT:
            return min(self.value, base_amount)
        return Decimal('0.00')

    def is_applicable(self, student, fee_structure):
        """Check if discount is applicable for given student and fee structure."""
        if not self.is_active:
            return False
        today = timezone.now().date()
        if not (self.start_date <= today <= self.end_date):
            return False
        
        if self.applicable_fee_types.exists() and fee_structure not in self.applicable_fee_types.all():
            return False
        
        # Check additional requirements from JSON field
        # This can be extended based on specific requirements
        return True


class Invoice(CoreBaseModel):
    """
    Model for student fee invoices.
    """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        ISSUED = 'issued', _('Issued')
        PARTIAL = 'partial', _('Partially Paid')
        PAID = 'paid', _('Paid')
        OVERDUE = 'overdue', _('Overdue')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    invoice_number = models.CharField(
        _('invoice number'),
        max_length=50,
        unique=True,
        db_index=True
    )
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('student')
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('academic session')
    )
    billing_period = models.CharField(_('billing period'), max_length=100)
    issue_date = models.DateField(_('issue date'))
    due_date = models.DateField(_('due date'))
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_discount = models.DecimalField(
        _('total discount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_tax = models.DecimalField(
        _('total tax'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    amount_paid = models.DecimalField(
        _('amount paid'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    balance_due = models.DecimalField(
        _('balance due'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    late_fee = models.DecimalField(
        _('late fee'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    notes = models.TextField(_('notes'), blank=True)
    terms_and_conditions = models.TextField(_('terms and conditions'), blank=True)

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-issue_date', 'invoice_number']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['academic_session', 'status']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.student}"

    def save(self, *args, **kwargs):
        """Calculate totals before saving."""
        if not self.invoice_number:
            from apps.core.models import SequenceGenerator
            sequence, created = SequenceGenerator.objects.get_or_create(
                sequence_type='invoice'
            )
            self.invoice_number = sequence.get_next_number()
        
        self.balance_due = self.total_amount - self.amount_paid
        
        # Update status based on payment
        if self.amount_paid >= self.total_amount:
            self.status = self.InvoiceStatus.PAID
        elif self.amount_paid > Decimal('0.00'):
            self.status = self.InvoiceStatus.PARTIAL
        elif self.status == self.InvoiceStatus.DRAFT and self.issue_date:
            self.status = self.InvoiceStatus.ISSUED
        
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.balance_due > Decimal('0.00')

    @property
    def days_overdue(self):
        """Calculate number of days overdue."""
        from django.utils import timezone
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0

    def calculate_late_fee(self):
        """Calculate late fee based on overdue days."""
        if not self.is_overdue:
            return Decimal('0.00')
        
        total_late_fee = Decimal('0.00')
        for item in self.items.all():
            if item.fee_structure.late_fee_per_day > Decimal('0.00'):
                days_overdue = self.days_overdue
                late_fee = days_overdue * item.fee_structure.late_fee_per_day
                if item.fee_structure.max_late_fee > Decimal('0.00'):
                    late_fee = min(late_fee, item.fee_structure.max_late_fee)
                total_late_fee += late_fee
        
        return total_late_fee

    def mark_as_paid(self):
        """Mark invoice as fully paid."""
        self.amount_paid = self.total_amount
        self.balance_due = Decimal('0.00')
        self.status = self.InvoiceStatus.PAID
        self.save()


class InvoiceItem(CoreBaseModel):
    """
    Model for individual line items in an invoice.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('invoice')
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name='invoice_items',
        verbose_name=_('fee structure')
    )
    quantity = models.PositiveIntegerField(_('quantity'), default=1)
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_rate = models.DecimalField(
        _('tax rate (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        _('discount amount'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        _('line total'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')
        ordering = ['invoice', 'created_at']

    def __str__(self):
        return f"{self.fee_structure.name} - {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        """Calculate line total before saving."""
        base_amount = self.unit_price * self.quantity
        tax_amount = (base_amount * self.tax_rate) / Decimal('100.00')
        self.line_total = base_amount + tax_amount - self.discount_amount
        super().save(*args, **kwargs)


class Payment(CoreBaseModel):
    """
    Model for tracking payments against invoices.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', _('Cash')
        CHEQUE = 'cheque', _('Cheque')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        CREDIT_CARD = 'credit_card', _('Credit Card')
        DEBIT_CARD = 'debit_card', _('Debit Card')
        ONLINE = 'online', _('Online Payment')
        MOBILE = 'mobile', _('Mobile Payment')
        PAYSTACK = 'paystack', _('Paystack')
        OTHER = 'other', _('Other')

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    payment_number = models.CharField(
        _('payment number'),
        max_length=50,
        unique=True,
        db_index=True
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('invoice')
    )
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('student')
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    payment_date = models.DateField(_('payment date'))
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_payments',
        verbose_name=_('received by')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    reference_number = models.CharField(_('reference number'), max_length=100, blank=True)
    bank_name = models.CharField(_('bank name'), max_length=100, blank=True)
    cheque_number = models.CharField(_('cheque number'), max_length=50, blank=True)
    transaction_id = models.CharField(_('transaction ID'), max_length=100, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    receipt_issued = models.BooleanField(_('receipt issued'), default=False)

    # Paystack-specific fields
    paystack_payment_id = models.CharField(
        _('Paystack Payment ID'),
        max_length=100,
        blank=True,
        help_text=_('Paystack payment reference ID')
    )
    paystack_transaction_reference = models.CharField(
        _('Paystack Transaction Reference'),
        max_length=100,
        blank=True,
        help_text=_('Paystack transaction reference')
    )
    paystack_authorization_code = models.CharField(
        _('Paystack Authorization Code'),
        max_length=100,
        blank=True,
        help_text=_('Paystack authorization code for future payments')
    )
    paystack_customer_email = models.EmailField(
        _('Paystack Customer Email'),
        blank=True,
        help_text=_('Customer email used for Paystack payment')
    )
    paystack_metadata = models.JSONField(
        _('Paystack Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional metadata from Paystack')
    )

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['invoice', 'status']),
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['paystack_payment_id']),
            models.Index(fields=['paystack_transaction_reference']),
        ]

    def __str__(self):
        return f"Payment {self.payment_number} - {self.amount}"

    def save(self, *args, **kwargs):
        """Generate payment number and update invoice before saving."""
        if not self.payment_number:
            from apps.core.models import SequenceGenerator
            sequence, created = SequenceGenerator.objects.get_or_create(
                sequence_type='receipt'
            )
            self.payment_number = sequence.get_next_number()

        # Only update invoice amount_paid when status FIRST changes to COMPLETED
        if self.status == self.PaymentStatus.COMPLETED:
            is_new = self._state.adding
            if is_new:
                # Brand new payment created as completed
                from django.db import transaction
                with transaction.atomic():
                    invoice = Invoice.objects.select_for_update().get(pk=self.invoice_id)
                    invoice.amount_paid = (invoice.amount_paid or Decimal('0.00')) + self.amount
                    invoice.balance_due = max(Decimal('0.00'), invoice.total_amount - invoice.amount_paid)
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = Invoice.InvoiceStatus.PAID
                    elif invoice.amount_paid > Decimal('0.00'):
                        invoice.status = Invoice.InvoiceStatus.PARTIAL
                    invoice.save(update_fields=['amount_paid', 'balance_due', 'status'])
            else:
                # Check if status changed TO completed (avoid double-counting on re-saves)
                try:
                    old_instance = Payment.objects.get(pk=self.pk)
                    if old_instance.status != self.PaymentStatus.COMPLETED:
                        from django.db import transaction
                        with transaction.atomic():
                            invoice = Invoice.objects.select_for_update().get(pk=self.invoice_id)
                            invoice.amount_paid = (invoice.amount_paid or Decimal('0.00')) + self.amount
                            invoice.balance_due = max(Decimal('0.00'), invoice.total_amount - invoice.amount_paid)
                            if invoice.amount_paid >= invoice.total_amount:
                                invoice.status = Invoice.InvoiceStatus.PAID
                            elif invoice.amount_paid > Decimal('0.00'):
                                invoice.status = Invoice.InvoiceStatus.PARTIAL
                            invoice.save(update_fields=['amount_paid', 'balance_due', 'status'])
                except Payment.DoesNotExist:
                    pass

        super().save(*args, **kwargs)


class Expense(CoreBaseModel):
    """
    Model for tracking school expenses.
    """
    class ExpenseCategory(models.TextChoices):
        SALARIES = 'salaries', _('Salaries')
        UTILITIES = 'utilities', _('Utilities')
        MAINTENANCE = 'maintenance', _('Maintenance')
        TEACHING_AIDS = 'teaching_aids', _('Teaching Aids')
        OFFICE_SUPPLIES = 'office_supplies', _('Office Supplies')
        SPORTS_EQUIPMENT = 'sports_equipment', _('Sports Equipment')
        LAB_EQUIPMENT = 'lab_equipment', _('Laboratory Equipment')
        TRANSPORT = 'transport', _('Transport')
        RENT = 'rent', _('Rent')
        OTHER = 'other', _('Other')

    expense_number = models.CharField(
        _('expense number'),
        max_length=50,
        unique=True,
        db_index=True
    )
    category = models.CharField(
        _('category'),
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER
    )
    description = models.CharField(_('description'), max_length=500)
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    expense_date = models.DateField(_('expense date'))
    vendor = models.CharField(_('vendor'), max_length=200, blank=True)
    invoice_number = models.CharField(_('vendor invoice number'), max_length=100, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_expenses',
        verbose_name=_('approved by')
    )
    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_expenses',
        verbose_name=_('paid by')
    )
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=Payment.PaymentMethod.choices,
        default=Payment.PaymentMethod.CASH
    )
    receipt_attachment = models.ForeignKey(
        'academics.FileAttachment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('receipt attachment')
    )
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('Expense')
        verbose_name_plural = _('Expenses')
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['category', 'expense_date']),
            models.Index(fields=['expense_date', 'status']),
        ]

    def __str__(self):
        return f"Expense {self.expense_number} - {self.amount}"

    def save(self, *args, **kwargs):
        """Generate expense number before saving."""
        if not self.expense_number:
            from apps.core.models import SequenceGenerator
            sequence, created = SequenceGenerator.objects.get_or_create(
                sequence_type='expense'
            )
            self.expense_number = sequence.get_next_number()
        super().save(*args, **kwargs)


class FinancialReport(CoreBaseModel):
    """
    Model for storing generated financial reports.
    """
    class ReportType(models.TextChoices):
        INCOME_STATEMENT = 'income_statement', _('Income Statement')
        BALANCE_SHEET = 'balance_sheet', _('Balance Sheet')
        CASH_FLOW = 'cash_flow', _('Cash Flow Statement')
        FEE_COLLECTION = 'fee_collection', _('Fee Collection Report')
        EXPENSE_SUMMARY = 'expense_summary', _('Expense Summary')
        OUTSTANDING_FEES = 'outstanding_fees', _('Outstanding Fees Report')
        STUDENT_LEDGER = 'student_ledger', _('Student Ledger')

    report_number = models.CharField(
        _('report number'),
        max_length=50,
        unique=True,
        db_index=True
    )
    report_type = models.CharField(
        _('report type'),
        max_length=20,
        choices=ReportType.choices
    )
    title = models.CharField(_('report title'), max_length=200)
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.CASCADE,
        related_name='financial_reports',
        verbose_name=_('academic session')
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    generated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='financial_reports',
        verbose_name=_('generated by')
    )
    report_data = models.JSONField(_('report data'), default=dict)
    summary = models.TextField(_('summary'), blank=True)
    is_published = models.BooleanField(_('is published'), default=False)
    published_at = models.DateTimeField(_('published at'), null=True, blank=True)

    class Meta:
        verbose_name = _('Financial Report')
        verbose_name_plural = _('Financial Reports')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'academic_session']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.academic_session}"

    def save(self, *args, **kwargs):
        """Generate report number before saving."""
        if not self.report_number:
            from apps.core.models import SequenceGenerator
            sequence, created = SequenceGenerator.objects.get_or_create(
                sequence_type='financial_report'
            )
            self.report_number = sequence.get_next_number()
        super().save(*args, **kwargs)


# ============================
# PAYSTACK INTEGRATION MODELS
# ============================

class PaystackPayment(CoreBaseModel):
    """
    Model for tracking Paystack payment transactions.
    This provides detailed tracking of Paystack-specific payment data.
    """
    class PaystackStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        SUCCESS = 'success', _('Success')
        FAILED = 'failed', _('Failed')
        ABANDONED = 'abandoned', _('Abandoned')
        CANCELLED = 'cancelled', _('Cancelled')

    # Payment Reference
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='paystack_details',
        verbose_name=_('payment')
    )
    paystack_reference = models.CharField(
        _('Paystack Reference'),
        max_length=100,
        unique=True,
        db_index=True
    )
    paystack_transaction_id = models.CharField(
        _('Paystack Transaction ID'),
        max_length=100,
        blank=True
    )
    paystack_access_code = models.CharField(
        _('Paystack Access Code'),
        max_length=100,
        blank=True
    )
    paystack_authorization_url = models.URLField(
        _('Paystack Authorization URL'),
        blank=True
    )

    # Customer Information
    customer_email = models.EmailField(_('customer email'))
    customer_name = models.CharField(_('customer name'), max_length=200, blank=True)
    customer_phone = models.CharField(_('customer phone'), max_length=20, blank=True)

    # Payment Details
    paystack_status = models.CharField(
        _('Paystack Status'),
        max_length=20,
        choices=PaystackStatus.choices,
        default=PaystackStatus.PENDING
    )
    paystack_amount = models.DecimalField(
        _('Paystack Amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    paystack_currency = models.CharField(_('Paystack Currency'), max_length=3, default='NGN')
    paystack_fees = models.DecimalField(
        _('Paystack Fees'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    paystack_fees_deducted = models.DecimalField(
        _('Paystack Fees Deducted'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    paystack_amount_received = models.DecimalField(
        _('Paystack Amount Received'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Authorization Code (for future payments)
    authorization_code = models.CharField(
        _('Authorization Code'),
        max_length=100,
        blank=True
    )
    authorization_channel = models.CharField(
        _('Authorization Channel'),
        max_length=50,
        blank=True
    )
    authorization_bin = models.CharField(_('Authorization BIN'), max_length=20, blank=True)
    authorization_last4 = models.CharField(_('Authorization Last 4'), max_length=10, blank=True)
    authorization_exp_month = models.CharField(_('Authorization Exp Month'), max_length=2, blank=True)
    authorization_exp_year = models.CharField(_('Authorization Exp Year'), max_length=4, blank=True)
    authorization_card_type = models.CharField(_('Authorization Card Type'), max_length=50, blank=True)
    authorization_bank = models.CharField(_('Authorization Bank'), max_length=100, blank=True)
    authorization_country_code = models.CharField(_('Authorization Country Code'), max_length=3, blank=True)

    # Metadata and Response Data
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    paystack_response = models.JSONField(_('Paystack Response'), default=dict, blank=True)

    # Timing
    paystack_created_at = models.DateTimeField(_('Paystack Created At'), null=True, blank=True)
    paystack_paid_at = models.DateTimeField(_('Paystack Paid At'), null=True, blank=True)
    paystack_updated_at = models.DateTimeField(_('Paystack Updated At'), null=True, blank=True)

    class Meta:
        verbose_name = _('Paystack Payment')
        verbose_name_plural = _('Paystack Payments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['customer_email']),
            models.Index(fields=['paystack_status']),
            models.Index(fields=['authorization_code']),
        ]

    def __str__(self):
        return f"Paystack Payment {self.paystack_reference} - {self.customer_email}"

    def update_from_paystack_response(self, response_data):
        """Update model fields from Paystack API response."""
        if not response_data:
            return

        # Basic payment information
        self.paystack_reference = response_data.get('reference', self.paystack_reference)
        self.paystack_transaction_id = response_data.get('id', self.paystack_transaction_id)
        self.paystack_access_code = response_data.get('access_code', self.paystack_access_code)
        self.paystack_authorization_url = response_data.get('authorization_url', self.paystack_authorization_url)

        # Customer information
        customer = response_data.get('customer', {})
        self.customer_email = customer.get('email', self.customer_email)
        self.customer_name = customer.get('first_name', '') + ' ' + customer.get('last_name', '')
        self.customer_phone = customer.get('phone', self.customer_phone)

        # Payment details
        self.paystack_amount = Decimal(str(response_data.get('amount', 0))) / Decimal('100')  # Paystack returns amount in kobo
        self.paystack_currency = response_data.get('currency', self.paystack_currency)
        self.paystack_fees = Decimal(str(response_data.get('fees', 0))) / Decimal('100')
        self.paystack_fees_deducted = Decimal(str(response_data.get('fees_deducted', 0))) / Decimal('100')
        self.paystack_amount_received = Decimal(str(response_data.get('amount_received', 0))) / Decimal('100')

        # Status
        status_map = {
            'success': self.PaystackStatus.SUCCESS,
            'failed': self.PaystackStatus.FAILED,
            'abandoned': self.PaystackStatus.ABANDONED,
            'pending': self.PaystackStatus.PENDING,
        }
        paystack_status = response_data.get('status', 'pending')
        self.paystack_status = status_map.get(paystack_status, self.PaystackStatus.PENDING)

        # Authorization details
        authorization = response_data.get('authorization', {})
        self.authorization_code = authorization.get('authorization_code', self.authorization_code)
        self.authorization_channel = authorization.get('channel', self.authorization_channel)
        self.authorization_bin = authorization.get('bin', self.authorization_bin)
        self.authorization_last4 = authorization.get('last4', self.authorization_last4)
        self.authorization_exp_month = authorization.get('exp_month', self.authorization_exp_month)
        self.authorization_exp_year = authorization.get('exp_year', self.authorization_exp_year)
        self.authorization_card_type = authorization.get('card_type', self.authorization_card_type)
        self.authorization_bank = authorization.get('bank', self.authorization_bank)
        self.authorization_country_code = authorization.get('country_code', self.authorization_country_code)

        # Timing
        self.paystack_created_at = self._parse_paystack_datetime(response_data.get('createdAt'))
        self.paystack_paid_at = self._parse_paystack_datetime(response_data.get('paidAt'))
        self.paystack_updated_at = self._parse_paystack_datetime(response_data.get('updatedAt'))

        # Store full response for debugging
        self.paystack_response = response_data

        self.save()

    def _parse_paystack_datetime(self, datetime_str):
        """Parse Paystack datetime string to Python datetime object."""
        if not datetime_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None

    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.paystack_status == self.PaystackStatus.SUCCESS

    @property
    def is_pending(self):
        """Check if payment is still pending."""
        return self.paystack_status == self.PaystackStatus.PENDING

    @property
    def is_failed(self):
        """Check if payment failed."""
        return self.paystack_status == self.PaystackStatus.FAILED


class PaystackWebhookEvent(CoreBaseModel):
    """
    Model for logging Paystack webhook events for debugging and audit purposes.
    """
    class WebhookEventType(models.TextChoices):
        CHARGE_SUCCESS = 'charge.success', _('Charge Success')
        CHARGE_FAILED = 'charge.failed', _('Charge Failed')
        CHARGE_ABANDONED = 'charge.abandoned', _('Charge Abandoned')
        TRANSFER_SUCCESS = 'transfer.success', _('Transfer Success')
        TRANSFER_FAILED = 'transfer.failed', _('Transfer Failed')
        CUSTOMER_CREATED = 'customer.created', _('Customer Created')
        INVOICE_CREATED = 'invoice.created', _('Invoice Created')
        INVOICE_PAYMENT_FAILED = 'invoice.payment_failed', _('Invoice Payment Failed')
        INVOICE_UPDATED = 'invoice.updated', _('Invoice Updated')
        INVOICE_ARCHIVE = 'invoice.archive', _('Invoice Archive')
        SUBSCRIPTION_CREATE = 'subscription.create', _('Subscription Create')
        SUBSCRIPTION_DISABLE = 'subscription.disable', _('Subscription Disable')
        SUBSCRIPTION_ENABLE = 'subscription.enable', _('Subscription Enable')
        SUBSCRIPTION_UPDATE = 'subscription.update', _('Subscription Update')
        PLAN_CREATE = 'plan.create', _('Plan Create')
        PLAN_UPDATE = 'plan.update', _('Plan Update')
        OTHER = 'other', _('Other')

    event_type = models.CharField(
        _('event type'),
        max_length=50,
        choices=WebhookEventType.choices,
        default=WebhookEventType.OTHER
    )
    event_data = models.JSONField(_('event data'), default=dict)
    event_reference = models.CharField(_('event reference'), max_length=100, blank=True)
    event_timestamp = models.DateTimeField(_('event timestamp'))
    processed = models.BooleanField(_('processed'), default=False)
    processed_at = models.DateTimeField(_('processed at'), null=True, blank=True)
    processing_error = models.TextField(_('processing error'), blank=True)

    # Related objects
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paystack_webhooks',
        verbose_name=_('payment')
    )
    paystack_payment = models.ForeignKey(
        PaystackPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhooks',
        verbose_name=_('paystack payment')
    )

    class Meta:
        verbose_name = _('Paystack Webhook Event')
        verbose_name_plural = _('Paystack Webhook Events')
        ordering = ['-event_timestamp', '-created_at']
        indexes = [
            models.Index(fields=['event_type', 'processed']),
            models.Index(fields=['event_reference']),
            models.Index(fields=['event_timestamp']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.event_reference}"

    def process_webhook(self):
        """
        Process the webhook event based on its type.
        """
        try:
            event_type = self.event_type
            event_data = self.event_data

            if event_type == self.WebhookEventType.CHARGE_SUCCESS:
                return self._handle_charge_success(event_data)
            elif event_type == self.WebhookEventType.CHARGE_FAILED:
                return self._handle_charge_failed(event_data)
            elif event_type == self.WebhookEventType.CHARGE_ABANDONED:
                return self._handle_charge_abandoned(event_data)
            elif event_type == self.WebhookEventType.CUSTOMER_CREATED:
                return self._handle_customer_created(event_data)
            elif event_type == self.WebhookEventType.INVOICE_CREATED:
                return self._handle_invoice_created(event_data)
            elif event_type == self.WebhookEventType.INVOICE_PAYMENT_FAILED:
                return self._handle_invoice_payment_failed(event_data)
            else:
                # Log unknown event types but don't mark as failed
                logger.info(f"Unknown Paystack webhook event type: {event_type}")
                return True

        except Exception as e:
            logger.error(f"Error processing webhook {self.event_reference}: {e}")
            return False

    def _handle_charge_success(self, event_data):
        """Handle successful charge webhook."""
        try:
            reference = event_data.get('data', {}).get('reference')
            if not reference:
                return False

            # Get the PaystackPayment record
            paystack_payment = PaystackPayment.objects.get(paystack_reference=reference)
            payment = paystack_payment.payment

            # Update PaystackPayment with response data
            paystack_payment.update_from_paystack_response(event_data)

            # Update main Payment record
            if paystack_payment.is_successful:
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.paystack_transaction_reference = reference
                payment.save()

                # Mark invoice as paid if fully paid
                if payment.invoice.balance_due <= Decimal('0.00'):
                    payment.invoice.mark_as_paid()

            return True

        except PaystackPayment.DoesNotExist:
            logger.error(f"PaystackPayment with reference {reference} not found for charge.success event")
            return False
        except Exception as e:
            logger.error(f"Error handling charge.success event: {e}")
            return False

    def _handle_charge_failed(self, event_data):
        """Handle failed charge webhook."""
        try:
            reference = event_data.get('data', {}).get('reference')
            if not reference:
                return False

            paystack_payment = PaystackPayment.objects.get(paystack_reference=reference)
            paystack_payment.paystack_status = paystack_payment.PaystackStatus.FAILED
            paystack_payment.save()

            payment = paystack_payment.payment
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()

            return True

        except PaystackPayment.DoesNotExist:
            logger.error(f"PaystackPayment with reference {reference} not found for charge.failed event")
            return False
        except Exception as e:
            logger.error(f"Error handling charge.failed event: {e}")
            return False

    def _handle_charge_abandoned(self, event_data):
        """Handle abandoned charge webhook."""
        try:
            reference = event_data.get('data', {}).get('reference')
            if not reference:
                return False

            paystack_payment = PaystackPayment.objects.get(paystack_reference=reference)
            paystack_payment.paystack_status = paystack_payment.PaystackStatus.ABANDONED
            paystack_payment.save()

            payment = paystack_payment.payment
            payment.status = Payment.PaymentStatus.CANCELLED
            payment.save()

            return True

        except PaystackPayment.DoesNotExist:
            logger.error(f"PaystackPayment with reference {reference} not found for charge.abandoned event")
            return False
        except Exception as e:
            logger.error(f"Error handling charge.abandoned event: {e}")
            return False

    def _handle_customer_created(self, event_data):
        """Handle customer created webhook."""
        try:
            customer_data = event_data.get('data', {}).get('customer', {})
            customer_code = customer_data.get('customer_code')
            
            if customer_code:
                # Update any existing payment methods with this customer code
                PaymentMethod.objects.filter(
                    paystack_customer_code=customer_code
                ).update(
                    is_verified=True
                )
            
            return True

        except Exception as e:
            logger.error(f"Error handling customer.created event: {e}")
            return False

    def _handle_invoice_created(self, event_data):
        """Handle invoice created webhook."""
        try:
            # This is typically handled by our system, but we can log it
            logger.info(f"Invoice created webhook received: {event_data.get('data', {}).get('reference')}")
            return True

        except Exception as e:
            logger.error(f"Error handling invoice.created event: {e}")
            return False

    def _handle_invoice_payment_failed(self, event_data):
        """Handle invoice payment failed webhook."""
        try:
            reference = event_data.get('data', {}).get('reference')
            if not reference:
                return False

            # Find the payment and mark it as failed
            try:
                paystack_payment = PaystackPayment.objects.get(paystack_reference=reference)
                paystack_payment.paystack_status = paystack_payment.PaystackStatus.FAILED
                paystack_payment.save()

                payment = paystack_payment.payment
                payment.status = Payment.PaymentStatus.FAILED
                payment.save()
            except PaystackPayment.DoesNotExist:
                # If no PaystackPayment found, try to find by transaction reference
                payment = Payment.objects.filter(
                    paystack_transaction_reference=reference
                ).first()
                if payment:
                    payment.status = Payment.PaymentStatus.FAILED
                    payment.save()

            return True

        except Exception as e:
            logger.error(f"Error handling invoice.payment_failed event: {e}")
            return False


class PaymentMethod(CoreBaseModel):
    """
    Model for storing saved payment methods (cards) for future use.
    """
    class PaymentMethodType(models.TextChoices):
        CARD = 'card', _('Card')
        BANK = 'bank', _('Bank Account')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name=_('user')
    )
    institution = models.ForeignKey(
        'core.Institution',
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name=_('institution')
    )
    payment_method_type = models.CharField(
        _('payment method type'),
        max_length=10,
        choices=PaymentMethodType.choices,
        default=PaymentMethodType.CARD
    )
    paystack_authorization_code = models.CharField(
        _('Paystack Authorization Code'),
        max_length=100,
        unique=True
    )
    paystack_customer_code = models.CharField(
        _('Paystack Customer Code'),
        max_length=100
    )
    card_bin = models.CharField(_('Card BIN'), max_length=20, blank=True)
    last4 = models.CharField(_('Last 4 digits'), max_length=10, blank=True)
    exp_month = models.CharField(_('Expiry Month'), max_length=2, blank=True)
    exp_year = models.CharField(_('Expiry Year'), max_length=4, blank=True)
    card_type = models.CharField(_('Card Type'), max_length=50, blank=True)
    bank = models.CharField(_('Bank'), max_length=100, blank=True)
    country_code = models.CharField(_('Country Code'), max_length=3, blank=True)
    channel = models.CharField(_('Channel'), max_length=50, blank=True)
    reusable = models.BooleanField(_('Reusable'), default=True)
    is_default = models.BooleanField(_('Default Method'), default=False)

    class Meta:
        verbose_name = _('Payment Method')
        verbose_name_plural = _('Payment Methods')
        ordering = ['-created_at']
        unique_together = ['user', 'paystack_authorization_code']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['paystack_authorization_code']),
            models.Index(fields=['paystack_customer_code']),
        ]

    def __str__(self):
        return f"{self.user} - {self.card_type} ending in {self.last4}"

    def save(self, *args, **kwargs):
        """Ensure only one default payment method per user per institution."""
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                institution=self.institution,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default_for_user(cls, user, institution):
        """Get the default payment method for a user in an institution."""
        return cls.objects.filter(
            user=user,
            institution=institution,
            is_default=True,
            reusable=True
        ).first()