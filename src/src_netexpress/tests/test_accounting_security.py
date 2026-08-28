import io
import csv
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.db import connection, close_old_connections
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.access import confirm_email
from accounts.forms import ProfileForm, SignUpForm
from accounts.models import Profile
from accounting.forms import AccountingDocumentForm, SupplierInvoiceForm
from accounting.models import AccountingDocument, InvoiceReview, SupplierInvoice
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
    user = make_user("admin_business")
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
    owner = make_user("admin_business")
    client.force_login(owner)
    client.post(reverse("accounting:supplier_add"), {**purchase_data(), "file": upload()})
    purchase = SupplierInvoice.objects.get()
    client.force_login(make_user())
    client.post(reverse("accounting:review_supplier", args=[purchase.pk]), {"fingerprint": purchase.updated_at.isoformat()})
    purchase.refresh_from_db()
    assert purchase.reviewed_at
    client.force_login(owner)
    response = client.post(reverse("accounting:supplier_edit", args=[purchase.pk]), {**purchase_data(total_ttc="130"), "version": purchase.updated_at.isoformat()})
    assert response.status_code == 302
    purchase.refresh_from_db()
    assert purchase.reviewed_at is None and purchase.total_ttc == Decimal(130)


def test_exports_period_formulas_zip_and_totals(client):
    client.force_login(make_user("admin_business"))
    invoice = make_invoice()
    client.post(reverse("accounting:supplier_add"), {**purchase_data(supplier_name="=CMD()"), "file": upload()})
    client.force_login(make_user())
    selection = {"date_from": "2026-01-01", "date_to": "2026-12-31"}
    response = client.get(reverse("accounting:export"), selection)
    assert response.status_code == 200
    assert "'=CMD()" in response.content.decode("utf-8-sig")
    assert "120.00" in response.content.decode("utf-8-sig")
    with patch.object(Invoice, "generate_pdf", return_value=b"%PDF-1.4 test"):
        response = client.get(reverse("accounting:export"), {**selection, "format": "zip"})
        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            names = archive.namelist()
            assert len(names) == 3
            assert "journal.csv" in names
            assert any(name.startswith("ventes/") for name in names)
            assert any(name.startswith("achats/") for name in names)
            assert "devis.csv" not in names
    response = client.get(reverse("accounting:dashboard"), selection)
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


def test_admin_dashboard_has_accounting_navigation_and_kpis_before_actions(client):
    client.force_login(make_user("admin_business"))
    response = client.get(reverse("core:admin_dashboard"))
    assert response.status_code == 200
    html = response.content.decode()
    # Shared desktop + mobile navigation survive the dashboard's own nav block.
    assert html.count('href="/comptabilite/"') >= 3
    assert html.index("Chiffre d'Affaires Total") < html.index("Actions Rapides") < html.index("Pièces et accès du cabinet")
    assert reverse("accounting:supplier_add") not in html
    assert reverse("accounting:document_add") not in html
    portal = client.get(reverse("accounting:dashboard")).content.decode()
    assert 'class="back-dashboard" href="/admin-dashboard/"' in portal
    assert "Espace comptable" in portal and "NetExpress · Espace entreprise" in portal
    assert portal.index('aria-label="Synthèse de la période"') < portal.index('aria-label="Préparer des pièces"')


@pytest.mark.parametrize("role,allowed", [("admin_business", True), ("admin_technical", True), ("accountant", False), ("client", False), ("worker", False)])
def test_only_company_can_deposit(client, role, allowed):
    client.force_login(make_user(role))
    for route in ("supplier_add", "document_add"):
        url = reverse(f"accounting:{route}")
        assert client.get(url).status_code == (200 if allowed else 403)
        response = client.post(url, {"file": upload(f"%PDF-1.4 {role} {route}".encode())})
        assert response.status_code == (302 if allowed else 403), response.content[:1000]


def test_supplier_file_only_preserves_unknowns_and_blocks_review(client):
    client.force_login(make_user("admin_business"))
    response = client.post(reverse("accounting:supplier_add"), {"file": upload()})
    assert response.status_code == 302, response.content[:1500]
    purchase = SupplierInvoice.objects.get()
    assert purchase.issue_date is None and purchase.total_ttc is None and purchase.vat_amount is None
    assert not purchase.is_complete and purchase.total_ht is None
    assert client.post(reverse("accounting:supplier_add"), {"file": upload(b"%PDF-1.4 Another invoice")}).status_code == 302
    assert SupplierInvoice.objects.count() == 2  # Blank references are not duplicates.

    client.force_login(make_user())
    response = client.get(reverse("accounting:dashboard"))
    assert response.context["totals"]["incomplete_purchases"] == 0
    assert response.context["totals"]["purchases"] == 0
    assert client.get(reverse("accounting:suppliers")).context["page"].paginator.count == 0
    assert client.get(reverse("accounting:supplier_detail", args=[purchase.pk])).status_code == 404
    assert client.post(reverse("accounting:review_supplier", args=[purchase.pk]), {"fingerprint": purchase.updated_at.isoformat()}).status_code == 404
    purchase.refresh_from_db()
    assert purchase.reviewed_at is None

    export = client.get(reverse("accounting:export"), {"date_from": "2026-01-01", "date_to": "2026-12-31"})
    assert export.status_code == 200
    assert "À compléter" not in export.content.decode("utf-8-sig")


