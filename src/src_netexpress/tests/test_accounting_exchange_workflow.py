import io
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.access import confirm_email
from accounting.exchange_file_validation import validate_exchange_document
from accounting.exchange_services import unread_exchange_count
from accounting.models import (
    AccountingDocument,
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeMessage,
)
from devis.models import Client, Quote, QuoteItem
from devis.services import create_invoice_from_quote

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role="accountant", verified=True):
    index = User.objects.count()
    user = User.objects.create_user(
        username=f"workflow_{role}_{index}",
        email=f"workflow{index}@example.test",
        password="LongSecurePassword854!",
    )
    user.profile.role = role
    user.profile.accounting_firm = "Cabinet Test" if role == "accountant" else ""
    user.profile.save(update_fields=["role", "accounting_firm"])
    if verified:
        confirm_email(user)
    user.refresh_from_db()
    return user


def pdf_upload(name="piece.pdf", payload=b"%PDF-1.4\nExchange workflow\n%%EOF"):
    return SimpleUploadedFile(name, payload, content_type="application/pdf")


def xlsx_upload(name="controle.xlsx"):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("xl/workbook.xml", "<workbook></workbook>")
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def make_issued_invoice():
    customer = Client.objects.create(full_name="Client comptable", email="client@example.test")
    quote = Quote.objects.create(client=customer, status="accepted")
    QuoteItem.objects.create(
        quote=quote,
        description="Entretien",
        quantity="1.00",
        unit_price="100.00",
        tax_rate="20.00",
    )
    invoice = create_invoice_from_quote(quote).invoice
    invoice.status = "sent"
    invoice.save(update_fields=["status"])
    return invoice


def create_payload(**overrides):
    return {
        "mode": "message",
        "subject": "Question de clôture",
        "kind": AccountingExchange.Kind.QUESTION,
        "priority": AccountingExchange.Priority.NORMAL,
        "message": "Pouvez-vous vérifier ce point ?",
        **overrides,
    }


def test_accountant_creates_traceable_exchange(client):
    accountant = make_user("accountant")
    make_user("admin_business", verified=False)
    client.force_login(accountant)

    response = client.post(reverse("accounting:exchange_create"), create_payload())

    assert response.status_code == 302
    exchange = AccountingExchange.objects.get()
    assert exchange.status == AccountingExchange.Status.WAITING_NETEXPRESS
    assert exchange.created_by == accountant
    assert exchange.messages.get().content == "Pouvez-vous vérifier ce point ?"
    assert response.url == reverse("accounting:exchange_detail", args=[exchange.pk])


def test_admin_reply_moves_workflow_to_cabinet_and_becomes_unread(client):
    accountant = make_user("accountant")
    admin = make_user("admin_business", verified=False)
    exchange = AccountingExchange.objects.create(
        subject="TVA à contrôler",
        created_by=accountant,
        status=AccountingExchange.Status.WAITING_NETEXPRESS,
    )
    client.force_login(admin)

    response = client.post(
        reverse("accounting:exchange_reply", args=[exchange.pk]),
        {"content": "Le montant a été vérifié."},
    )

    assert response.status_code == 302
    exchange.refresh_from_db()
    assert exchange.status == AccountingExchange.Status.WAITING_ACCOUNTANT
    assert unread_exchange_count(accountant) == 1
    assert exchange.messages.filter(author=admin).count() == 1


def test_opening_exchange_marks_it_read(client):
    accountant = make_user("accountant")
    admin = make_user("admin_business", verified=False)
    exchange = AccountingExchange.objects.create(
        subject="Document reçu",
        created_by=admin,
        status=AccountingExchange.Status.WAITING_ACCOUNTANT,
    )
    assert unread_exchange_count(accountant) == 1

    client.force_login(accountant)
    response = client.get(reverse("accounting:exchange_detail", args=[exchange.pk]))

    assert response.status_code == 200
    assert unread_exchange_count(accountant) == 0


def test_accountant_can_publish_xlsx_and_cannot_force_internal_visibility(client):
    accountant = make_user("accountant")
    make_user("admin_business", verified=False)
    client.force_login(accountant)

    response = client.post(
        reverse("accounting:exchange_create"),
        create_payload(
            mode="document",
            subject="Tableau de régularisation",
            kind=AccountingExchange.Kind.DOCUMENT_DELIVERY,
            message="",
            file=xlsx_upload(),
            document_title="Tableau de régularisation TVA",
            document_type=AccountingExchangeDocument.Type.SPREADSHEET,
            visibility=AccountingExchangeDocument.Visibility.NETEXPRESS_ONLY,
        ),
    )

    assert response.status_code == 302
    document = AccountingExchangeDocument.objects.get()
    assert document.visibility == AccountingExchangeDocument.Visibility.SHARED
    assert document.extension == "XLSX"
    assert document.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "/documents/prives/" in document.file.url


