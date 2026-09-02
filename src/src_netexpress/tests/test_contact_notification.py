"""
Le formulaire de contact doit réellement prévenir le gestionnaire.

Ces tests couvrent la régression qui a motivé leur écriture : la notification
partait dans une file Celery sans worker, et son échec était avalé
silencieusement — le message arrivait en base, personne n'était prévenu.
"""

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

from contact.models import Message
from contact.tasks import send_contact_notification


VALID_PAYLOAD = {
    "topic": "peinture",
    "full_name": "Jeanne Dupont",
    "email": "jeanne@exemple.fr",
    "phone": "0694000000",
    "street": "12 rue des Palmiers",
    "city": "Cayenne",
    "zip_code": "97300",
    "body": "Bonjour, je souhaite un devis pour repeindre un local.",
}


@pytest.mark.django_db
def test_le_formulaire_envoie_la_notification_au_gestionnaire(settings):
    settings.CONTACT_RECEIVER_EMAIL = "gestion@exemple.fr"
    settings.CONTACT_CC_EMAIL = "copie@exemple.fr"
    settings.DEFAULT_FROM_EMAIL = "contact@exemple.fr"

    response = Client().post(reverse("contact:contact"), VALID_PAYLOAD)

    assert response.status_code == 302
    assert Message.objects.count() == 1

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["gestion@exemple.fr"]
    assert sent.cc == ["copie@exemple.fr"]
    # Répondre au courriel doit écrire au demandeur, pas à la boîte d'envoi.
    assert sent.reply_to == ["jeanne@exemple.fr"]
    assert "Jeanne Dupont" in sent.subject
    # Un corps texte et une alternative HTML : le message reste lisible partout.
    assert "Jeanne Dupont" in sent.body
    assert any(mimetype == "text/html" for _, mimetype in sent.alternatives)


@pytest.mark.django_db
def test_sans_destinataire_configure_rien_n_est_envoye_mais_c_est_journalise(settings, caplog):
    settings.CONTACT_RECEIVER_EMAIL = ""
    settings.DEFAULT_FROM_EMAIL = ""

    msg = Message.objects.create(**VALID_PAYLOAD)
    send_contact_notification(msg.pk)

    assert mail.outbox == []
    assert "non notifié" in caplog.text


@pytest.mark.django_db
def test_un_echec_d_envoi_n_empeche_pas_la_confirmation_du_visiteur(settings, monkeypatch, caplog):
    settings.CONTACT_RECEIVER_EMAIL = "gestion@exemple.fr"

    def relais_injoignable(*args, **kwargs):
        raise ConnectionRefusedError("relais SMTP injoignable")

    monkeypatch.setattr(
        "django.core.mail.EmailMultiAlternatives.send", relais_injoignable
    )

    response = Client().post(reverse("contact:contact"), VALID_PAYLOAD)

    # Le message est enregistré : le visiteur n'a pas à ressaisir sa demande
    # parce que notre relais est en panne.
    assert response.status_code == 302
    assert Message.objects.count() == 1
    assert "Échec de l'envoi de la notification" in caplog.text


@pytest.mark.django_db
def test_la_page_de_confirmation_affiche_la_reference_une_seule_fois(settings):
    settings.CONTACT_RECEIVER_EMAIL = "gestion@exemple.fr"
    client = Client()

    client.post(reverse("contact:contact"), VALID_PAYLOAD)
    reference = f"MSG-{Message.objects.get().pk:05d}"

    first = client.get(reverse("contact:success"))
    assert reference in first.content.decode()
    assert "Jeanne" in first.content.decode()

    # Rechargée, la page reste valide mais n'affiche plus un accusé périmé.
    second = client.get(reverse("contact:success"))
    assert second.status_code == 200
    assert reference not in second.content.decode()
