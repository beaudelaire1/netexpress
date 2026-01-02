# Integration of Django Email Templates with Brevo API

## Overview

This document describes the integration of existing Django email templates with the Brevo (ex-Sendinblue) API for sending transactional emails. Previously, emails were being sent via Brevo but without using the professionally designed HTML templates stored in `src/src_netexpress/templates/emails/`.

## Changes Summary

### 1. New Service: `BrevoEmailService`

**File:** `src/src_netexpress/core/services/brevo_email_service.py`

A new service class that wraps the Brevo API and provides Django template integration:

- **`send()`** - Direct email sending via Brevo API with support for HTML content and attachments
- **`send_with_django_template()`** - Renders Django templates and sends via Brevo API

**Features:**
- Automatic template rendering with `render_to_string()`
- Support for PDF attachments (invoices, quotes)
- Comprehensive error handling and logging
- Graceful fallback when API key is not configured

### 2. Updated Services

#### `core/services/email_service.py` (EmailService/PremiumEmailService)

- **`send_invoice_notification()`** - Now uses `emails/invoice_notification.html` template with Brevo
  - Generates PDF invoice on-the-fly
  - Sends to all client email addresses
  - Falls back to Django EmailMultiAlternatives if Brevo fails

- **`send_quote_pdf_to_client()`** - New method using `emails/new_quote_pdf.html` template
  - Generates PDF quote on-the-fly
  - Sends to client email
  - Falls back to Django EmailMultiAlternatives if Brevo fails

#### `messaging/services.py`

- **`send_contact_notification()`** - Now uses `emails/new_contact_admin.html` template with Brevo
  - Professional HTML design for contact form notifications
  - Maintains fallback to EmailNotificationService

- **`send_quote_notification()`** - Now uses `emails/new_quote.html` template with Brevo
  - Professional HTML design for quote notifications
  - Maintains fallback to EmailNotificationService

- **`_prepare_pdf_attachment()`** - New helper function
  - Extracts PDF attachment preparation logic
  - Reusable across multiple functions

#### `tasks/services.py` (EmailNotificationService)

- **`send_with_template()`** - New class method for Django template support
  - Enables task notifications to use professional templates
  - Prefers Brevo API when configured
  - Falls back to Django email

#### `core/services/notification_service.py`

- **`send_email_notification()`** - Updated to prefer Brevo when available
  - Checks for Brevo backend configuration
  - Uses `BrevoEmailService.send_with_django_template()` when possible
  - Maintains backward compatibility with all existing notifications

### 3. Email Template Mapping

| Service Function | Template Used |
|------------------|---------------|
| `send_invoice_notification()` | `emails/invoice_notification.html` |
| `send_quote_pdf_to_client()` | `emails/new_quote_pdf.html` |
| `send_contact_notification()` | `emails/new_contact_admin.html` |
| `send_quote_notification()` | `emails/new_quote.html` |
| Task assignment notifications | `emails/task_assignment.html` |
| Task completion notifications | `emails/task_completion.html` |
| Generic notifications | `emails/notification_generic.html` |
| Quote validation | `emails/quote_validation.html` |

### 4. Template Context Variables

All templates receive appropriate context variables:

**Invoice Notification:**
- `invoice` - Invoice object
- `branding` - Branding settings (name, email, colors, logo)
- `client_name` - Client's full name

**Quote Notification:**
- `quote` - Quote object
- `client` - Client object
- `branding` - Branding settings

**Contact Notification:**
- `msg` - Contact message object
- `branding` - Branding settings

**Task Notifications:**
- `task` - Task object
- `worker` or `completed_by` - User object
- `branding` - Branding settings
- `company_name` - Company name from settings

## Configuration

### Settings Required