def test_supplier_optional_metadata_validation_and_completion(client):
    client.force_login(make_user("admin_business"))
    client.post(reverse("accounting:supplier_add"), {"file": upload()})
    purchase = SupplierInvoice.objects.get()
    response = client.post(reverse("accounting:supplier_edit", args=[purchase.pk]), {
        **purchase_data(vat_amount="0"), "version": purchase.updated_at.isoformat()})
    assert response.status_code == 302
    purchase.refresh_from_db()
    assert purchase.is_complete and purchase.total_ht == Decimal("120")
    duplicate = SupplierInvoiceForm(purchase_data(supplier_name=" FOURNISSEUR "), {"file": upload(b"%PDF-1.4 different")})
    assert not duplicate.is_valid()
    client.force_login(make_user())
    assert client.get(reverse("accounting:supplier_edit", args=[purchase.pk])).status_code == 403
    assert client.post(reverse("accounting:supplier_edit", args=[purchase.pk]), purchase_data()).status_code == 403


@pytest.mark.parametrize("kind", [value for value, _ in AccountingDocument.Kind.choices])
def test_company_document_then_cabinet_review_and_download(client, kind):
    owner = make_user("admin_business")
    client.force_login(owner)
    response = client.post(reverse("accounting:document_add"), {"file": upload(filename="releve-aout.pdf"), "kind": kind})
    assert response.status_code == 302, response.content[:1500]
    document = AccountingDocument.objects.get()
    assert document.title == "releve-aout" and document.kind == kind
    assert document.created_by == owner and document.document_date == timezone.localdate()
    cabinet = make_user()
    client.force_login(cabinet)
    detail = client.get(reverse("accounting:document_detail", args=[document.pk]))
    assert detail.status_code == 200
    assert reverse("accounting:document_edit", args=[document.pk]) not in detail.content.decode()
    assert client.get(document.file.url).status_code == 200
    assert client.get(reverse("accounting:document_edit", args=[document.pk])).status_code == 403
    assert client.post(reverse("accounting:document_edit", args=[document.pk]), {"title": "Changed"}).status_code == 403
    url = reverse("accounting:review_document", args=[document.pk])
    assert client.get(url).status_code == 405
    assert client.post(url, {"fingerprint": document.updated_at.isoformat(), "note": "Pièce lisible"}).status_code == 302
    document.refresh_from_db()
    assert document.reviewed_by == cabinet and document.review_note == "Pièce lisible"
    assert client.get(reverse("accounting:documents"), {"review": "pending"}).context["page"].paginator.count == 0


def test_document_security_duplicates_and_stale_changes(client):
    owner = make_user("admin_business")
    client.force_login(owner)
    client.post(reverse("accounting:document_add"), {"file": upload()})
    document = AccountingDocument.objects.get()
    original_version = document.updated_at.isoformat()
    assert not AccountingDocumentForm({"kind": "bank"}, {"file": upload()}).is_valid()
    assert not SupplierInvoiceForm(purchase_data(), {"file": upload()}).is_valid()
    cabinet = make_user()
    client.force_login(cabinet)
    client.post(reverse("accounting:review_document", args=[document.pk]), {"fingerprint": original_version})
    client.force_login(owner)
    document.refresh_from_db()
    response = client.post(reverse("accounting:document_edit", args=[document.pk]), {"title": "Old edit", "version": original_version})
    assert response.status_code == 200 and response.context["form"].errors
    document.refresh_from_db()
    assert document.reviewed_at and document.title == "piece"
    client.post(reverse("accounting:document_edit", args=[document.pk]), {"title": "New title", "version": document.updated_at.isoformat()})
    document.refresh_from_db()
    assert document.title == "New title" and not document.reviewed_at and not document.review_note
    client.force_login(cabinet)
    client.post(reverse("accounting:review_document", args=[document.pk]), {"fingerprint": original_version})
    document.refresh_from_db()
    assert document.reviewed_at is None
    for role in ("client", "worker"):
        client.force_login(make_user(role))
        assert client.get(document.file.url).status_code == 404
        assert client.get(reverse("accounting:document_detail", args=[document.pk])).status_code == 403
    client.logout()
    assert client.get(document.file.url).status_code == 302
    client.force_login(make_user(verified=False))
    assert client.get(document.file.url).status_code == 404
    assert client.get(reverse("accounting:documents")).status_code == 302


