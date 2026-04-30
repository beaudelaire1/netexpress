"""
Cloudflare Turnstile integration for form protection.

Usage:
  1. Add TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY to settings/environment
  2. In templates: {% include "core/partials/turnstile_widget.html" %}
  3. In views: from core.turnstile import verify_turnstile
     if not verify_turnstile(request): messages.error(...)
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def get_site_key():
    """Return the Turnstile site key (public)."""
    return getattr(settings, 'TURNSTILE_SITE_KEY', '')


def is_enabled():
    """Return True if Turnstile is configured."""
    return bool(get_site_key() and getattr(settings, 'TURNSTILE_SECRET_KEY', ''))


def verify_turnstile(request) -> bool:
    """Verify the Turnstile response token from a POST request.
    
    Returns True if verification passes or if Turnstile is not configured.
    """
    secret_key = getattr(settings, 'TURNSTILE_SECRET_KEY', '')
    if not secret_key:
        return True  # Skip if not configured

    token = request.POST.get('cf-turnstile-response', '')
    if not token:
        logger.warning("[TURNSTILE] No token in POST data")
        return False

    try:
        response = requests.post(TURNSTILE_VERIFY_URL, data={
            'secret': secret_key,
            'response': token,
            'remoteip': _get_client_ip(request),
        }, timeout=5)
        result = response.json()
        success = result.get('success', False)
        if not success:
            logger.warning(f"[TURNSTILE] Verification failed: {result.get('error-codes', [])}")
        return success
    except Exception as e:
        logger.error(f"[TURNSTILE] Error during verification: {e}")
        return True  # Fail open to not block users if Cloudflare is down


def _get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
