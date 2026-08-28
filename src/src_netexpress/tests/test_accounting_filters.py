from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.access import confirm_email
from accounts.models import Profile
from accounting.filters import SalesFilterForm, SupplierFilterForm
from accounting.models import (
    AccountingDocument,
    AccountingExchange,
    AccountingExchangeReadState,
    InvoiceReview,
    SupplierInvoice,
)
from accounting.services import invoice_fingerprint
from devis.models import Client as Customer, Quote, QuoteItem
from devis.services import create_invoice_from_quote

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role=Profile.ROLE_ACCOUNTANT, username=None):
    username = username or f"filter-{role}-{User.objects.count()}"
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="LongSecurePassword854!",
    )
    user.profile.role = role
    user.profile.save(update_fields=["role"])
    confirm_email(user)
    user.refresh_from_db()
    return user


def make_invoice(*, client_name, total_unit, status="sent", issue_date=date(2026, 8, 15)):
    customer = Customer.objects.create(
        full_name=client_name,
        email=f"{client_name.lower().replace(' ', '.')}@example.test",
    )
    quote = Quote.objects.create(client=customer, status="accepted")
    QuoteItem.objects.create(
        quote=quote,
        description=f"Prestation {client_name}",
        quantity=Decimal("1.00"),
        unit_price=Decimal(total_unit),
        tax_rate=Decimal("0.00"),
    )
    invoice = create_invoice_from_quote(quote).invoice
    invoice.issue_date = issue_date
    invoice.status = status
    invoice.save(update_fields=["issue_date", "status"])
    return invoice


def pdf_upload(name):
    return SimpleUploadedFile(name, b"%PDF-1.4\nfilter-test\n%%EOF", content_type="application/pdf")


