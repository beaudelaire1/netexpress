from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from .models import Invoice, InvoiceItem


logger = logging.getLogger(__name__)


def _copy_quote_items_if_needed(invoice: Invoice) -> None:
    """Copie les lignes du devis quand une facture a été créée directement.

    Le portail admin utilisait historiquement ``ModelForm.save()`` et créait
    donc une facture liée au devis sans recopier ses lignes. Le service
    ``create_invoice_from_quote`` continue de fonctionner normalement : dans
    ce cas les lignes existent déjà et cette fonction ne fait rien.
    """
    if not invoice.quote_id or invoice.invoice_items.exists():
        return

    quote_items = list(invoice.quote.quote_items.select_related("service").all())
    if not quote_items:
        return

    InvoiceItem.objects.bulk_create(
        [
            InvoiceItem(
                invoice=invoice,
                description=(
                    item.description
                    or (item.service.title if item.service else "")
                    or "Prestation"
                ),
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
            )
            for item in quote_items
        ]
    )


def _send_created_notification(invoice: Invoice) -> None:
    """Envoie la notification interne une fois la facture finalisée."""
    recipient = getattr(
        settings,
        "TASK_NOTIFICATION_EMAIL",
        getattr(settings, "DEFAULT_FROM_EMAIL", ""),
    )
    if not recipient:
        return

    num = invoice.number or invoice.pk
    subject = f"[Nettoyage Express] Facture #{num} générée"
    html_body = render_to_string(
        "emails/notification_generic.html",
        {
            "headline": "Nouvelle facture générée",
            "intro": "Une nouvelle facture a été créée dans le système.",
            "rows": [
                {"label": "Numéro", "value": str(num)},
                {"label": "Total TTC", "value": f"{invoice.total_ttc} €"},
            ],
        },
    )

    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "noreply@nettoyageexpresse.fr",
    )
    email = EmailMessage(
        subject=subject,
        body=html_body,
        from_email=from_email,
        to=[recipient],
    )
    email.content_subtype = "html"
    email.send(fail_silently=True)


def _finalize_created_invoice(invoice_id: int) -> None:
    """Finalise une facture après validation de sa transaction de création."""
    try:
        invoice = Invoice.objects.select_related("quote", "quote__client").get(pk=invoice_id)

        _copy_quote_items_if_needed(invoice)

        if not invoice.invoice_items.exists():
            logger.warning(
                "Facture %s créée sans ligne : génération PDF différée.",
                invoice.pk,
            )
            return

        # Les lignes doivent être figées avant le calcul et la génération du PDF.
        invoice.compute_totals()
        invoice.refresh_from_db()

        # Une facture créée depuis un devis accepté clôt le parcours de devis,
        # même lorsque la création provient directement du ModelForm admin.
        quote = invoice.quote
        if quote and quote.status == quote.QuoteStatus.ACCEPTED:
            quote.status = quote.QuoteStatus.INVOICED
            quote.save(update_fields=["status"])

        # Le PDF est une sortie de la facture finalisée, pas un effet de bord de
        # Invoice.save(). Cela évite la récursion provoquée par FileField.save().
        if not invoice.pdf:
            invoice.generate_pdf(attach=True)
            invoice.refresh_from_db(fields=["pdf", "total_ht", "tva", "total_ttc", "amount"])

        _send_created_notification(invoice)
    except Invoice.DoesNotExist:
        return
    except Exception:
        logger.exception(
            "Échec de finalisation automatique de la facture %s",
            invoice_id,
        )


@receiver(post_save, sender=Invoice)
def finalize_invoice_created(sender, instance: Invoice, created: bool, raw: bool = False, **kwargs) -> None:
    """Finalise automatiquement toute nouvelle facture après son commit DB."""
    if raw or not created or not instance.pk:
        return

    invoice_id = instance.pk
    transaction.on_commit(lambda: _finalize_created_invoice(invoice_id))
