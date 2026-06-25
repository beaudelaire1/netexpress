"""En-têtes de sécurité applicatifs complémentaires.

Django couvre déjà HSTS, `X-Content-Type-Options`, `X-Frame-Options` et
`Referrer-Policy` via ``SecurityMiddleware`` / réglages. Ce middleware ajoute
les en-têtes manquants relevés à l'audit avant publication :

* ``Content-Security-Policy`` — défense en profondeur contre l'injection de
  scripts/ressources et le clickjacking (``frame-ancestors``) ;
* ``Permissions-Policy`` — neutralise des API navigateur non utilisées.

La politique est volontairement une **base pragmatique** : elle autorise les
origines réellement employées par le site (Google Fonts, Font Awesome via
cdnjs, Cloudflare Turnstile, Cloudinary) et conserve ``'unsafe-inline'`` /
``'unsafe-eval'`` pour rester compatible avec l'admin Jazzmin et TinyMCE. Elle
peut être durcie ensuite (nonces) sans changer ce point d'ancrage.

Surcharge possible via les réglages ``CONTENT_SECURITY_POLICY`` et
``PERMISSIONS_POLICY`` ; définir une valeur vide désactive l'en-tête concerné.
"""

from __future__ import annotations

from django.conf import settings

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: "
    "https://challenges.cloudflare.com https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
    "https://cdnjs.cloudflare.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https://challenges.cloudflare.com; "
    "frame-src https://challenges.cloudflare.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "form-action 'self'"
)

DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=(), payment=()"


class SecurityHeadersMiddleware:
    """Ajoute CSP et Permissions-Policy à chaque réponse."""

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
