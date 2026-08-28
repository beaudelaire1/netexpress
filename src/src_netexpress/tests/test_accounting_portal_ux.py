from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.access import confirm_email
from accounts.models import Profile
from accounting.models import AccountingExchange
from core.services import document_generator


pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(role, *, username, email):
    user = User.objects.create_user(
        username=username,
        email=email,
        password="LongSecurePassword854!",
    )
    profile = user.profile
    profile.role = role
    profile.save(update_fields=["role"])
    confirm_email(user)
    user.refresh_from_db()
    return user


def test_accountant_collaboration_entry_points_are_visible_and_legacy_message_is_migrated(client):
    make_user(
        Profile.ROLE_ADMIN_BUSINESS,
        username="netexpress-admin",
        email="admin@example.test",
    )
    accountant = make_user(
        Profile.ROLE_ACCOUNTANT,
        username="cabinet-user",
        email="cabinet@example.test",
    )
    accountant.profile.accounting_firm = "Cabinet Test"
    accountant.profile.save(update_fields=["accounting_firm"])
    client.force_login(accountant)

    dashboard = client.get(reverse("accounting:dashboard"))
    assert dashboard.status_code == 200
    html = dashboard.content.decode("utf-8")
    assert "Collaborer" in html
    assert "Nouvel échange" in html
    assert "Mettre un document à disposition" in html
    assert reverse("accounting:exchanges") in html

    response = client.post(
        reverse("accounting:message_netexpress"),
        {
            "message": "<script>alert(1)</script>\nMerci de vérifier FAC-2026-012.",
            "next": "https://evil.example/phishing",
        },
    )

    assert response.status_code == 302
    exchange = AccountingExchange.objects.get(created_by=accountant)
    assert response.url == reverse("accounting:exchange_detail", args=[exchange.pk])
    stored = exchange.messages.get().content
    assert "<script>" in stored  # texte brut stocké, jamais marqué safe
    detail = client.get(response.url).content.decode("utf-8")
    assert "<script>alert(1)</script>" not in detail
    assert "&lt;script&gt;" in detail
    assert "FAC-2026-012" in detail


def test_legacy_accounting_message_endpoint_remains_accountant_only(client):
    admin = make_user(
        Profile.ROLE_ADMIN_BUSINESS,
        username="business-admin",
        email="business@example.test",
    )
    client.force_login(admin)
    forbidden = client.post(
        reverse("accounting:message_netexpress"),
        {"message": "Test"},
    )
    assert forbidden.status_code == 403
    assert not AccountingExchange.objects.exists()


def test_accounting_layout_defines_independent_scroll_regions():
    css = (
        Path(settings.BASE_DIR) / "static" / "css" / "accounting-ux-fixes.css"
    ).read_text(encoding="utf-8")

    assert "grid-template-rows: auto minmax(0, 1fr)" in css
    assert ".acc-sidebar," in css
    assert ".acc-main" in css
    assert "overflow-y: auto" in css
    assert "overscroll-behavior: contain" in css


def test_accounting_exchange_design_uses_netexpress_palette_and_private_workspace_patterns():
    css = (
        Path(settings.BASE_DIR) / "static" / "css" / "accounting-exchanges.css"
    ).read_text(encoding="utf-8")
    base = (
        Path(settings.BASE_DIR) / "templates" / "accounting" / "base.html"
    ).read_text(encoding="utf-8")

    assert "var(--green)" in css
    assert "accounting-collab-menu" in css
    assert "exchange-document-card" in css
    assert "exchange-detail-layout" in css
    assert "Trait d’Union Studio" in base
    assert "accounting-exchanges.css" in base


def test_pdf_layout_reserves_footer_margin_and_compacts_header():
    css = (
        Path(settings.BASE_DIR) / "static" / "css" / "pdf-layout-fixes.css"
    ).read_text(encoding="utf-8")

    assert "margin: 0 0 18mm 0" in css
    assert "min-height: 28mm" in css
    assert "position: fixed" in css
    assert "bottom: -18mm" in css
    assert "height: 18mm" in css


def test_document_generator_loads_base_and_layout_stylesheets(monkeypatch):
    requested = []
    loaded = []

    def fake_find(name):
        requested.append(name)
        return f"/tmp/{name.replace('/', '-')}"

    def fake_css(*, filename, url_fetcher):
        loaded.append(filename)
        return object()

    class FakeHTML:
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, stylesheets=None):
            assert len(stylesheets) == 2
            return b"%PDF-test"

    monkeypatch.setattr(document_generator.finders, "find", fake_find)
    monkeypatch.setattr(document_generator, "CSS", fake_css)
    monkeypatch.setattr(document_generator, "HTML", FakeHTML)
    monkeypatch.setattr(
        document_generator,
        "render_to_string",
        lambda *args, **kwargs: "<html><body></body></html>",
    )

    result = document_generator.DocumentGenerator.generate_pdf(
        SimpleNamespace(number="DEV-TEST"),
        "pdf/quote_premium.html",
        "DEV",
    )

    assert requested == ["css/pdf.css", "css/pdf-layout-fixes.css"]
    assert len(loaded) == 2
    assert result.content == b"%PDF-test"
