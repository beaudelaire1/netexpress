"""Activer ou retirer une prestation du site, depuis l'administration.

Une prestation retirée doit disparaître de la liste publique *et* de sa fiche,
sans que rien ne soit supprimé : les devis déjà établis référencent ces
prestations et doivent rester intacts.
"""

from __future__ import annotations

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from services.admin import ServiceAdmin
from services.models import Category, Service


@pytest.fixture
def categorie(db) -> Category:
    return Category.objects.create(name="Nettoyage")


@pytest.fixture
def administration() -> ServiceAdmin:
    return ServiceAdmin(Service, AdminSite())


@pytest.fixture
def requete(rf):
    """Requête munie du support des messages, exigé par message_user()."""
    from django.contrib.messages.storage.fallback import FallbackStorage

    demande = rf.post("/")
    setattr(demande, "session", {})
    setattr(demande, "_messages", FallbackStorage(demande))
    return demande


@pytest.mark.django_db
def test_desactiver_retire_de_la_liste_publique(client, categorie: Category):
    visible = Service.objects.create(title="Nettoyage de vitres", category=categorie)
    retiree = Service.objects.create(
        title="Nettoyage de fin de chantier", category=categorie, is_active=False
    )

    contenu = client.get(reverse("services:list")).content.decode()

    assert visible.title in contenu
    assert retiree.title not in contenu


@pytest.mark.django_db
def test_la_fiche_d_une_prestation_retiree_repond_404(client, categorie: Category):
    retiree = Service.objects.create(
        title="Nettoyage de bureaux", category=categorie, is_active=False
    )

    reponse = client.get(reverse("services:detail", kwargs={"slug": retiree.slug}))

    assert reponse.status_code == 404


@pytest.mark.django_db
def test_l_action_desactiver_ne_supprime_rien(
    administration: ServiceAdmin, requete, categorie: Category
):
    service = Service.objects.create(title="Nettoyage haute pression", category=categorie)

    administration.desactiver(requete, Service.objects.filter(pk=service.pk))

    service.refresh_from_db()
    assert service.is_active is False
    assert Service.objects.filter(pk=service.pk).exists(), "la prestation a été supprimée"


@pytest.mark.django_db
def test_l_action_activer_remet_en_ligne(
    administration: ServiceAdmin, requete, categorie: Category
):
    service = Service.objects.create(
        title="Entretien de parties communes", category=categorie, is_active=False
    )

    administration.activer(requete, Service.objects.filter(pk=service.pk))

    service.refresh_from_db()
    assert service.is_active is True


@pytest.mark.django_db
def test_la_bascule_est_editable_depuis_la_liste(administration: ServiceAdmin):
    """Le but de la demande : basculer sans ouvrir chaque fiche."""
    assert "is_active" in administration.list_editable
    assert "is_active" in administration.list_display
    # Django refuse qu'un champ éditable occupe la première colonne, qui porte
    # le lien d'édition : cette contrainte doit rester respectée.
    assert administration.list_display[0] != "is_active"
