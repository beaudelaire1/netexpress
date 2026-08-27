import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, close_old_connections
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.access import confirm_email
from accounts.forms import ProfileForm, SignUpForm
from accounts.models import Profile
from accounting.forms import SupplierInvoiceForm
from accounting.models import InvoiceReview, SupplierInvoice
from accounting.services import invoice_fingerprint, is_reviewed, csv_content
from core.services.document_service import ClientDocumentService
from devis.models import Client as Customer, Quote, QuoteItem
from devis.services import create_invoice_from_quote, QuoteStatusError, QuoteAlreadyInvoicedError
from factures.models import Invoice, InvoiceItem

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role="accountant", verified=True):
    user = User.objects.create_user(username=f"{role}_{User.objects.count()}", email=f"u{User.objects.count()}@example.test", password="LongSecurePassword854!")
    profile = user.profile
    profile.role = role
    profile.save(update_fields=["role"])
    if verified:
        confirm_email(user)
    user.refresh_from_db()
    return user


def make_invoice(status="sent", quantity="0.50"):
    customer = Customer.objects.create(full_name="Client test", email="client@example.test")
    quote = Quote.objects.create(client=customer, status="accepted")
    QuoteItem.objects.create(quote=quote, description="Nettoyage", quantity=Decimal(quantity), unit_price=100, tax_rate=20)
    invoice = create_invoice_from_quote(quote).invoice
    invoice.status = status
    invoice.save(update_fields=["status"])
    return invoice


def purchase_data(**changes):
    return {"supplier_name": "Fournisseur", "reference": "FOUR-01", "issue_date": "2026-08-01",
            "total_ttc": "120.00", "vat_amount": "20.00", "category": "supplies", **changes}


def upload(content=b"%PDF-1.4\nTest supplier\n%%EOF", filename="piece.pdf"):
    return SimpleUploadedFile(filename, content, content_type="application/pdf")


def test_public_roles_cannot_escalate(client):
    form = SignUpForm({"username": "attacker", "email": "attacker@example.test", "role": "admin_technical",
        "password1": "LongSecurePassword854!", "password2": "LongSecurePassword854!"})
    assert form.is_valid(), form.errors
    user = form.save()
    user.refresh_from_db()
    assert user.profile.role == "client" and not user.is_staff and not user.is_superuser
    form = ProfileForm({"role": "admin_technical", "phone": "123"}, instance=user.profile)
    assert form.is_valid()
    form.save()
    user.refresh_from_db()
    assert user.profile.role == "client" and not user.is_superuser


def test_signup_http_backend_and_mail(client):
    response = client.post(reverse("accounts:signup"), {"username": "new", "email": "new@example.test",
        "role": "admin_technical", "password1": "LongSecurePassword854!", "password2": "LongSecurePassword854!"})
    assert response.status_code == 302
    assert not User.objects.get(username="new").is_superuser


def test_email_claim_does_not_grant_documents():
    invoice = make_invoice()
    user = make_user("client", verified=False)
    user.email = invoice.quote.client.email
    user.save()
    assert not ClientDocumentService.can_access_quote(user, invoice.quote)
    assert not ClientDocumentService.get_accessible_invoices(user).exists()
    confirm_email(user)
    assert ClientDocumentService.can_access_invoice(user, invoice)
    user.email = "changed@example.test"
    user.save()
    assert not ClientDocumentService.can_access_invoice(user, invoice)


def test_invitation_single_use_and_role_redirect(client):
    user = make_user(verified=False)
    token = default_token_generator.make_token(user)
    url = reverse("accounts:password_setup", args=[urlsafe_base64_encode(force_bytes(user.pk)), token])
    response = client.post(url, {"new_password1": "AnotherSecure854!", "new_password2": "AnotherSecure854!"})
    assert response.status_code == 302 and response.url == "/comptabilite/"
    user.refresh_from_db()
    assert user.profile.has_verified_email
    assert not default_token_generator.check_token(user, token)


