import io
import zipfile
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.management import CommandError, call_command
from django.urls import reverse

from accounts.access import confirm_email
from accounting.management.commands.sync_accounting_invoices import (
    Command, copy_verified, invoice_state, pdf_digest,
)
from accounting.models import AccountingActivity
from accounting.services import invoice_pdf_content, issued_invoices
from factures.models import Invoice, InvoiceItem


pytestmark = pytest.mark.django_db
ORIGINAL = b"%PDF-1.4\nOriginal historique, ne pas regenerer\n%%EOF"
HISTORICAL_TIME = datetime(2025, 12, 22, 12, 0, tzinfo=datetime_timezone.utc)


@pytest.fixture(autouse=True)
def isolated_storage(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "old-media"
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private"
    return settings


def make_legacy_invoice(status="paid", year=2025, pdf=True, issued=False, archived=False):
    invoice = Invoice.objects.create(
        status=status, issue_date=date(year, 12, 21), due_date=date(year, 12, 31),
        total_ht=Decimal("100.00"), tva=Decimal("20.00"), total_ttc=Decimal("120.00"),
        amount=Decimal("120.00"), notes="Texte historique", payment_terms="30 jours",
    )
    InvoiceItem.objects.create(invoice=invoice, description="Prestation historique",
                               quantity=1, unit_price=100, tax_rate=20)
    Invoice.all_objects.filter(pk=invoice.pk).update(
        created_at=HISTORICAL_TIME,
        issued_at=HISTORICAL_TIME if issued else None,
        is_credit_note=False,
        deleted_at=HISTORICAL_TIME if archived else None,
        pdf=f"factures/{invoice.number}.pdf" if pdf else "",
    )
    invoice.refresh_from_db()
    return invoice


def put_pdf(root, invoice, content=ORIGINAL):
    path = Path(root) / invoice.pdf.name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def run_command(**options):
    output, errors = io.StringIO(), io.StringIO()
    call_command("sync_accounting_invoices", stdout=output, stderr=errors, **options)
    return output.getvalue()


def accountant():
    user = get_user_model().objects.create_user(username="recovery_accountant", email="accountant@example.test")
    user.profile.role = "accountant"
    user.profile.save(update_fields=["role"])
    confirm_email(user)
    return user


def test_default_simulation_does_not_change_database_or_files(settings):
    invoice = make_legacy_invoice()
    original = put_pdf(settings.MEDIA_ROOT, invoice)
    before = invoice_state(invoice)
    output = run_command()
    invoice.refresh_from_db()
    assert invoice_state(invoice) == before
    assert not Path(settings.PRIVATE_MEDIA_ROOT).exists()
    assert original.read_bytes() == ORIGINAL
    assert not AccountingActivity.objects.exists()
    assert "SIMULATION" in output and "1 PDF à récupérer" in output
    assert "/comptabilite/ventes/?date_from=2025-12-21&date_to=2025-12-21" in output


def test_apply_preserves_invoice_and_original_and_is_idempotent(settings):
    invoice = make_legacy_invoice(archived=True)
    original = put_pdf(settings.MEDIA_ROOT, invoice)
    before = invoice_state(invoice)
    items = list(invoice.invoice_items.values())
    with patch.object(Invoice, "save", side_effect=AssertionError("No reissue")), \
            patch.object(Invoice, "generate_pdf", side_effect=AssertionError("No regeneration")):
        run_command(apply=True)
        second = run_command(apply=True)
    invoice.refresh_from_db()
    assert invoice_state(invoice) == before | {"issued_at": HISTORICAL_TIME}
    assert list(invoice.invoice_items.values()) == items
    assert Invoice.all_objects.count() == 1
    assert issued_invoices().filter(pk=invoice.pk).exists()
    assert (Path(settings.PRIVATE_MEDIA_ROOT) / invoice.pdf.name).read_bytes() == original.read_bytes() == ORIGINAL
    assert AccountingActivity.objects.filter(action="Reprise facture client").count() == 1
    assert "0 PDF à récupérer" in second and "0 marqueur(s)" in second
    assert not list(Path(settings.PRIVATE_MEDIA_ROOT).rglob(".accounting-*"))


@pytest.mark.parametrize("status", ["draft", "demo", "unknown", ""])
def test_unissued_drafts_quotes_and_unknown_statuses_stay_hidden(settings, status):
    invoice = make_legacy_invoice(status=status)
    original = put_pdf(settings.MEDIA_ROOT, invoice)
    before = invoice_state(invoice)
    output = run_command(apply=True)
    invoice.refresh_from_db()
    assert invoice_state(invoice) == before
    assert not Path(settings.PRIVATE_MEDIA_ROOT).exists()
    assert not issued_invoices().exists()
    assert original.read_bytes() == ORIGINAL
    assert "1 brouillon(s)" in output


@pytest.mark.parametrize("status", ["sent", "partial", "overdue", "refacturation", "avoir", "paid"])
def test_legacy_issued_statuses_are_recovered_without_changing_status(status):
    invoice = make_legacy_invoice(status=status, pdf=False)
    output = run_command(apply=True)
    invoice.refresh_from_db()
    assert invoice.status == status
    assert invoice.issued_at == HISTORICAL_TIME
    assert invoice.is_credit_note is (status == "avoir")
    assert "aucun PDF enregistré" in output


def test_already_issued_timestamp_and_archive_are_preserved(settings):
    invoice = make_legacy_invoice(status="draft", issued=True, archived=True)
    put_pdf(settings.MEDIA_ROOT, invoice)
    before = invoice_state(invoice)
    run_command(apply=True)
    invoice.refresh_from_db()
    assert invoice_state(invoice) == before
    assert issued_invoices().filter(pk=invoice.pk).exists()


def test_year_filter_does_not_touch_other_years(settings):
    old = make_legacy_invoice(year=2025)
    recent = make_legacy_invoice(year=2026)
    put_pdf(settings.MEDIA_ROOT, old)
    put_pdf(settings.MEDIA_ROOT, recent)
    run_command(year=2025, apply=True)
    recent.refresh_from_db()
    assert recent.issued_at is None
    assert not (Path(settings.PRIVATE_MEDIA_ROOT) / recent.pdf.name).exists()
    assert issued_invoices().get().pk == old.pk


@pytest.mark.parametrize("problem", ["missing", "conflict", "invalid"])
def test_preflight_error_prevents_all_writes(settings, problem):
    valid = make_legacy_invoice()
    put_pdf(settings.MEDIA_ROOT, valid)
    bad = make_legacy_invoice()
    if problem != "missing":
        put_pdf(settings.MEDIA_ROOT, bad, b"not a PDF" if problem == "invalid" else ORIGINAL)
    if problem == "conflict":
        put_pdf(settings.PRIVATE_MEDIA_ROOT, bad, b"%PDF-1.4\nDifferent private PDF\n%%EOF")
    with pytest.raises(CommandError, match="Aucune écriture effectuée"):
        run_command(apply=True)
    assert not (Path(settings.PRIVATE_MEDIA_ROOT) / valid.pdf.name).exists()
    assert Invoice.all_objects.filter(issued_at__isnull=False).count() == 0
    assert not AccountingActivity.objects.exists()


@pytest.mark.parametrize("name", ["../invoice.pdf", "/invoice.pdf", "C:/invoice.pdf", "factures\\invoice.pdf"])
def test_unsafe_legacy_path_is_rejected(name):
    invoice = make_legacy_invoice()
    Invoice.all_objects.filter(pk=invoice.pk).update(pdf=name)
    with pytest.raises(CommandError, match="Aucune écriture effectuée"):
        run_command(apply=True)
    assert not AccountingActivity.objects.exists()


def test_existing_private_pdf_is_enough_when_old_source_is_gone(settings):
    invoice = make_legacy_invoice()
    original = put_pdf(settings.PRIVATE_MEDIA_ROOT, invoice)
    run_command(apply=True)
    assert issued_invoices().get().pk == invoice.pk
    assert original.read_bytes() == ORIGINAL


def test_custom_source_directory(settings, tmp_path):
    invoice = make_legacy_invoice()
    source = tmp_path / "backup"
    put_pdf(source, invoice)
    run_command(source_dir=str(source), apply=True)
    assert (Path(settings.PRIVATE_MEDIA_ROOT) / invoice.pdf.name).read_bytes() == ORIGINAL


def test_cloudinary_source_uses_configured_storage(settings):
    invoice = make_legacy_invoice()
    put_pdf(settings.MEDIA_ROOT, invoice)
    with patch("cloudinary_storage.storage.MediaCloudinaryStorage",
               return_value=FileSystemStorage(location=settings.MEDIA_ROOT)) as storage:
        run_command(source="cloudinary", apply=True)
    storage.assert_called_once_with()
    assert (Path(settings.PRIVATE_MEDIA_ROOT) / invoice.pdf.name).read_bytes() == ORIGINAL


@pytest.mark.parametrize("options", [{"year": 0}, {"year": 10000},
                                    {"source": "cloudinary", "source_dir": "backup"}])
def test_invalid_options_are_rejected(options):
    with pytest.raises(CommandError):
        run_command(**options)


def test_source_must_not_contain_private_destination(settings):
    with pytest.raises(CommandError, match="sans imbrication"):
        run_command(source_dir=str(Path(settings.PRIVATE_MEDIA_ROOT).parent))


def test_source_change_during_copy_never_publishes_incomplete_pdf(settings):
    invoice = make_legacy_invoice()
    original = put_pdf(settings.MEDIA_ROOT, invoice)
    source = FileSystemStorage(location=settings.MEDIA_ROOT)
    target = invoice.pdf.storage
    fingerprint = pdf_digest(source, invoice.pdf.name)
    original.write_bytes(b"%PDF-1.4\nModified since preflight\n%%EOF")
    with pytest.raises(ValueError, match="source a changé"):
        copy_verified(source, target, invoice.pdf.name, fingerprint)
    assert not target.exists(invoice.pdf.name)
    assert not list(Path(settings.PRIVATE_MEDIA_ROOT).rglob(".accounting-*"))


def test_changed_invoice_is_not_overwritten(settings):
    invoice = make_legacy_invoice()
    put_pdf(settings.MEDIA_ROOT, invoice)
    original_apply = Command.apply_recovery

    def change_before_apply(command, recovery, source, target):
        Invoice.all_objects.filter(pk=invoice.pk).update(notes="Modification concurrente")
        return original_apply(command, recovery, source, target)

    with patch.object(Command, "apply_recovery", change_before_apply), \
            pytest.raises(CommandError, match="facture a changé"):
        run_command(apply=True)
    invoice.refresh_from_db()
    assert invoice.notes == "Modification concurrente" and invoice.issued_at is None
    assert not invoice.pdf.storage.exists(invoice.pdf.name)


def test_portal_and_zip_use_recovered_original_without_regeneration(client, settings):
    invoice = make_legacy_invoice()
    put_pdf(settings.MEDIA_ROOT, invoice)
    run_command(apply=True)
    client.force_login(accountant())
    period = {"date_from": "2025-01-01", "date_to": "2025-12-31"}
    with patch.object(Invoice, "generate_pdf", side_effect=AssertionError("Original required")):
        pdf = client.get(reverse("accounting:invoice_pdf", args=[invoice.pk]))
        assert pdf.status_code == 200 and pdf.content == ORIGINAL
        listing = client.get(reverse("accounting:sales"), period)
        assert invoice.number in listing.content.decode()
        response = client.get(reverse("accounting:export"), {**period, "format": "zip"})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            name = next(name for name in archive.namelist() if name.startswith("ventes/"))
            assert archive.read(name) == ORIGINAL


def test_missing_original_does_not_silently_regenerate_or_export_partial_zip(client):
    invoice = make_legacy_invoice(issued=True)
    client.force_login(accountant())
    with patch.object(Invoice, "generate_pdf", side_effect=AssertionError("Missing original must be reported")):
        response = client.get(reverse("accounting:invoice_pdf", args=[invoice.pk]), follow=True)
        assert "Le PDF original est indisponible" in response.content.decode()
        response = client.get(reverse("accounting:export"),
                              {"format": "zip", "date_from": "2025-01-01", "date_to": "2025-12-31"})
        assert response.status_code == 302
        assert response.url == reverse("accounting:dashboard")


def test_pdf_without_historical_attachment_keeps_existing_generation():
    invoice = make_legacy_invoice(pdf=False, issued=True)
    with patch.object(Invoice, "generate_pdf", return_value=ORIGINAL) as generate:
        assert invoice_pdf_content(invoice) == ORIGINAL
    generate.assert_called_once_with(attach=False)


def test_portal_has_one_discreet_studio_credit_without_partnership_signature(client):
    client.force_login(accountant())
    html = client.get(reverse("accounting:dashboard")).content.decode()
    assert "NetExpress ×" not in html
    assert html.count("Trait d’Union Studio") == 1
    assert "Outil métier conçu par" in html
