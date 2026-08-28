from decimal import Decimal

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

from core.management.commands import deploy_migrate
from core.services.document_generator import DocumentGenerator
from devis.models import Client, Quote
from factures.models import Invoice, InvoiceItem
from netexpress.settings.runtime_validation import normalize_bic, normalize_iban


pytestmark = pytest.mark.django_db


VALID_IBAN = "GB82 WEST 1234 5698 7654 32"


def test_iban_is_checksum_validated_and_normalized():
    assert normalize_iban("gb82west12345698765432") == VALID_IBAN

    with pytest.raises(ImproperlyConfigured, match="clé IBAN invalide"):
        normalize_iban("GB82 WEST 1234 5698 7654 31")

    with pytest.raises(ImproperlyConfigured, match="IBAN valide"):
        normalize_iban("not-an-iban")


def test_bic_is_optional_but_validated_when_present():
    assert normalize_bic("") == ""
    assert normalize_bic("deut de ff") == "DEUTDEFF"
    assert normalize_bic("DEUTDEFF500") == "DEUTDEFF500"

    with pytest.raises(ImproperlyConfigured, match="BIC"):
        normalize_bic("invalid")


def test_invoice_template_renders_complete_bank_details(settings):
    client = Client.objects.create(
        full_name="Client Test",
        company="Entreprise Test",
        email="client@example.test",
        phone="0694000000",
    )
    quote = Quote.objects.create(client=client, status=Quote.QuoteStatus.ACCEPTED)
    invoice = Invoice.objects.create(quote=quote)
    InvoiceItem.objects.create(
        invoice=invoice,
        description="Prestation",
        quantity=Decimal("1.00"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("0.00"),
    )
    invoice.compute_totals()

    settings.INVOICE_BRANDING = {
        "name": "Nettoyage Express",
        "address_lines": ["Adresse test"],
        "siret": "000 000 000 00000",
        "bank_account_name": "Titulaire de démonstration",
        "iban": VALID_IBAN,
        "bic": "DEUTDEFF",
        "payment_terms": "Paiement à réception",
    }

    html = render_to_string(
        "pdf/invoice_premium.html",
        DocumentGenerator._build_context(invoice, "FAC"),
    )

    assert "Coordonnées bancaires" in html
    assert "Titulaire" in html
    assert "Titulaire de démonstration" in html
    assert VALID_IBAN in html
    assert "DEUTDEFF" in html


def test_deploy_migrate_serializes_with_postgresql_advisory_lock(monkeypatch):
    statements = []
    commands = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            statements.append((sql, params))

    class FakeConnection:
        vendor = "postgresql"

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(deploy_migrate, "connection", FakeConnection())
    monkeypatch.setattr(
        deploy_migrate,
        "call_command",
        lambda *args, **kwargs: commands.append((args, kwargs)),
    )

    deploy_migrate.Command().handle(verbosity=0)

    assert statements == [
        ("SELECT pg_advisory_lock(%s)", [deploy_migrate.MIGRATION_LOCK_ID]),
        ("SELECT pg_advisory_unlock(%s)", [deploy_migrate.MIGRATION_LOCK_ID]),
    ]
    assert commands == [
        (("migrate",), {"interactive": False, "verbosity": 0}),
    ]


def test_deploy_migrate_refuses_non_postgresql(monkeypatch):
    class FakeConnection:
        vendor = "sqlite"

    monkeypatch.setattr(deploy_migrate, "connection", FakeConnection())

    with pytest.raises(deploy_migrate.CommandError, match="PostgreSQL"):
        deploy_migrate.Command().handle(verbosity=0)
