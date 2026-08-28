from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from core.services.document_generator import DocumentGenerator
from devis.models import Client, Quote, QuoteItem
from factures.models import Invoice, InvoiceItem


pytestmark = pytest.mark.django_db


def make_quote() -> Quote:
    client = Client.objects.create(
        full_name="Client Test",
        company="Entreprise Test",
        email="client@example.com",
        phone="0694000000",
        address_line="1 rue de Test",
        zip_code="97300",
        city="Cayenne",
    )
    return Quote.objects.create(client=client)


def test_document_generator_exposes_line_tax_and_ttc():
    quote = make_quote()
    QuoteItem.objects.create(
        quote=quote,
        description="Nettoyage",
        quantity=Decimal("2.00"),
        unit_price=Decimal("50.00"),
        tax_rate=Decimal("8.50"),
    )
    quote.compute_totals()

    context = DocumentGenerator._build_context(quote, "DEV")

    assert context["quote"] == quote
    assert context["client_company"] == "Entreprise Test"
    assert context["client_address"] == "1 rue de Test\n97300 Cayenne"
    assert len(context["rows"]) == 1
    row = context["rows"][0]
    assert row["tax_rate"] == Decimal("8.50")
    assert row["total_ht"] == Decimal("100.00")
    assert row["total_tva"] == Decimal("8.50")
    assert row["total_ttc"] == Decimal("108.50")


def test_invoice_context_uses_same_document_contract():
    quote = make_quote()
    invoice = Invoice.objects.create(quote=quote)
    InvoiceItem.objects.create(
        invoice=invoice,
        description="Entretien",
        quantity=Decimal("3.00"),
        unit_price=Decimal("20.00"),
        tax_rate=Decimal("0.00"),
    )
    invoice.compute_totals()

    context = DocumentGenerator._build_context(invoice, "FAC")

    assert context["invoice"] == invoice
    assert context["client_name"] == "Client Test"
    assert context["rows"][0]["total_ht"] == Decimal("60.00")
    assert context["rows"][0]["total_ttc"] == Decimal("60.00")


def test_pdf_design_uses_netexpress_palette_and_no_tus_tokens():
    base_dir = Path(settings.BASE_DIR)
    css = (base_dir / "static" / "css" / "pdf.css").read_text(encoding="utf-8")
    quote_template = (base_dir / "templates" / "pdf" / "quote_premium.html").read_text(encoding="utf-8")
    invoice_template = (base_dir / "templates" / "pdf" / "invoice_premium.html").read_text(encoding="utf-8")

    assert "#104130" in css
    assert "#2d8a5e" in css.lower()
    assert "--tus" not in css.lower()
    assert "#0b2dff" not in css.lower()

    for template in (quote_template, invoice_template):
        assert 'class="document-header"' in template
        assert 'class="items-table"' in template
        assert "Total TTC" in template or "Net à payer" in template
        assert "row.tax_rate" in template
        assert "row.total_ttc" in template


def test_quote_editor_contains_empty_form_for_first_line(client):
    quote = make_quote()
    user = User.objects.create_superuser(
        username="document-admin",
        email="admin@example.com",
        password="test-password",
    )
    client.force_login(user)

    response = client.get(reverse("devis:admin_quote_edit", args=[quote.pk]))

    assert response.status_code == 200
    assert "formset" in response.context
    assert response.context["formset"].total_form_count() == 0
    content = response.content.decode("utf-8")
    assert 'id="quote-item-empty-form"' in content
    assert "TOTAL_FORMS" in content
    assert "+ Ajouter une prestation" in content


def test_quote_editor_can_create_first_line_and_recalculate(client):
    quote = make_quote()
    user = User.objects.create_superuser(
        username="quote-editor-admin",
        email="editor@example.com",
        password="test-password",
    )
    client.force_login(user)

    get_response = client.get(reverse("devis:admin_quote_edit", args=[quote.pk]))
    prefix = get_response.context["formset"].prefix

    payload = {
        "client": str(quote.client_id),
        "quote_request": "",
        "status": Quote.QuoteStatus.DRAFT,
        "issue_date": quote.issue_date.isoformat(),
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else "",
        "message": "",
        "notes": "",
        "_action": "save",
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-service": "",
        f"{prefix}-0-description": "Prestation créée depuis l'éditeur",
        f"{prefix}-0-quantity": "2.00",
        f"{prefix}-0-unit_price": "45.00",
        f"{prefix}-0-tax_rate": "0.00",
    }

    response = client.post(reverse("devis:admin_quote_edit", args=[quote.pk]), payload)

    assert response.status_code == 302
    quote.refresh_from_db()
    assert quote.quote_items.count() == 1
    assert quote.total_ht == Decimal("90.00")
    assert quote.tva == Decimal("0.00")
    assert quote.total_ttc == Decimal("90.00")


def test_quote_pdf_responses_are_not_publicly_cacheable(client):
    quote = make_quote()
    user = User.objects.create_superuser(
        username="pdf-admin",
        email="pdf-admin@example.com",
        password="test-password",
    )
    client.force_login(user)

    # Le moteur WeasyPrint est volontairement simulé ici : ce test porte sur
    # la politique HTTP, pas sur les bibliothèques système du runner.
    original = Quote.generate_pdf
    Quote.generate_pdf = lambda self, attach=False: b"%PDF-test"
    try:
        response = client.get(reverse("devis:download", args=[quote.pk]))
    finally:
        Quote.generate_pdf = original

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
