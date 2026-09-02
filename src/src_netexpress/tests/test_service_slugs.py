"""Les slugs doivent rester joignables par la route de détail.

La route utilise le convertisseur ``<slug:…>`` de Django, limité à
``[-a-zA-Z0-9_]+``. Un slug accentué s'enregistre sans broncher, mais rend la
fiche inaccessible *et* fait échouer le ``{% url %}`` de la page de liste — donc
une 500 sur l'ensemble du catalogue, pas seulement sur la fiche fautive.

En français, un titre sans accent est l'exception : ce cas se serait produit à
la première prestation créée depuis l'administration.
"""

from __future__ import annotations

import re

import pytest
from django.urls import reverse

from services.models import Category, Service

# Le motif du convertisseur `slug` de Django.
SLUG_AUTORISE = re.compile(r"^[-a-zA-Z0-9_]+$")


@pytest.fixture
def categorie(db) -> Category:
    return Category.objects.create(name="Espaces verts")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "titre",
    [
        "Débroussaillage de terrain",
        "Évacuation de déchets verts",
        "Élagage et abattage léger",
        "Peinture extérieure et façade",
        "Traitement anti-moisissure",
    ],
)
def test_un_titre_accentue_produit_un_slug_joignable(categorie: Category, titre: str):
    service = Service.objects.create(title=titre, category=categorie)

    assert SLUG_AUTORISE.match(service.slug), (
        f"{titre!r} produit le slug {service.slug!r}, que la route rejette."
    )
    # reverse() est ce qui échouait en production, depuis la page de liste.
    assert reverse("services:detail", kwargs={"slug": service.slug})


@pytest.mark.django_db
def test_une_categorie_accentuee_produit_un_slug_ascii():
    categorie = Category.objects.create(name="Rénovation intérieure")

    assert SLUG_AUTORISE.match(categorie.slug)


@pytest.mark.django_db
def test_les_titres_voisins_restent_distincts(categorie: Category):
    """Retirer les accents rapproche des titres jusque-là distincts."""
    premier = Service.objects.create(title="Réparation", category=categorie)
    second = Service.objects.create(title="Reparation", category=categorie)

    assert premier.slug != second.slug
    assert SLUG_AUTORISE.match(second.slug)


@pytest.mark.django_db
def test_la_page_de_liste_se_rend_avec_des_titres_accentues(client, categorie: Category):
    """Reproduit la 500 : la liste construit une URL par prestation."""
    Service.objects.create(title="Débroussaillage de terrain", category=categorie)

    reponse = client.get(reverse("services:list"))

    assert reponse.status_code == 200
