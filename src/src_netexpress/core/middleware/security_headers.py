"""
Middleware d'en-têtes de sécurité HTTP.

Ajoute une Content-Security-Policy et une Permissions-Policy à toutes les
réponses. Ces en-têtes complètent ceux déjà fournis par
``django.middleware.security.SecurityMiddleware`` (HSTS, nosniff, etc.) et
sont évalués par des outils comme Mozilla Observatory / SecurityHeaders.

La politique est volontairement pragmatique :
- ``script-src`` et ``style-src`` autorisent ``'unsafe-inline'`` car le projet
  s'appuie encore sur des scripts/styles inline (gestionnaires onclick,
  JSON-LD, Jazzmin, TinyMCE). Le durcissement (nonces) pourra être fait
  ultérieurement sans changer cette structure.
- ``frame-ancestors 'none'`` empêche le clickjacking (complète X-Frame-Options).
- ``object-src 'none'`` et ``base-uri 'self'`` ferment des vecteurs courants.

La valeur peut être surchargée via ``settings.CONTENT_SECURITY_POLICY`` et
``settings.PERMISSIONS_POLICY``.
"""

from __future__ import annotations

from django.conf import settings


DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https://challenges.cloudflare.com; "
    "frame-src https://challenges.cloudflare.com; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'"
)

DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"


class SecurityHeadersMiddleware:
    """Ajoute CSP et Permissions-Policy sans écraser des valeurs déjà posées."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = getattr(settings, "CONTENT_SECURITY_POLICY", DEFAULT_CSP)
        self.permissions_policy = getattr(
            settings, "PERMISSIONS_POLICY", DEFAULT_PERMISSIONS_POLICY
        )

    def __call__(self, request):
        response = self.get_response(request)

        if self.csp and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = self.csp

        if self.permissions_policy and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = self.permissions_policy

        return response
