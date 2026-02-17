# apps/finance/services.py
"""
Paystack integration services for handling payment processing.
"""

import requests
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Payment, PaystackPayment, PaystackWebhookEvent, Invoice, PaymentMethod
from apps.users.models import User
from apps.core.models import Institution

logger = logging.getLogger(__name__)


class PaystackService:
    """
    Service class for handling Paystack API interactions.
    """

    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
        self.currency = getattr(settings, 'PAYSTACK_CURRENCY', 'NGN')
        self.callback_url = getattr(settings, 'PAYSTACK_CALLBACK_URL', '')
        self.webhook_secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')

        if not self.secret_key or not self.public_key:
            logger.warning("Paystack API keys not configured properly")

    def _make_request(self, method, endpoint, data=None, headers=None):
        """
        Make HTTP request to Paystack API.
        """
        url = f"{self.base_url}{endpoint}"
        default_headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if headers:
            default_headers.update(headers)

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=default_headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=default_headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {e}")
            raise ValidationError(f"Paystack API error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Paystack: {e}")
            raise ValidationError("Invalid response from Paystack")

    def initialize_payment(self, email, amount, reference, metadata=None, callback_url=None, channels=None):
        """
        Initialize a payment with Paystack.
        """
        if not email or not amount or not reference:
            raise ValidationError("Email, amount, and reference are required")

        # Convert amount to kobo (Paystack expects amount in kobo)
        amount_in_kobo = int(amount * 100)

        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'currency': self.currency,
            'callback_url': callback_url or self.callback_url,
            'channels': channels or getattr(settings, 'PAYSTACK_PAYMENT_CHANNELS', ['card']),
        }

        if metadata:
            payload['metadata'] = metadata

        response = self._make_request('POST', '/transaction/initialize', payload)
        
        if response.get('status'):
            return {
                'authorization_url': response['data']['authorization_url'],
                'access_code': response['data']['access_code'],
                'reference': response['data']['reference'],
                'message': response['message']
            }
        else:
            raise ValidationError(f"Payment initialization failed: {response.get('message', 'Unknown error')}")

    def verify_payment(self, reference):
        """
        Verify a payment with Paystack using reference.
        """
        if not reference:
            raise ValidationError("Reference is required for payment verification")

        response = self._make_request('GET', f'/transaction/verify/{reference}')
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Payment verification failed: {response.get('message', 'Unknown error')}")

    def create_customer(self, email, first_name=None, last_name=None, phone=None):
        """
        Create a customer in Paystack.
        """
        if not email:
            raise ValidationError("Email is required for customer creation")

        payload = {'email': email}
        if first_name:
            payload['first_name'] = first_name
        if last_name:
            payload['last_name'] = last_name
        if phone:
            payload['phone'] = phone

        response = self._make_request('POST', '/customer', payload)
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Customer creation failed: {response.get('message', 'Unknown error')}")

    def charge_authorization(self, authorization_code, email, amount, reference, metadata=None):
        """
        Charge a customer using saved authorization code.
        """
        if not authorization_code or not email or not amount or not reference:
            raise ValidationError("Authorization code, email, amount, and reference are required")

        # Convert amount to kobo
        amount_in_kobo = int(amount * 100)

        payload = {
            'authorization_code': authorization_code,
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'currency': self.currency,
        }

        if metadata:
            payload['metadata'] = metadata

        response = self._make_request('POST', '/charge/authorize', payload)
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Authorization charge failed: {response.get('message', 'Unknown error')}")

    def get_payment_methods(self, customer_email):
        """
        Get available payment methods for a customer.
        """
        if not customer_email:
            raise ValidationError("Customer email is required")

        response = self._make_request('GET', f'/customer/{customer_email}/payment_method')
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Failed to get payment methods: {response.get('message', 'Unknown error')}")

    def list_banks(self):
        """
        Get list of supported banks for transfers.
        """
        response = self._make_request('GET', '/bank')
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Failed to get banks list: {response.get('message', 'Unknown error')}")

    def resolve_bank_account(self, account_number, bank_code):
        """
        Resolve bank account details.
        """
        if not account_number or not bank_code:
            raise ValidationError("Account number and bank code are required")

        payload = {
            'account_number': account_number,
            'bank_code': bank_code
        }

        response = self._make_request('GET', '/bank/resolve', payload)
        
        if response.get('status'):
            return response['data']
        else:
            raise ValidationError(f"Failed to resolve bank account: {response.get('message', 'Unknown error')}")