def test_sales_filter_is_métier_oriented_and_excludes_draft_choice(client):
    accountant = make_user()
    reviewed = make_invoice(client_name="Alpha SARL", total_unit="120.00")
    linked = make_invoice(client_name="Beta SAS", total_unit="280.00", status="paid")
    InvoiceReview.objects.create(
        invoice=reviewed,
        fingerprint=invoice_fingerprint(reviewed),
        reviewed_by=accountant,
    )
    AccountingExchange.objects.create(
        subject="Question Beta",
        kind=AccountingExchange.Kind.QUESTION,
        status=AccountingExchange.Status.WAITING_ACCOUNTANT,
        created_by=accountant,
        invoice=linked,
    )
    client.force_login(accountant)

    response = client.get(reverse("accounting:sales"), {"review": "reviewed", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert response.status_code == 200
    assert reviewed.number in html
    assert linked.number not in html
    assert "Statut facture" in html and "TTC minimum" in html and "Avec échange ouvert" in html

    response = client.get(reverse("accounting:sales"), {"exchange": "open", "amount_min": "200", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert linked.number in html
    assert reviewed.number not in html

    choices = dict(SalesFilterForm().fields["status"].choices)
    assert "draft" not in choices
    assert "demo" not in choices


def test_supplier_filters_keep_drafts_private_from_accountant(client):
    admin = make_user(Profile.ROLE_ADMIN_BUSINESS, "filter-admin")
    complete = SupplierInvoice.objects.create(
        supplier_name="Fournisseur complet",
        supplier_key="fournisseur complet",
        reference="FC-001",
        issue_date=date(2026, 8, 10),
        due_date=date(2026, 8, 20),
        total_ttc=Decimal("180.00"),
        vat_amount=Decimal("30.00"),
        category=SupplierInvoice.Category.SUPPLIES,
        file=pdf_upload("complete.pdf"),
        file_sha256="a" * 64,
        created_by=admin,
    )
    draft = SupplierInvoice.objects.create(
        supplier_name="Fournisseur brouillon",
        supplier_key="fournisseur brouillon",
        reference="",
        issue_date=None,
        total_ttc=None,
        vat_amount=None,
        category=SupplierInvoice.Category.OTHER,
        file=pdf_upload("draft.pdf"),
        file_sha256="b" * 64,
        created_by=admin,
    )

    client.force_login(admin)
    response = client.get(reverse("accounting:suppliers"), {"completeness": "incomplete", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert draft.display_name in html
    assert complete.display_name not in html
    assert "Préparation" in html and "Paiement" in html and "Catégorie" in html

    accountant = make_user(username="filter-accountant")
    client.force_login(accountant)
    response = client.get(reverse("accounting:suppliers"), {"q": "Fournisseur", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert complete.display_name in html
    assert draft.display_name not in html
    assert "Brouillons à compléter" not in html
    assert "completeness" not in SupplierFilterForm(accounting_admin=False).fields


def test_document_filters_cover_type_review_source_and_exchange(client):
    admin = make_user(Profile.ROLE_ADMIN_BUSINESS, "document-filter-admin")
    bank = AccountingDocument.objects.create(
        title="Relevé août",
        kind=AccountingDocument.Kind.BANK,
        document_date=date(2026, 8, 1),
        file=pdf_upload("bank.pdf"),
        file_sha256="c" * 64,
        created_by=admin,
    )
    contract = AccountingDocument.objects.create(
        title="Contrat entretien",
        kind=AccountingDocument.Kind.CONTRACT,
        document_date=date(2026, 8, 2),
        file=pdf_upload("contract.pdf"),
        file_sha256="d" * 64,
        created_by=admin,
    )
    bank.reviewed_at = timezone.now()
    bank.reviewed_by = admin
    bank.save(update_fields=["reviewed_at", "reviewed_by", "updated_at"])
    AccountingExchange.objects.create(
        subject="Contrat à vérifier",
        kind=AccountingExchange.Kind.INFORMATION,
        status=AccountingExchange.Status.WAITING_NETEXPRESS,
        created_by=admin,
        accounting_document=contract,
    )

    client.force_login(admin)
    response = client.get(reverse("accounting:documents"), {"kind": AccountingDocument.Kind.BANK, "review": "reviewed", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert bank.title in html
    assert contract.title not in html

    response = client.get(reverse("accounting:documents"), {"exchange": "open", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert contract.title in html
    assert bank.title not in html
    assert "Type de document" in html and "Origine" in html


def test_exchange_filters_cover_status_priority_context_and_unread(client):
    accountant = make_user(username="exchange-filter-accountant")
    first = AccountingExchange.objects.create(
        subject="TVA août",
        kind=AccountingExchange.Kind.CORRECTION_REQUEST,
        status=AccountingExchange.Status.WAITING_ACCOUNTANT,
        priority=AccountingExchange.Priority.HIGH,
        created_by=accountant,
    )
    second = AccountingExchange.objects.create(
        subject="Information générale",
        kind=AccountingExchange.Kind.INFORMATION,
        status=AccountingExchange.Status.RESOLVED,
        priority=AccountingExchange.Priority.NORMAL,
        created_by=accountant,
    )
    AccountingExchangeReadState.objects.create(
        exchange=second,
        user=accountant,
        last_read_at=timezone.now() + timedelta(seconds=1),
    )
    client.force_login(accountant)

    response = client.get(reverse("accounting:exchanges"), {
        "status": AccountingExchange.Status.WAITING_ACCOUNTANT,
        "priority": AccountingExchange.Priority.HIGH,
        "context": "general",
        "date_from": "2026-01-01",
        "date_to": "2026-12-31",
    })
    html = response.content.decode("utf-8")
    assert first.subject in html
    assert second.subject not in html
    assert "Type de demande" in html and "Pièces jointes" in html and "Contexte" in html

    response = client.get(reverse("accounting:exchanges"), {"unread": "on", "date_from": "2026-01-01", "date_to": "2026-12-31"})
    html = response.content.decode("utf-8")
    assert first.subject in html
    assert second.subject not in html


def test_filter_validation_rejects_inverted_amount_range(client):
    accountant = make_user(username="amount-filter-accountant")
    client.force_login(accountant)
    response = client.get(reverse("accounting:sales"), {
        "amount_min": "500",
        "amount_max": "100",
        "date_from": "2026-01-01",
        "date_to": "2026-12-31",
    })
    assert response.status_code == 200
    assert "Le montant minimum ne peut pas dépasser le montant maximum." in response.content.decode("utf-8")
