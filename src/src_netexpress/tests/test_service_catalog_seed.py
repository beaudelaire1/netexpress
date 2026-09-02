"""La commande de catalogue doit pouvoir être rejouée en production sans dégât.

Elle sera lancée sur la base réelle, éventuellement plusieurs fois — après une
correction de libellé, ou par prudence. Les cas ci-dessous éprouvent surtout ce
qu'un second passage ne doit pas faire : dupliquer, ou empiler les tâches.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from services.management.commands.seed_service_catalog import CATALOGUE
from services.models import Category, Service, ServiceTask

NOMBRE_ATTENDU_DE_SERVICES = sum(len(bloc["services"]) for bloc in CATALOGUE)


def executer(**options) -> str:
    sortie = StringIO()
    call_command("seed_service_catalog", stdout=sortie, **options)
    return sortie.getvalue()


@pytest.mark.django_db
def test_le_catalogue_est_cree():
    executer()

    assert Category.objects.count() == len(CATALOGUE)
    assert Service.objects.count() == NOMBRE_ATTENDU_DE_SERVICES
    assert set(Category.objects.values_list("slug", flat=True)) == {
        bloc["slug"] for bloc in CATALOGUE
    }


@pytest.mark.django_db
def test_rejouer_ne_duplique_rien():
    executer()
    taches_premier_passage = ServiceTask.objects.count()

    executer()

    assert Category.objects.count() == len(CATALOGUE)
    assert Service.objects.count() == NOMBRE_ATTENDU_DE_SERVICES
    # Les tâches sont réécrites, pas empilées : c'est la régression la plus
    # probable, puisqu'elles n'ont pas de clé d'unicité en base.
    assert ServiceTask.objects.count() == taches_premier_passage


@pytest.mark.django_db
def test_la_simulation_n_ecrit_rien():
    sortie = executer(dry_run=True)

    assert Category.objects.count() == 0
    assert Service.objects.count() == 0
    assert "rien n'a été enregistré" in sortie


@pytest.mark.django_db
def test_chaque_service_est_exploitable_pour_un_devis():
    """Un service sans unité ni description ne sert à rien au moment de chiffrer."""
    executer()

    for service in Service.objects.all():
        assert service.is_active
        assert service.slug, f"{service.title} n'a pas de slug"
        assert service.unit_type, f"{service.title} n'a pas d'unité"
        assert service.short_description, f"{service.title} n'a pas de description courte"
        assert service.duration_minutes > 0, f"{service.title} n'a pas de durée"
        assert service.tasks.exists(), f"{service.title} n'a aucune tâche"


@pytest.mark.django_db
def test_les_taches_sont_ordonnees_sans_trou():
    executer()

    for service in Service.objects.all():
        rangs = list(service.tasks.values_list("order", flat=True))
        assert rangs == list(range(1, len(rangs) + 1)), (
            f"Ordre des tâches incohérent pour {service.title} : {rangs}"
        )


@pytest.mark.django_db
def test_un_libelle_corrige_est_repercute():
    """Le cas d'usage réel d'un second passage : corriger un texte."""
    executer()
    service = Service.objects.get(title="Nettoyage de vitres")
    service.short_description = "texte obsolète"
    service.save(update_fields=["short_description"])

    executer()

    service.refresh_from_db()
    assert service.short_description != "texte obsolète"