@pytest.mark.parametrize("role,expected", [("client",403), ("worker",403), ("accountant",200), ("admin_business",200), ("admin_technical",200)])
def test_role_access_matrix(client, role, expected):
    user = make_user(role)
    client.force_login(user)
    assert client.get(reverse("accounting:dashboard")).status_code == expected
    if role == "accountant":
        assert not user.is_staff and not user.is_superuser
        assert client.get(reverse("accounting:accountants")).status_code == 403
        assert client.get("/gestion/").status_code != 200


def test_profile_and_forced_password_change_do_not_loop(client):
    user = make_user("client")
    user.profile.force_password_change = True
    user.profile.save(update_fields=["force_password_change"])
    client.force_login(user)
    assert client.get("/client/").url == reverse("accounts:password_change")
    assert client.get(reverse("accounts:password_change")).status_code == 200


def test_login_external_next_is_rejected(client):
    user = make_user("client")
    response = client.post(reverse("accounts:login") + "?next=https://evil.example", {"username": user.username, "password": "LongSecurePassword854!"})
    assert response.status_code == 302 and response.url == "/client/"


def test_decimal_conversion_and_recalculation():
    invoice = make_invoice()
    assert invoice.invoice_items.get().quantity == Decimal("0.50")
    invoice.compute_totals()
    assert invoice.total_ht == Decimal("50.00")
    assert invoice.total_ttc == Decimal("60.00")
    with pytest.raises((QuoteStatusError, QuoteAlreadyInvoicedError)):
        create_invoice_from_quote(invoice.quote_id)


@pytest.mark.parametrize("kind", ["invoice", "quote"])
def test_numbers_after_999_and_soft_delete(kind):
    customer = Customer.objects.create(full_name="Test", email="test@example.test")
    model = Invoice if kind == "invoice" else Quote
    prefix = "FAC" if kind == "invoice" else "DEV"
    fields = {"issue_date": date(2026, 1, 1), **({"client": customer} if kind == "quote" else {})}
    model.objects.create(number=f"{prefix}-2026-999", **fields)
    last = model.objects.create(number=f"{prefix}-2026-1000", **fields)
    last.delete()
    assert model.objects.create(**fields).number == f"{prefix}-2026-1001"


def test_issued_visible_draft_hidden_archive_preserved(client):
    user = make_user()
    client.force_login(user)
    invoice = make_invoice(status="draft")
    url = reverse("accounting:invoice_detail", args=[invoice.pk])
    assert client.get(url).status_code == 404
    invoice.status = "sent"
    invoice.save(update_fields=["status"])
    invoice.delete()
    assert client.get(url).status_code == 200


def test_review_detects_modifications(client):
    user = make_user()
    client.force_login(user)
    invoice = make_invoice()
    fingerprint = invoice_fingerprint(invoice)
    url = reverse("accounting:review_invoice", args=[invoice.pk])
    assert client.post(url, {"fingerprint": fingerprint, "note": "Vérifié"}).status_code == 302
    invoice.refresh_from_db()
    assert is_reviewed(invoice)
    item = invoice.invoice_items.get()
    item.description = "Changed"
    item.save()
    invoice.refresh_from_db()
    assert not is_reviewed(invoice)
    client.post(url, {"fingerprint": fingerprint})
    assert InvoiceReview.objects.get(invoice=invoice).fingerprint == fingerprint
    assert not is_reviewed(invoice)


def test_supplier_upload_total_duplicate_and_private_download(client):
    user = make_user()
    client.force_login(user)
    response = client.post(reverse("accounting:supplier_add"), {**purchase_data(), "file": upload()})
    assert response.status_code == 302, response.content[:1000]
    purchase = SupplierInvoice.objects.get()
    assert purchase.total_ht == Decimal("100.00")
    assert "/documents/prives/" in purchase.file.url
    assert client.get(purchase.file.url).status_code == 200
    client.logout()
    assert client.get(purchase.file.url).status_code == 302
    client.force_login(make_user("client"))
    assert client.get(purchase.file.url).status_code == 404
    form = SupplierInvoiceForm(purchase_data(reference="different"), {"file": upload()})
    assert not form.is_valid() and "file" in form.errors