def test_company_cannot_perform_cabinet_controls(client):
    client.force_login(make_user("admin_business"))
    invoice = make_invoice()
    client.post(reverse("accounting:supplier_add"), {**purchase_data(), "file": upload()})
    client.post(reverse("accounting:document_add"), {"file": upload(b"%PDF-1.4 bank")})
    purchase = SupplierInvoice.objects.get()
    document = AccountingDocument.objects.get()
    for route, piece in [("review_invoice", invoice), ("review_supplier", purchase), ("review_document", document)]:
        assert client.post(reverse(f"accounting:{route}", args=[piece.pk]), {}).status_code == 403
    assert not InvoiceReview.objects.exists()
    assert purchase.reviewed_at is None and document.reviewed_at is None
    assert "Marquer comme vérifié" not in client.get(reverse("accounting:document_detail", args=[document.pk])).content.decode()


@pytest.mark.parametrize("content,filename", [(b"<html>bad</html>", "bad.pdf"), (b"%PDF-1.4", "bad.html"), (b"", "empty.pdf"), (b"%PDF-" + b"x" * (10 * 1024 * 1024), "large.pdf")], ids=["invalid-signature", "invalid-extension", "empty", "too-large"])
def test_document_rejects_invalid_uploads(content, filename):
    form = AccountingDocumentForm({}, {"file": upload(content, filename)})
    assert not form.is_valid() and "file" in form.errors


def test_document_filters_exports_and_no_effect_on_sales(client):
    client.force_login(make_user("admin_business"))
    client.post(reverse("accounting:document_add"), {"file": upload(), "kind": "bank", "title": "=SUM(1)", "document_date": "2026-08-01"})
    client.post(reverse("accounting:document_add"), {"file": upload(b"%PDF-1.4 old"), "kind": "contract", "document_date": "2025-08-01"})
    client.force_login(make_user())
    selection = {"date_from": "2026-01-01", "date_to": "2026-12-31"}
    response = client.get(reverse("accounting:documents"), {**selection, "kind": "bank", "q": "SUM"})
    assert response.context["page"].paginator.count == 1
    assert client.get(reverse("accounting:documents"), {**selection, "kind": "contract"}).context["page"].paginator.count == 0
    totals = client.get(reverse("accounting:dashboard"), selection).context["totals"]
    assert totals["documents"] == 1 and totals["pending_documents"] == 1 and totals["net_sales"] == totals["purchases"] == 0
    response = client.get(reverse("accounting:export"), {**selection, "format": "zip"})
    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
        assert len(archive.namelist()) == 2
        assert any(name.startswith("documents/") for name in archive.namelist())
        assert "'=SUM(1)" in archive.read("journal.csv").decode("utf-8-sig")


def test_quotes_are_readonly_context_only_and_draft_private(client):
    invoice = make_invoice()
    quote = invoice.quote
    draft = Quote.objects.create(client=quote.client, status="draft")
    client.force_login(make_user())

    assert client.get(reverse("accounting:quote_detail", args=[quote.pk])).status_code == 200
    assert client.get(reverse("accounting:quote_detail", args=[draft.pk])).status_code == 404
    assert client.get(reverse("accounting:quote_pdf", args=[draft.pk])).status_code == 404

    before = (quote.total_ttc, quote.status, quote.pdf.name)
    with patch("core.services.document_generator.DocumentGenerator.generate_quote_pdf", return_value=b"%PDF-1.4 quote") as generate:
        assert client.get(reverse("accounting:quote_pdf", args=[quote.pk])).status_code == 200
        assert generate.call_args.kwargs == {"attach": False}
    quote.refresh_from_db()
    assert (quote.total_ttc, quote.status, quote.pdf.name) == before

    selection = {"date_from": "2026-01-01", "date_to": "2026-12-31"}
    journal = client.get(reverse("accounting:export"), selection).content.decode("utf-8-sig")
    assert invoice.number in journal
    assert quote.number not in journal and draft.number not in journal
    totals = client.get(reverse("accounting:dashboard"), selection).context["totals"]
    assert totals["net_sales"] == Decimal(60)
    assert "quotes" not in totals


def test_demo_account_local_only_and_login(client, settings):
    settings.DEBUG = True
    settings.SETTINGS_MODULE = "netexpress.settings.test"
    output = io.StringIO()
    call_command("create_accounting_demo", stdout=output)
    user = User.objects.get(username="cabinet_test")
    assert user.profile.has_verified_email and user.profile.role == "accountant"
    assert not user.is_staff and not user.is_superuser
    password = output.getvalue().split("Mot de passe : ")[1].splitlines()[0]
    response = client.post(reverse("accounts:login"), {"username": user.username, "password": password})
    assert response.status_code == 302 and response.url == "/comptabilite/"
    html = client.get(response.url).content.decode()
    assert reverse("accounting:document_add") not in html and reverse("accounting:supplier_add") not in html
    assert 'href="/admin-dashboard/"' not in html
    with pytest.raises(CommandError):
        call_command("create_accounting_demo", stdout=io.StringIO())
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("create_accounting_demo", username="forbidden", stdout=io.StringIO())
    assert not User.objects.filter(username="forbidden").exists()
    settings.DEBUG = True
    settings.SETTINGS_MODULE = "netexpress.settings.prod"
    with pytest.raises(CommandError):
        call_command("create_accounting_demo", username="forbidden", stdout=io.StringIO())


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
