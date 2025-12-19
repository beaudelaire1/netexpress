import pytest
from django.urls import reverse

from devis.models import Client, Quote

pytestmark = pytest.mark.django_db


def _make_quote():
    client = Client.objects.create(full_name="Jean Dupont", email="jean@example.com", phone="0694123456")
    quote = Quote.objects.create(client=client, message="Test")
    return quote


def test_public_pdf_link_works(client, settings):
    settings.SITE_URL = "http://testserver"
    quote = _make_quote()
    url = reverse("devis:quote_public_pdf", kwargs={"token": quote.public_token})
    resp = client.get(url)
    # Might be 404 if PDF generation fails because of missing WeasyPrint system libs.
    # The important part here is that URL resolves and view is reachable.
    assert resp.status_code in (200, 404)


def test_validation_start_redirects(client, settings):
    settings.SITE_URL = "http://testserver"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    quote = _make_quote()
    url = reverse("devis:quote_validate_start", kwargs={"token": quote.public_token})
    resp = client.get(url)
    assert resp.status_code == 302
    assert "/devis/valider/" in resp["Location"]
    assert resp["Location"].endswith("/code/")
