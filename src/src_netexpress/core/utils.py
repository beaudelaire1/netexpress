"""Utilitaires partagés du projet NetExpress."""

from decimal import Decimal


def num2words_fr(v: Decimal) -> str:
    """Convertit un montant en toutes lettres (français).

    Utilise num2words si disponible, sinon repli simple.
    """
    try:
        from num2words import num2words
        return num2words(v, lang='fr')
    except Exception:
        return str(v).replace(".", ",")


def sanitize_html(html: str) -> str:
    """Nettoie le HTML utilisateur via bleach (TinyMCE, messages, etc.)."""
    try:
        import bleach
        from django.conf import settings
        return bleach.clean(
            html,
            tags=getattr(settings, 'BLEACH_ALLOWED_TAGS', []),
            attributes=getattr(settings, 'BLEACH_ALLOWED_ATTRIBUTES', {}),
            strip=getattr(settings, 'BLEACH_STRIP_TAGS', True),
        )
    except ImportError:
        return html
