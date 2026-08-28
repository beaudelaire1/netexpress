import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from accounts.access import confirm_email
from accounting.access import (
    can_access_accounting_exchange,
    can_access_accounting_exchange_document,
)
from accounting.models import (
    AccountingExchange,
    AccountingExchangeDocument,
    AccountingExchangeMessage,
    AccountingExchangeReadState,
)
from devis.models import Client, Quote
from factures.models import Invoice

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role="accountant", verified=True):
    index = User.objects.count()
    user = User.objects.create_user(
        username=f"exchange_{role}_{index}",
        email=f"exchange{index}@example.test",
        password="LongSecurePassword854!",
    )
    profile = user.profile
    profile.role = role
    profile.save(update_fields=["role"])
    if verified:
        confirm_email(user)
    user.refresh_from_db()
    return user


def pdf_upload(name="note-cabinet.pdf", content=b"%PDF-1.4\nAccounting exchange\n%%EOF"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_accounting_exchange_access_boundary():
    accountant = make_user("accountant", verified=True)
    unverified = make_user("accountant", verified=False)
    admin = make_user("admin_business", verified=False)
    client_user = make_user("client", verified=True)
    exchange = AccountingExchange.objects.create(subject="Question de clôture", created_by=accountant)

    assert can_access_accounting_exchange(accountant, exchange)
    assert can_access_accounting_exchange(admin, exchange)
    assert not can_access_accounting_exchange(unverified, exchange)
    assert not can_access_accounting_exchange(client_user, exchange)


def test_exchange_accepts_zero_or_one_context_but_rejects_multiple():
    customer = Client.objects.create(full_name="Client test", email="client@example.test")
    quote = Quote.objects.create(client=customer)
    invoice = Invoice.objects.create(quote=quote)

    exchange = AccountingExchange(subject="Contexte facture", invoice=invoice)
    exchange.full_clean()

    invalid = AccountingExchange(subject="Double contexte", invoice=invoice, quote=quote)
    with pytest.raises(ValidationError):
        invalid.full_clean()


def test_message_updates_exchange_last_activity():
    user = make_user()
    exchange = AccountingExchange.objects.create(subject="Pièce manquante", created_by=user)
    previous_activity = exchange.last_activity_at

    message = AccountingExchangeMessage.objects.create(
        exchange=exchange,
        author=user,
        content="Merci de transmettre le justificatif demandé.",
    )
    exchange.refresh_from_db()

    assert exchange.last_activity_at >= previous_activity
    assert exchange.last_activity_at == message.created_at


def test_exchange_document_records_private_file_metadata():
    user = make_user()
    exchange = AccountingExchange.objects.create(subject="Note du cabinet", created_by=user)
    payload = b"%PDF-1.4\nPrivate accounting note\n%%EOF"

    document = AccountingExchangeDocument.objects.create(
        exchange=exchange,
        uploaded_by=user,
        title="Note de contrôle — Août 2026",
        document_type=AccountingExchangeDocument.Type.ACCOUNTANT_NOTE,
        file=pdf_upload(content=payload),
    )

    assert document.original_filename == "note-cabinet.pdf"
    assert document.file_sha256 == hashlib.sha256(payload).hexdigest()
    assert document.file_size == len(payload)
    assert document.mime_type == "application/pdf"
    assert document.file.name.startswith("accounting/exchanges/")
    assert "/documents/prives/" in document.file.url


def test_document_message_must_belong_to_same_exchange():
    user = make_user()
    first = AccountingExchange.objects.create(subject="Premier échange", created_by=user)
    second = AccountingExchange.objects.create(subject="Second échange", created_by=user)
    message = AccountingExchangeMessage.objects.create(
        exchange=first,
        author=user,
        content="Message du premier échange",
    )
    document = AccountingExchangeDocument(
        exchange=second,
        message=message,
        uploaded_by=user,
        title="Document incohérent",
        file=pdf_upload(),
    )

    with pytest.raises(ValidationError):
        document.full_clean()


def test_shared_exchange_document_is_downloadable_only_inside_accounting_boundary(client):
    accountant = make_user("accountant", verified=True)
    admin = make_user("admin_business", verified=False)
    external_client = make_user("client", verified=True)
    exchange = AccountingExchange.objects.create(subject="Document partagé", created_by=accountant)
    document = AccountingExchangeDocument.objects.create(
        exchange=exchange,
        uploaded_by=accountant,
        title="Note partagée",
        file=pdf_upload(),
        visibility=AccountingExchangeDocument.Visibility.SHARED,
    )

    assert can_access_accounting_exchange_document(accountant, document)
    assert can_access_accounting_exchange_document(admin, document)
    assert not can_access_accounting_exchange_document(external_client, document)

    client.force_login(accountant)
    response = client.get(document.file.url)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"

    client.force_login(external_client)
    assert client.get(document.file.url).status_code == 404


def test_netexpress_only_document_is_hidden_from_accountant(client):
    accountant = make_user("accountant", verified=True)
    admin = make_user("admin_business", verified=False)
    exchange = AccountingExchange.objects.create(subject="Note interne", created_by=admin)
    document = AccountingExchangeDocument.objects.create(
        exchange=exchange,
        uploaded_by=admin,
        title="Préparation interne",
        file=pdf_upload(name="interne.pdf", content=b"%PDF-1.4\nInternal\n%%EOF"),
        visibility=AccountingExchangeDocument.Visibility.NETEXPRESS_ONLY,
    )

    assert not can_access_accounting_exchange_document(accountant, document)
    assert can_access_accounting_exchange_document(admin, document)

    client.force_login(accountant)
    assert client.get(document.file.url).status_code == 404
    client.force_login(admin)
    assert client.get(document.file.url).status_code == 200


def test_read_state_is_unique_per_user_and_exchange():
    user = make_user()
    exchange = AccountingExchange.objects.create(subject="Suivi de lecture", created_by=user)
    AccountingExchangeReadState.objects.create(exchange=exchange, user=user)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AccountingExchangeReadState.objects.create(exchange=exchange, user=user)