def test_fake_office_archive_is_rejected():
    fake = SimpleUploadedFile(
        "controle.xlsx",
        b"not-a-zip-file",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    with pytest.raises(ValidationError):
        validate_exchange_document(fake)


def test_netexpress_internal_exchange_document_remains_hidden_from_accountant(client):
    accountant = make_user("accountant")
    admin = make_user("admin_business", verified=False)
    exchange = AccountingExchange.objects.create(subject="Préparation interne", created_by=admin)
    document = AccountingExchangeDocument.objects.create(
        exchange=exchange,
        uploaded_by=admin,
        title="Note interne",
        visibility=AccountingExchangeDocument.Visibility.NETEXPRESS_ONLY,
        file=pdf_upload("interne.pdf", b"%PDF-1.4\nPrivate admin note\n%%EOF"),
    )

    client.force_login(accountant)
    assert client.get(document.file.url).status_code == 404
    client.force_login(admin)
    assert client.get(document.file.url).status_code == 200


def test_exchange_can_be_created_from_accounting_visible_invoice(client):
    accountant = make_user("accountant")
    make_user("admin_business", verified=False)
    invoice = make_issued_invoice()
    client.force_login(accountant)

    response = client.post(
        reverse("accounting:exchange_create"),
        create_payload(
            context_type="invoice",
            context_id=str(invoice.pk),
            subject=f"À propos de {invoice.number}",
        ),
    )

    assert response.status_code == 302
    exchange = AccountingExchange.objects.get()
    assert exchange.invoice == invoice
    assert exchange.quote is None


def test_hidden_invoice_cannot_be_used_as_exchange_context(client):
    accountant = make_user("accountant")
    customer = Client.objects.create(full_name="Client brouillon", email="draft@example.test")
    quote = Quote.objects.create(client=customer)
    from factures.models import Invoice

    invoice = Invoice.objects.create(quote=quote, status="draft")
    client.force_login(accountant)

    response = client.get(
        reverse("accounting:exchange_create"),
        {"context_type": "invoice", "context_id": invoice.pk},
    )

    assert response.status_code == 404


def test_exchange_can_be_resolved_and_reopened(client):
    accountant = make_user("accountant")
    exchange = AccountingExchange.objects.create(
        subject="Demande traitée",
        created_by=accountant,
        status=AccountingExchange.Status.WAITING_NETEXPRESS,
    )
    client.force_login(accountant)

    response = client.post(
        reverse("accounting:exchange_status", args=[exchange.pk]),
        {"action": "resolve"},
    )
    assert response.status_code == 302
    exchange.refresh_from_db()
    assert exchange.status == AccountingExchange.Status.RESOLVED

    client.post(
        reverse("accounting:exchange_status", args=[exchange.pk]),
        {"action": "reopen"},
    )
    exchange.refresh_from_db()
    assert exchange.status == AccountingExchange.Status.WAITING_NETEXPRESS


def test_netexpress_can_promote_received_document_into_accounting_folder(client):
    accountant = make_user("accountant")
    admin = make_user("admin_business", verified=False)
    exchange = AccountingExchange.objects.create(subject="Attestation reçue", created_by=accountant)
    document = AccountingExchangeDocument.objects.create(
        exchange=exchange,
        uploaded_by=accountant,
        title="Attestation du cabinet",
        file=pdf_upload("attestation.pdf", b"%PDF-1.4\nAttestation\n%%EOF"),
    )
    client.force_login(admin)

    response = client.post(
        reverse(
            "accounting:exchange_document_promote",
            args=[exchange.pk, document.pk],
        )
    )

    assert response.status_code == 302
    document.refresh_from_db()
    assert document.promoted_to is not None
    target = AccountingDocument.objects.get(pk=document.promoted_to_id)
    assert target.title == "Attestation du cabinet"
    assert target.file.name == document.file.name

    client.post(
        reverse(
            "accounting:exchange_document_promote",
            args=[exchange.pk, document.pk],
        )
    )
    assert AccountingDocument.objects.count() == 1


def test_message_content_is_rendered_escaped_in_exchange_detail(client):
    accountant = make_user("accountant")
    exchange = AccountingExchange.objects.create(subject="Sécurité", created_by=accountant)
    AccountingExchangeMessage.objects.create(
        exchange=exchange,
        author=accountant,
        content='<script>alert("x")</script>',
    )
    client.force_login(accountant)

    response = client.get(reverse("accounting:exchange_detail", args=[exchange.pk]))
    content = response.content.decode("utf-8")

    assert '<script>alert("x")</script>' not in content
    assert "&lt;script&gt;" in content


def test_legacy_message_endpoint_now_creates_accounting_exchange(client):
    accountant = make_user("accountant")
    make_user("admin_business", verified=False)
    client.force_login(accountant)

    response = client.post(
        reverse("accounting:message_netexpress"),
        {"message": "Ancien raccourci, nouveau domaine."},
    )

    assert response.status_code == 302
    exchange = AccountingExchange.objects.get()
    assert exchange.messages.get().content == "Ancien raccourci, nouveau domaine."
    assert response.url == reverse("accounting:exchange_detail", args=[exchange.pk])


def test_accounting_navigation_exposes_exchange_workspace(client):
    accountant = make_user("accountant")
    client.force_login(accountant)

    response = client.get(reverse("accounting:exchanges"))
    content = response.content.decode("utf-8")

    assert response.status_code == 200
    assert "Échanges" in content
    assert "Mettre un document à disposition" in content
    assert reverse("accounting:exchange_create") in content
