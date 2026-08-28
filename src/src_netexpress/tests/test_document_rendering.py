"""Tests de non-régression de la chaîne documentaire NetExpress."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

from devis.forms import DevisForm
from devis.models import Client, Quote, QuoteItem
from factures.models import Invoice, InvoiceItem


pytestmark = pytest.mark.django_db


@pytest.fixture
def quote_with_item():
    client = Client.objects.create(
        full_name="Client Test",
        company="Entreprise Test",
        email="client@example.com",
        phone="0694000000",
        address_line="1 rue Exemple",
        city="Cayenne",
        zip_code="97300",
    )
    quote = Quote.objects.create(client=client)
    QuoteItem.objects.create(
        quote=quote,
        description="Nettoyage professionnel",
        quantity=Decimal("2.00"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("20.00"),
    )
    quote.compute_totals()
    return quote


def test_quote_template_uses_shared_document_structure(settings, quote_with_item):
    html = render_to_string(
        "pdf/quote.html",
        {
            "quote": quote_with_item,
            "branding": settings.INVOICE_BRANDING,
        },
    )

    assert "document-header" in html
    assert "DEVIS" in html
    assert quote_with_item.number in html
    assert "Net à payer" not in html
    assert "Trait D'Union" not in html
    assert "0B2DFF" not in html


def test_document_styles_keep_netexpress_palette(settings):
    css = (settings.BASE_DIR / "static" / "css" / "pdf.css").read_text(encoding="utf-8").lower()

    assert "#0b5d46" in css
    assert "#1c7c54" in css
    assert "#0b2dff" not in css


def test_invoice_service_renders_line_level_tax(monkeypatch, quote_with_item):
    from core.services import pdf_service

    invoice = Invoice.objects.create(quote=quote_with_item)
    InvoiceItem.objects.create(
        invoice=invoice,
        description="Nettoyage professionnel",
        quantity=2,
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("20.00"),
    )
    invoice.compute_totals()

    captured = {}

    class FakeHTML:
        def __init__(self, *, string, base_url):
            captured["html"] = string
            captured["base_url"] = base_url

        def write_pdf(self, *, stylesheets):
            captured["stylesheets"] = stylesheets
            return b"%PDF-test"

    class FakeCSS:
        def __init__(self, *, filename):
            self.filename = filename

    monkeypatch.setattr(pdf_service, "HTML", FakeHTML)
    monkeypatch.setattr(pdf_service, "CSS", FakeCSS)

    result = pdf_service.InvoicePdfService().generate(invoice)

    assert result.content == b"%PDF-test"
    assert result.filename == f"{invoice.number}.pdf"
    assert "FACTURE" in captured["html"]
    assert invoice.number in captured["html"]
    assert "20" in captured["html"]
    assert "Total TTC" in captured["html"] or "Net à payer" in captured["html"]


def test_public_quote_form_uses_weasyprint_renderer(monkeypatch, settings, tmp_path):
    from devis import forms as devis_forms

    settings.MEDIA_ROOT = tmp_path
    calls = []

    def fake_render_quote_pdf(quote):
        calls.append(quote.pk)
        return SimpleNamespace(
            filename=f"{quote.number}.pdf",
            content=b"%PDF-test",
            mimetype="application/pdf",
        )

    def fail_if_legacy_renderer_is_used(*args, **kwargs):
        raise AssertionError("L'ancien renderer ReportLab ne doit pas être appelé")

    monkeypatch.setattr(devis_forms, "render_quote_pdf", fake_render_quote_pdf)
    monkeypatch.setattr(Quote, "generate_pdf", fail_if_legacy_renderer_is_used)

    form = DevisForm(
        data={
            "full_name": "Client Public",
            "email": "public@example.com",
            "phone": "0694111111",
            "city": "Matoury",
            "zip_code": "97351",
            "address": "2 rue Exemple",
            "service": "",
            "message": "Demande de prestation",
            "service_type": "nettoyage",
            "urgency": "standard",
        }
    )

    assert form.is_valid(), form.errors
    quote = form.save()

    assert calls == [quote.pk]
    assert quote.pdf.name.endswith(f"{quote.number}.pdf")
