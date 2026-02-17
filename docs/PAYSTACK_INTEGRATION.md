# Paystack Integration Documentation

This document provides comprehensive information about the Paystack payment integration in the NexusSMS system.

## Overview

The Paystack integration provides a complete payment processing solution for school fee payments, including:

- **Online Payment Processing**: Secure payment gateway integration with Paystack
- **Payment Tracking**: Detailed tracking of payment transactions and statuses
- **Webhook Handling**: Automatic processing of payment status updates
- **Multi-tenant Support**: Payment processing across multiple institutions
- **Student/Parent Interface**: User-friendly payment interface for students and parents

## Architecture

### Core Components

1. **PaystackPayment Model**: Tracks Paystack-specific payment data
2. **PaystackWebhookEvent Model**: Logs and processes webhook events
3. **PaymentService**: Business logic for payment processing
4. **PaystackService**: API integration with Paystack
5. **WebhookService**: Webhook event processing

### Payment Flow

```
Student/Parent → Payment Gateway → Paystack → Webhook → System Update
```

## Models

### PaystackPayment

Tracks detailed Paystack payment information:

- **paystack_reference**: Unique Paystack transaction reference
- **customer_email**: Customer email for payment
- **paystack_status**: Payment status (pending, success, failed, abandoned)
- **authorization_code**: Reusable authorization code for future payments
- **paystack_amount**: Amount in NGN
- **paystack_fees**: Paystack processing fees
- **paystack_response**: Full API response for debugging

### PaystackWebhookEvent

Logs and processes webhook events:

- **event_type**: Type of webhook event (charge.success, charge.failed, etc.)
- **event_data**: Full webhook payload
- **processed**: Whether the event has been processed
- **processing_error**: Error details if processing failed

### PaymentMethod

Stores saved payment methods for future use:

- **paystack_authorization_code**: Reusable authorization code
- **paystack_customer_code**: Customer identifier in Paystack
- **card details**: Last 4 digits, expiry, card type, bank
- **is_default**: Whether this is the default payment method

## Configuration

### Settings

Add to `config/settings.py`:

```python
# Paystack API Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'your_secret_key')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'your_public_key')
PAYSTACK_TEST_MODE = os.getenv('PAYSTACK_TEST_MODE', 'True').lower() == 'true'

# Paystack URLs
PAYSTACK_BASE_URL = 'https://api.paystack.co' if not PAYSTACK_TEST_MODE else 'https://api.paystack.co'
PAYSTACK_PAYMENT_URL = f'{PAYSTACK_BASE_URL}/transaction'
PAYSTACK_CUSTOMER_URL = f'{PAYSTACK_BASE_URL}/customer'

# Paystack Webhook Configuration
PAYSTACK_WEBHOOK_SECRET = os.getenv('PAYSTACK_WEBHOOK_SECRET', 'your_webhook_secret')
PAYSTACK_WEBHOOK_URL = '/finance/webhooks/paystack/'

# Paystack Payment Settings
PAYSTACK_CURRENCY = 'NGN'
PAYSTACK_PAYMENT_CHANNELS = ['card', 'bank', 'ussd', 'qr', 'mobile_money']
PAYSTACK_CALLBACK_URL = os.getenv('PAYSTACK_CALLBACK_URL', 'http://localhost:8000/finance/payments/callback/')
```

### Environment Variables

Required environment variables:

- `PAYSTACK_SECRET_KEY`: Paystack secret key
- `PAYSTACK_PUBLIC_KEY`: Paystack public key
- `PAYSTACK_WEBHOOK_SECRET`: Webhook secret for signature verification
- `PAYSTACK_CALLBACK_URL`: URL for payment callback

## API Integration

### PaystackService

The `PaystackService` class handles all Paystack API interactions:

```python
from apps.finance.services import get_paystack_service

paystack = get_paystack_service()

# Initialize payment
payment_data = paystack.initialize_payment(
    email='student@example.com',
    amount=Decimal('10000.00'),
    reference='INV-12345-001',
    callback_url='https://yourschool.com/callback/'
)

# Verify payment
verification_data = paystack.verify_payment('INV-12345-001')

# Create customer
customer_data = paystack.create_customer(
    email='student@example.com',
    first_name='John',
    last_name='Doe'
)
```

### PaymentService

The `PaymentService` class handles payment business logic:

```python
from apps.finance.services import get_payment_service

payment_service = get_payment_service()

# Create payment from invoice
payment = payment_service.create_payment_from_invoice(
    invoice=invoice,
    amount=invoice.balance_due,
    payment_method='paystack'
)

# Process payment verification
payment, paystack_payment = payment_service.process_payment_verification(
    reference='INV-12345-001',
    paystack_response_data=response_data
)
```

## Webhook Handling

### Webhook Endpoint

The webhook endpoint is configured at `/finance/webhooks/paystack/` and handles:

- **charge.success**: Successful payment
- **charge.failed**: Failed payment
- **charge.abandoned**: Abandoned payment
- **customer.created**: New customer created
- **invoice.payment_failed**: Invoice payment failed

### Webhook Processing

```python
from apps.finance.services import get_webhook_service

webhook_service = get_webhook_service()

# Process webhook event
webhook_event, success = webhook_service.process_webhook_event(
    event_type='charge.success',
    event_data=event_data,
    event_reference='INV-12345-001',
    event_timestamp=timezone.now()
)
```

