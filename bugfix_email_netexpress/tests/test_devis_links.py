import pytest
from django.urls import reverse
from devis.models import Client, Quote

pytestmark = pytest.mark.django_db


def test_quote_public_pdf_url_resolves(client):
    c = Client.objects.create(full_name="Jean Dupont", email="jean@example.com", phone="0694462012")
    q = Quote.objects.create(client=c)
    url = reverse('devis:quote_public_pdf', kwargs={'token': q.public_token})
    resp = client.get(url)
    # PDF may not exist yet -> should still respond (generate) or redirect/file
    assert resp.status_code in (200, 302)


def test_quote_validation_flow_urls_resolve(client):
    c = Client.objects.create(full_name="Jean Dupont", email="jean@example.com", phone="0694462012")
    q = Quote.objects.create(client=c)

    start_url = reverse('devis:quote_validate_start', kwargs={'token': q.public_token})
    resp = client.get(start_url)
    # should redirect to code entry
    assert resp.status_code == 302
    assert '/code/' in resp['Location']
