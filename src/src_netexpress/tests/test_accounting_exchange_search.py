import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.access import confirm_email
from accounts.models import Profile
from accounting.models import AccountingExchange

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_accountant(username="search-accountant"):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="LongSecurePassword854!",
    )
    profile = user.profile
    profile.role = Profile.ROLE_ACCOUNTANT
    profile.accounting_firm = "Cabinet Recherche"
    profile.save(update_fields=["role", "accounting_firm"])
    confirm_email(user)
    user.refresh_from_db()
    return user


def test_accounting_shell_exposes_global_search_and_list_filters(client):
    accountant = make_accountant()
    client.force_login(accountant)

    dashboard = client.get(reverse("accounting:dashboard"))
    assert dashboard.status_code == 200
    html = dashboard.content.decode("utf-8")
    assert reverse("accounting:search") in html
    assert "Rechercher dans tout l’espace comptable" in html

    sales = client.get(reverse("accounting:sales"))
    assert sales.status_code == 200
    html = sales.content.decode("utf-8")
    assert 'class="accounting-filterbar"' in html
    assert 'type="search" name="q"' in html
    assert 'name="date_from"' in html
    assert 'name="date_to"' in html


def test_unified_search_finds_accounting_exchange_content(client):
    accountant = make_accountant("exchange-searcher")
    exchange = AccountingExchange.objects.create(
        subject="Régularisation TVA août 2026",
        kind=AccountingExchange.Kind.QUESTION,
        created_by=accountant,
    )
    client.force_login(accountant)

    response = client.get(
        reverse("accounting:search"),
        {"q": "TVA août", "scope": "exchanges"},
    )

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert exchange.subject in html
    assert '<p class="eyebrow">COLLABORATION</p>' in html
    assert '<p class="eyebrow">VENTES</p>' not in html


def test_unified_search_rejects_inverted_date_range(client):
    accountant = make_accountant("date-searcher")
    client.force_login(accountant)

    response = client.get(
        reverse("accounting:search"),
        {"date_from": "2026-09-30", "date_to": "2026-09-01"},
    )

    assert response.status_code == 200
    assert "La date de début doit précéder la date de fin." in response.content.decode("utf-8")