### Security

Webhook requests are secured with signature verification:

```python
import hashlib
import hmac

def verify_webhook_signature(request_body, signature):
    webhook_secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')
    computed_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request_body,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(signature, computed_signature)
```

## Views and Templates

### Payment Gateway View

- **URL**: `/finance/invoices/<uuid:invoice_pk>/gateway/`
- **Purpose**: Redirect students/parents to Paystack payment page
- **Features**: Payment amount validation, metadata tracking

### Payment Callback View

- **URL**: `/finance/payments/callback/<str:reference>/`
- **Purpose**: Handle payment completion and status updates
- **Features**: Payment verification, status updates, user notifications

### Student Payment Views

- **Payment List**: `/finance/student/payments/` - View payment history
- **Pay Invoice**: `/finance/student/invoices/<uuid:invoice_pk>/pay/` - Pay specific invoice

## Templates

### Payment Gateway Template

Located at `templates/finance/payments/payment_gateway.html`:

- Invoice details display
- Payment method selection
- Amount validation
- Payment initiation

### Student Payment Templates

- `templates/finance/student/payment_list.html` - Payment history
- `templates/finance/student/pay_invoice.html` - Invoice payment
- `templates/finance/payments/payment_success.html` - Success confirmation
- `templates/finance/payments/payment_failed.html` - Failure notification

## API Endpoints

### Payment APIs

- `POST /finance/api/invoices/generate/` - Generate invoices for students
- `GET /finance/api/students/<uuid:student_id>/outstanding-fees/` - Get outstanding fees
- `GET /finance/api/payments/<uuid:payment_id>/status/` - Get payment status

### Webhook Endpoint

- `POST /finance/webhooks/paystack/` - Process Paystack webhooks (CSRF exempt)

## Error Handling

### Common Errors

1. **Invalid API Keys**: Check Paystack credentials in settings
2. **Webhook Signature Mismatch**: Verify webhook secret configuration
3. **Payment Verification Failed**: Check network connectivity and API limits
4. **Insufficient Funds**: Handle gracefully in frontend

### Logging

All payment operations are logged for debugging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Payment initialized: {reference}")
logger.error(f"Payment failed: {error_message}")
logger.warning(f"Webhook processing error: {error_details}")
```

## Testing

### Test Environment

Use Paystack test mode for development:

```python
PAYSTACK_TEST_MODE = True
```

### Test Cards

Paystack provides test card numbers:

- **Visa**: 4081259999999996
- **MasterCard**: 5060666666666666
- **Verve**: 4081259999999996

### Test Scenarios

1. **Successful Payment**: Use valid test card
2. **Failed Payment**: Use invalid card (5060666666666666)
3. **Abandoned Payment**: Cancel payment on Paystack page
4. **Webhook Processing**: Test webhook endpoint with sample payloads

## Security Considerations

### Data Protection

- Never log sensitive card information
- Store only necessary payment metadata
- Use HTTPS for all payment-related endpoints
- Validate all webhook signatures

### Access Control

- Restrict payment creation to authorized users
- Validate invoice ownership before payment
- Implement rate limiting for payment attempts
- Audit all payment modifications

## Deployment

### Production Checklist

1. **Environment Variables**: Set all Paystack credentials
2. **Webhook URL**: Configure webhook URL in Paystack dashboard
3. **SSL Certificate**: Ensure HTTPS is enabled
4. **Database**: Run migrations for new models
5. **Logging**: Configure production logging

### Paystack Dashboard Setup

1. **API Keys**: Generate and configure API keys
2. **Webhook**: Set webhook URL to `/finance/webhooks/paystack/`
3. **Webhook Secret**: Configure webhook secret
4. **Test Mode**: Disable test mode for production

## Troubleshooting

### Common Issues

1. **Payments Not Processing**:
   - Check API key configuration
   - Verify webhook endpoint accessibility
   - Check network connectivity

2. **Webhook Not Received**:
   - Verify webhook URL in Paystack dashboard
   - Check firewall settings
   - Ensure endpoint is accessible from internet

3. **Payment Status Not Updated**:
   - Check webhook processing logs
   - Verify signature verification
   - Check database connectivity

### Debug Mode

Enable debug logging for payment operations:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.finance': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Future Enhancements

### Planned Features

1. **Recurring Payments**: Support for subscription-based payments
2. **Multiple Payment Methods**: Support for additional payment providers
3. **Payment Scheduling**: Schedule future payments
4. **Payment Reminders**: Automated payment reminder system
5. **Advanced Reporting**: Detailed payment analytics and reports

### Integration Points

- **Accounting Software**: Integration with accounting systems
- **SMS Notifications**: Payment confirmation via SMS
- **Email Templates**: Customizable payment notification emails
- **Mobile App**: Mobile payment interface

## Support

For issues related to Paystack integration:

1. **Check Logs**: Review application logs for error details
2. **Paystack Documentation**: Refer to [Paystack API Documentation](https://paystack.com/docs)
3. **Support Channels**: Contact Paystack support for API issues
4. **Community**: Check Django and Paystack community forums

## Version History

- **v1.0**: Initial Paystack integration
  - Basic payment processing
  - Webhook handling
  - Student payment interface
  - Multi-tenant support