@pytest.mark.parametrize("file,total,vat", [(upload(b"<html>bad</html>"),"120","20"), (upload(filename="piece.html"),"120","20"), (upload(),"-1","0"), (upload(),"120","121")])
def test_supplier_rejects_invalid_files_and_amounts(file, total, vat):
    form = SupplierInvoiceForm(purchase_data(total_ttc=total, vat_amount=vat), {"file": file})
    assert not form.is_valid()


def test_supplier_control_edit_resets_review(client):
    client.force_login(make_user())
    client.post(reverse("accounting:supplier_add"), {**purchase_data(), "file": upload()})
    purchase = SupplierInvoice.objects.get()
    client.post(reverse("accounting:review_supplier", args=[purchase.pk]), {"fingerprint": purchase.updated_at.isoformat()})
    purchase.refresh_from_db()
    assert purchase.reviewed_at
    response = client.post(reverse("accounting:supplier_edit", args=[purchase.pk]), {**purchase_data(total_ttc="130"), "version": purchase.updated_at.isoformat()})
    assert response.status_code == 302
    purchase.refresh_from_db()
    assert purchase.reviewed_at is None and purchase.total_ttc == Decimal(130)


def test_exports_period_formulas_zip_and_totals(client):
    client.force_login(make_user())
    invoice = make_invoice()
    client.post(reverse("accounting:supplier_add"), {**purchase_data(supplier_name="=CMD()"), "file": upload()})
    response = client.get(reverse("accounting:export"), {"date_from": "2026-01-01", "date_to": "2026-12-31"})
    assert response.status_code == 200
    assert "'=CMD()" in response.content.decode("utf-8-sig")
    assert "120.00" in response.content.decode("utf-8-sig")
    with patch.object(Invoice, "generate_pdf", return_value=b"%PDF-1.4 test"):
        response = client.get(reverse("accounting:export"), {"format": "zip", "date_from": "2026-01-01", "date_to": "2026-12-31"})
        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            assert len(archive.namelist()) == 3
            assert "journal.csv" in archive.namelist()
    response = client.get(reverse("accounting:dashboard"), {"date_from": "2026-01-01", "date_to": "2026-12-31"})
    assert response.context["totals"]["purchases"] == Decimal(120)
    assert response.context["totals"]["net_sales"] == Decimal(60)
    assert client.get(reverse("accounting:export"), {"date_from": "2027-12-31", "date_to": "2026-01-01"}).status_code == 400


def test_accountant_invite_disable(client):
    client.force_login(make_user("admin_business"))
    response = client.post(reverse("accounting:accountants"), {"email": "cabinet@example.test", "first_name": "Anne", "last_name": "Test", "accounting_firm": "Cabinet Test"})
    assert response.status_code == 302
    user = User.objects.get(email="cabinet@example.test")
    assert user.profile.role == "accountant" and not user.is_staff and not user.has_usable_password()
    client.post(reverse("accounting:accountant_action", args=[user.pk]), {"action": "disable"})
    user.refresh_from_db()
    assert not user.is_active


def test_get_cannot_mutate_and_private_legacy_media_blocked(client):
    client.force_login(make_user("admin_business"))
    invoice = make_invoice()
    assert client.get(reverse("factures:create", args=[invoice.quote_id])).status_code == 405
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.get("/media/factures/secret.pdf").status_code == 404


def test_turnstile_failure_denies(settings):
    from django.test import RequestFactory
    from core.turnstile import verify_turnstile
    settings.TURNSTILE_SECRET_KEY = "test"
    with patch("core.turnstile.requests.post", side_effect=OSError):
        assert not verify_turnstile(RequestFactory().post("/", {"cf-turnstile-response": "test"}))


def test_pdf_fetcher_restricts_network_and_local_secrets():
    from core.services.document_generator import restricted_fetcher
    for url in ["https://example.test/a.png", "http://169.254.169.254/", "file:///etc/passwd"]:
        with pytest.raises(ValueError):
            restricted_fetcher(url)


@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_invoice_numbers():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL required for row-lock concurrency")
    def create(_):
        close_old_connections()
        try:
            return Invoice.objects.create().number
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=5) as executor:
        numbers = list(executor.map(create, range(15)))
    assert len(set(numbers)) == 15
