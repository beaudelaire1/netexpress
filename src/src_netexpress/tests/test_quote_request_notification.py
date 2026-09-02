"""
Le formulaire public de demande de devis doit prévenir quelqu'un.

Régression couverte : la tâche `send_quote_request_received` existait mais
n'était appelée nulle part. Une demande déposée depuis le site n'envoyait donc
ni accusé de réception au client, ni notification au gestionnaire.
"""

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

from devis.models import QuoteRequest
from devis.tasks import send_quote_request_notification


VALID_PAYLOAD = {
    "client_name": "Marc Antoine",
    "email": "marc@exemple.fr",
    "phone": "0694111111",
    "address": "5 avenue du Général de Gaulle, 97300 Cayenne",
    "service_type": "renovation",
    "surface": "120",
    "deadline": "express",
    "message": "Rafraîchir les peintures d'un local commercial.",
}


@pytest.mark.django_db
def test_le_formulaire_notifie_le_client_et_le_gestionnaire(settings):
    settings.TASK_NOTIFICATION_EMAIL = "gestion@exemple.fr"
    settings.DEFAULT_FROM_EMAIL = "contact@exemple.fr"

    response = Client().post(reverse("devis:request_quote"), VALID_PAYLOAD)

    assert response.status_code == 302
    assert QuoteRequest.objects.count() == 1

    destinataires = [adresse for message in mail.outbox for adresse in message.to]
    assert "marc@exemple.fr" in destinataires, "accusé de réception au demandeur"
    assert "gestion@exemple.fr" in destinataires, "notification au gestionnaire"

    interne = next(m for m in mail.outbox if m.to == ["gestion@exemple.fr"])
    reference = f"REQ-{QuoteRequest.objects.get().pk:05d}"
    assert reference in interne.subject
    # Le récapitulatif lit les champs réels du modèle : les anciens libellés
    # pointaient sur des attributs inexistants et restaient vides.
    assert "Rénovation" in interne.body
    assert "120 m²" in interne.body
    assert interne.reply_to == ["marc@exemple.fr"]


@pytest.mark.django_db
def test_sans_destinataire_interne_le_client_est_quand_meme_confirme(settings, caplog):
    settings.TASK_NOTIFICATION_EMAIL = ""

    demande = QuoteRequest.objects.create(
        client_name="Marc Antoine",
        email="marc@exemple.fr",
        phone="0694111111",
        address="5 avenue du Général de Gaulle",
    )
    send_quote_request_notification(demande.pk)

    assert [m.to for m in mail.outbox] == [["marc@exemple.fr"]]
    assert "non notifiée" in caplog.text


@pytest.mark.django_db
def test_un_echec_d_envoi_n_empeche_pas_l_enregistrement_de_la_demande(settings, monkeypatch, caplog):
    settings.TASK_NOTIFICATION_EMAIL = "gestion@exemple.fr"

    def relais_injoignable(*args, **kwargs):
        raise ConnectionRefusedError("relais SMTP injoignable")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", relais_injoignable)

    response = Client().post(reverse("devis:request_quote"), VALID_PAYLOAD)

    assert response.status_code == 302
    assert QuoteRequest.objects.count() == 1
    assert "Échec de l'envoi de la notification" in caplog.text


@pytest.mark.django_db
def test_la_page_de_confirmation_affiche_la_reference_une_seule_fois(settings):
    settings.TASK_NOTIFICATION_EMAIL = "gestion@exemple.fr"
    client = Client()

    client.post(reverse("devis:request_quote"), VALID_PAYLOAD)
    reference = f"REQ-{QuoteRequest.objects.get().pk:05d}"

    premiere = client.get(reverse("devis:quote_success"))
    contenu = premiere.content.decode()
    assert reference in contenu
    assert "Marc" in contenu
    assert "Rénovation" in contenu

    seconde = client.get(reverse("devis:quote_success"))
    assert seconde.status_code == 200
    assert reference not in seconde.content.decode()