class PaymentService:
    """
    Service class for handling payment business logic.
    """

    @staticmethod
    def create_paystack_payment(payment, paystack_reference, authorization_url=None, access_code=None):
        """
        Create a PaystackPayment record linked to a Payment.
        """
        paystack_payment = PaystackPayment.objects.create(
            payment=payment,
            paystack_reference=paystack_reference,
            paystack_access_code=access_code,
            paystack_authorization_url=authorization_url,
            customer_email=payment.paystack_customer_email or payment.student.user.email,
            paystack_amount=payment.amount,
            paystack_currency='NGN',
            institution=payment.institution
        )
        return paystack_payment

    @staticmethod
    def process_payment_verification(payment_reference, paystack_response_data):
        """
        Process payment verification and update related models.
        """
        try:
            with transaction.atomic():
                # Get the PaystackPayment record
                paystack_payment = PaystackPayment.objects.select_for_update().get(
                    paystack_reference=payment_reference
                )
                payment = paystack_payment.payment

                # Update PaystackPayment with response data
                paystack_payment.update_from_paystack_response(paystack_response_data)

                # Update main Payment record based on status
                if paystack_payment.is_successful:
                    payment.status = Payment.PaymentStatus.COMPLETED
                    payment.paystack_transaction_reference = paystack_reference
                    payment.save()

                    # Mark invoice as paid if fully paid
                    if payment.invoice.balance_due <= Decimal('0.00'):
                        payment.invoice.mark_as_paid()

                elif paystack_payment.is_failed:
                    payment.status = Payment.PaymentStatus.FAILED
                    payment.save()

                elif paystack_payment.paystack_status == paystack_payment.PaystackStatus.ABANDONED:
                    payment.status = Payment.PaymentStatus.CANCELLED
                    payment.save()

                return payment, paystack_payment

        except PaystackPayment.DoesNotExist:
            logger.error(f"PaystackPayment with reference {payment_reference} not found")
            raise ValidationError("Payment record not found")
        except Exception as e:
            logger.error(f"Error processing payment verification: {e}")
            raise ValidationError(f"Error processing payment: {str(e)}")

    @staticmethod
    def create_payment_from_invoice(invoice, amount=None, payment_method='paystack', customer_email=None, metadata=None):
        """
        Create a Payment record from an Invoice.
        """
        if amount is None:
            amount = invoice.balance_due

        if amount <= Decimal('0.00'):
            raise ValidationError("Payment amount must be greater than zero")

        if amount > invoice.balance_due:
            raise ValidationError("Payment amount cannot exceed invoice balance")

        # Create Payment record
        payment = Payment.objects.create(
            invoice=invoice,
            student=invoice.student,
            amount=amount,
            payment_method=payment_method,
            payment_date=timezone.now().date(),
            status=Payment.PaymentStatus.PENDING,
            institution=invoice.institution,
            paystack_customer_email=customer_email or invoice.student.user.email,
            paystack_metadata=metadata or {}
        )

        return payment

    @staticmethod
    def save_payment_method(user, institution, paystack_customer_data, paystack_authorization_data):
        """
        Save a payment method for future use.
        """
        # Check if customer already exists in our system
        existing_method = PaymentMethod.objects.filter(
            user=user,
            institution=institution,
            paystack_customer_code=paystack_customer_data.get('customer_code')
        ).first()

        if existing_method:
            # Update existing method
            existing_method.paystack_authorization_code = paystack_authorization_data.get('authorization_code')
            existing_method.card_bin = paystack_authorization_data.get('bin')
            existing_method.last4 = paystack_authorization_data.get('last4')
            existing_method.exp_month = paystack_authorization_data.get('exp_month')
            existing_method.exp_year = paystack_authorization_data.get('exp_year')
            existing_method.card_type = paystack_authorization_data.get('card_type')
            existing_method.bank = paystack_authorization_data.get('bank')
            existing_method.country_code = paystack_authorization_data.get('country_code')
            existing_method.channel = paystack_authorization_data.get('channel')
            existing_method.reusable = paystack_authorization_data.get('reusable', True)
            existing_method.save()
            return existing_method

        # Create new payment method
        payment_method = PaymentMethod.objects.create(
            user=user,
            institution=institution,
            payment_method_type=PaymentMethod.PaymentMethodType.CARD,
            paystack_authorization_code=paystack_authorization_data.get('authorization_code'),
            paystack_customer_code=paystack_customer_data.get('customer_code'),
            card_bin=paystack_authorization_data.get('bin'),
            last4=paystack_authorization_data.get('last4'),
            exp_month=paystack_authorization_data.get('exp_month'),
            exp_year=paystack_authorization_data.get('exp_year'),
            card_type=paystack_authorization_data.get('card_type'),
            bank=paystack_authorization_data.get('bank'),
            country_code=paystack_authorization_data.get('country_code'),
            channel=paystack_authorization_data.get('channel'),
            reusable=paystack_authorization_data.get('reusable', True),
            is_default=True  # Set as default for first saved method
        )

        return payment_method

    @staticmethod
    def charge_saved_payment_method(payment_method, amount, reference, metadata=None):
        """
        Charge a customer using a saved payment method.
        """
        paystack_service = PaystackService()
        
        try:
            response = paystack_service.charge_authorization(
                authorization_code=payment_method.paystack_authorization_code,
                email=payment_method.user.email,
                amount=amount,
                reference=reference,
                metadata=metadata
            )
            return response
        except Exception as e:
            logger.error(f"Failed to charge saved payment method: {e}")
            raise ValidationError(f"Failed to charge saved payment method: {str(e)}")


