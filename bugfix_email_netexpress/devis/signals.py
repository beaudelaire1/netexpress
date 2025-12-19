"""Signals for the ``devis`` app.

Audit decisions (18 Dec 2025):
- WeasyPrint is the only PDF renderer.
- No automatic quote emailing on creation (manual, explicit action only).

We use signals only for low-risk consistency tasks.
"""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import QuoteItem


@receiver(post_save, sender=QuoteItem)
def _quoteitem_post_save(sender, instance: QuoteItem, **kwargs):
    """Recompute quote totals whenever a line is created/updated."""
    quote = getattr(instance, "quote", None)
    if quote is None:
        return
    try:
        quote.compute_totals()
    except Exception:
        # Never block saves because of totals recomputation.
        pass


@receiver(post_delete, sender=QuoteItem)
def _quoteitem_post_delete(sender, instance: QuoteItem, **kwargs):
    """Recompute quote totals whenever a line is deleted."""
    quote = getattr(instance, "quote", None)
    if quote is None:
        return
    try:
        quote.compute_totals()
    except Exception:
        pass