```python
# Enable Brevo backend
EMAIL_BACKEND = 'core.backends.brevo_backend.BrevoEmailBackend'

# Brevo API key
BREVO_API_KEY = 'xkeysib-...'

# Email sender configuration
DEFAULT_FROM_EMAIL = 'noreply@example.com'
DEFAULT_FROM_NAME = 'Company Name'

# Branding for templates
INVOICE_BRANDING = {
    'name': 'Company Name',
    'email': 'contact@example.com',
    'site_url': 'https://example.com',
    'logo_url': 'https://example.com/logo.png',
    # ... other branding settings
}
```

### Fallback Behavior

The integration maintains graceful fallback at multiple levels:

1. **No Brevo API key** → Service initializes but doesn't use Brevo
2. **Brevo API error** → Falls back to Django EmailMultiAlternatives
3. **Template rendering error** → Logged and returns False
4. **Backend not Brevo** → Uses existing email sending logic

## Testing

### Unit Tests

**File:** `src/src_netexpress/tests/test_brevo_email_service.py`

Comprehensive test coverage including:
- Service initialization with and without API key
- Email sending (simple, with attachments, with templates)
- Error handling (API errors, template errors)
- Mock-based tests (no actual API calls)

### Running Tests

```bash
cd src/src_netexpress
python manage.py test tests.test_brevo_email_service
```

## Benefits

1. ✅ **Professional HTML Design** - All emails now use the branded templates with consistent styling
2. ✅ **Branding Consistency** - Company colors (#104130), logo, and styling applied to all emails
3. ✅ **Dynamic Content** - Invoice numbers, amounts, client names properly displayed
4. ✅ **PDF Attachments** - Invoices and quotes attached correctly
5. ✅ **No Breaking Changes** - All existing code continues to work
6. ✅ **Graceful Fallback** - Multiple levels of fallback ensure emails are always sent
7. ✅ **Maintainability** - Templates can be updated independently of code
8. ✅ **Security** - No vulnerabilities found by CodeQL analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Code                        │
│  (Views, Signals, Admin Actions)                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Email Service Layer                       │
│  • EmailService (core/services/email_service.py)           │
│  • messaging/services.py                                    │
│  • tasks/services.py (EmailNotificationService)             │
│  • notification_service.py                                  │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ↓                          ↓
  ┌────────────────────────┐   ┌────────────────────────┐
  │  BrevoEmailService     │   │ Django Email           │
  │  (Brevo API)           │   │ (Fallback)             │
  └────────────┬───────────┘   └────────────────────────┘
               │
               ↓
  ┌────────────────────────┐
  │  Django Templates      │
  │  (emails/*.html)       │
  └────────────────────────┘
```

## Future Improvements

Possible enhancements for future iterations:

1. **Template Caching** - Cache rendered templates for better performance
2. **Email Analytics** - Track open rates and click-through rates via Brevo
3. **A/B Testing** - Test different email designs
4. **Scheduled Sending** - Queue emails for optimal delivery times
5. **Localization** - Multi-language email templates

## Troubleshooting

### Emails Not Using Templates

1. Check `EMAIL_BACKEND` setting points to Brevo backend
2. Verify `BREVO_API_KEY` is configured and valid
3. Check logs for template rendering errors
4. Verify templates exist in `templates/emails/` directory

### Attachments Not Working

1. Verify PDF generation is working (check DocumentGenerator)
2. Check file permissions on generated PDFs
3. Review Brevo API logs for attachment upload errors
4. Verify base64 encoding is working correctly

### Branding Not Appearing

1. Check `INVOICE_BRANDING` setting is properly configured
2. Verify template is using correct context variable names
3. Ensure `branding` is passed in template context

## Migration Notes

**No database migrations required** - This is purely a code-level change.

All existing functionality continues to work. The integration adds Brevo template support while maintaining complete backward compatibility.

## Support

For issues or questions:
1. Check logs in Django admin or console
2. Verify Brevo API key status in Brevo dashboard
3. Test email sending with Django management command
4. Review template rendering in development mode