class WebhookService:
    """
    Service class for handling Paystack webhooks.
    """

    @staticmethod
    def verify_webhook_signature(request_body, signature):
        """
        Verify Paystack webhook signature.
        """
        import hashlib
        import hmac

        webhook_secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')
        if not webhook_secret:
            logger.warning("Paystack webhook secret not configured")
            return False

        # Compute signature
        computed_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            request_body,
            hashlib.sha512
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(signature, computed_signature)

    @staticmethod
    def process_webhook_event(event_type, event_data, event_reference, event_timestamp):
        """
        Process a Paystack webhook event.
        """
        # Log the webhook event
        webhook_event = PaystackWebhookEvent.objects.create(
            event_type=event_type,
            event_data=event_data,
            event_reference=event_reference,
            event_timestamp=event_timestamp
        )

        # Process the event
        success = webhook_event.process_webhook()

        if not success:
            logger.error(f"Failed to process webhook event: {event_type} - {event_reference}")

        return webhook_event, success

    @staticmethod
    def handle_charge_success_event(event_data):
        """
        Handle charge.success webhook event.
        """
        reference = event_data.get('data', {}).get('reference')
        if not reference:
            return False

        try:
            paystack_service = PaystackService()
            verification_data = paystack_service.verify_payment(reference)
            
            if verification_data.get('status') == 'success':
                payment, paystack_payment = PaymentService.process_payment_verification(
                    reference, verification_data
                )
                return True
        except Exception as e:
            logger.error(f"Error handling charge.success event: {e}")
            return False

        return False

    @staticmethod
    def handle_charge_failed_event(event_data):
        """
        Handle charge.failed webhook event.
        """
        reference = event_data.get('data', {}).get('reference')
        if not reference:
            return False

        try:
            paystack_payment = PaystackPayment.objects.get(paystack_reference=reference)
            paystack_payment.paystack_status = paystack_payment.PaystackStatus.FAILED
            paystack_payment.save()

            payment = paystack_payment.payment
            payment.status = Payment.PaymentStatus.FAILED
            payment.save()

            return True
        except PaystackPayment.DoesNotExist:
            logger.error(f"PaystackPayment with reference {reference} not found for failed event")
            return False
        except Exception as e:
            logger.error(f"Error handling charge.failed event: {e}")
            return False


def get_paystack_service():
    """
    Get an instance of PaystackService.
    """
    return PaystackService()


def get_payment_service():
    """
    Get an instance of PaymentService.
    """
    return PaymentService()


def get_webhook_service():
    """
    Get an instance of WebhookService.
    """
    return WebhookService()