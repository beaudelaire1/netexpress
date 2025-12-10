"""Tests unitaires pour les modèles étendus de NetExpress.

Ce module utilise ``pytest`` et ``pytest-django`` pour vérifier
le bon fonctionnement des méthodes utilitaires ajoutées aux modèles
``Category`` et ``Task``.  Les tests couvrent :

* La génération correcte d'URL via ``get_absolute_url`` pour les
  catégories et les tâches.
* Le calcul de l'état « à échéance proche » pour les tâches via
  ``is_due_soon``.

Assurez-vous d'avoir installé ``pytest`` et ``pytest-django`` dans
votre environnement de développement (voir ``requirements/dev.txt``).
"""

import datetime

import pytest
from django.urls import reverse

from services.models import Category
from tasks.models import Task


pytestmark = pytest.mark.django_db


def test_category_get_absolute_url() -> None:
    """La méthode ``get_absolute_url`` doit générer une URL avec le slug."""
    cat = Category.objects.create(slug="peinture", name="Peinture")
    url = cat.get_absolute_url()
    # L'URL de base est celle de la liste des services
    base = reverse("services:list")
    assert url.startswith(base)
    assert f"category={cat.slug}" in url


def test_task_get_absolute_url() -> None:
    """``Task.get_absolute_url`` doit retourner l'URL du détail."""
    today = datetime.date.today()
    task = Task.objects.create(
        title="Tondre la pelouse",
        due_date=today + datetime.timedelta(days=5),
    )
    expected = reverse("tasks:detail", kwargs={"pk": task.pk})
    assert task.get_absolute_url() == expected


@pytest.mark.parametrize(
    "start_offset,due_offset,threshold,expected",
    [
        (0, 0, 0, True),          # due today, threshold 0 -> due soon
        (0, 2, 3, True),          # due in 2 days, threshold 3 -> due soon
        (0, 5, 3, False),         # due in 5 days, threshold 3 -> not soon
        (0, -1, 3, False),        # overdue tasks are not considered due soon
    ],
)
def test_task_is_due_soon(start_offset: int, due_offset: int, threshold: int, expected: bool) -> None:
    """Vérifie le calcul de l'indicateur ``is_due_soon`` selon diverses situations."""
    today = datetime.date.today()
    task = Task(
        title="Préparer le chantier",
        start_date=today + datetime.timedelta(days=start_offset),
        due_date=today + datetime.timedelta(days=due_offset),
    )
    # Définir un statut qui n'est pas 'completed' pour prendre en compte la logique
    if due_offset < 0:
        task.status = Task.STATUS_OVERDUE
    else:
        task.status = Task.STATUS_IN_PROGRESS
    assert task.is_due_soon(threshold) is expected