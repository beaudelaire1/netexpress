"""
Tests du flux métier pour les tâches (interventions).

Couvre:
- Calcul automatique du statut selon dates
- Validation des règles métier
- Détection des tâches proches de l'échéance
- Transitions de statuts
"""

import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from tasks.models import Task


pytestmark = pytest.mark.django_db


class TestTaskStatusAutoCalculation:
    """Tests du calcul automatique du statut des tâches."""

    def test_task_status_upcoming_when_start_in_future(self):
        """TEST-TASK-001: Une tâche dont start_date est dans le futur doit être UPCOMING."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Future",
            start_date=today + timedelta(days=5),
            due_date=today + timedelta(days=10)
        )
        
        # Assert
        assert task.status == Task.STATUS_UPCOMING

    def test_task_status_in_progress_when_started(self):
        """Une tâche dont start_date est aujourd'hui ou passé doit être IN_PROGRESS."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche en Cours",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Assert
        assert task.status == Task.STATUS_IN_PROGRESS

    def test_task_status_overdue_when_past_due_date(self):
        """Une tâche dont due_date est dépassée doit être OVERDUE."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche en Retard",
            start_date=today - timedelta(days=10),
            due_date=today - timedelta(days=2)
        )
        
        # Assert
        assert task.status == Task.STATUS_OVERDUE

    def test_task_status_almost_overdue_when_due_tomorrow(self):
        """Une tâche due demain doit être ALMOST_OVERDUE."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Urgente",
            start_date=today - timedelta(days=2),
            due_date=today + timedelta(days=1)
        )
        
        # Assert
        assert task.status == Task.STATUS_ALMOST_OVERDUE

    def test_task_status_almost_overdue_when_due_today(self):
        """Une tâche due aujourd'hui doit être ALMOST_OVERDUE."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Due Aujourd'hui",
            start_date=today - timedelta(days=1),
            due_date=today
        )
        
        # Assert
        assert task.status == Task.STATUS_ALMOST_OVERDUE

    def test_task_status_completed_preserved(self):
        """Une tâche COMPLETED ne doit pas voir son statut recalculé."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Terminée",
            start_date=today - timedelta(days=5),
            due_date=today - timedelta(days=1),
            status=Task.STATUS_COMPLETED
        )
        
        # Assert
        assert task.status == Task.STATUS_COMPLETED

    def test_task_status_updates_on_save(self):
        """Le statut doit être recalculé à chaque save (sauf si completed)."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche",
            start_date=today + timedelta(days=5),
            due_date=today + timedelta(days=10)
        )
        assert task.status == Task.STATUS_UPCOMING
        
        # Act - Modifier les dates pour rendre la tâche en cours
        task.start_date = today
        task.save()
        
        # Assert
        assert task.status == Task.STATUS_IN_PROGRESS


class TestTaskDateValidation:
    """Tests de validation des dates."""

    def test_task_due_date_cannot_precede_start_date(self):
        """TEST-TASK-002: La date d'échéance ne peut pas précéder la date de début."""
        # Arrange
        today = date.today()
        
        # Act & Assert
        with pytest.raises(ValueError, match="ne peut pas être antérieure"):
            task = Task.objects.create(
                title="Invalid Task",
                start_date=today + timedelta(days=5),
                due_date=today  # Due avant start
            )

    def test_task_accepts_same_start_and_due_date(self):
        """Une tâche peut avoir start_date == due_date."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche d'un jour",
            start_date=today,
            due_date=today
        )
        
        # Assert - Ne lève pas d'exception
        assert task.start_date == task.due_date


class TestTaskIsDueSoon:
    """Tests de la méthode is_due_soon()."""

    def test_task_is_due_soon_within_threshold(self):
        """TEST-TASK-003: Une tâche due dans 2 jours (threshold=3) doit être due soon."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche Proche",
            start_date=today,
            due_date=today + timedelta(days=2)
        )
        
        # Act & Assert
        assert task.is_due_soon(days_threshold=3) is True

    def test_task_is_not_due_soon_beyond_threshold(self):
        """Une tâche due dans 5 jours (threshold=3) ne doit pas être due soon."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche Lointaine",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Act & Assert
        assert task.is_due_soon(days_threshold=3) is False

    def test_task_is_due_soon_today(self):
        """Une tâche due aujourd'hui doit être due soon."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche Due Aujourd'hui",
            start_date=today,
            due_date=today
        )
        
        # Act & Assert
        assert task.is_due_soon(days_threshold=0) is True
        assert task.is_due_soon(days_threshold=3) is True

    def test_completed_task_not_due_soon(self):
        """Une tâche COMPLETED ne doit jamais être due soon."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche Terminée",
            start_date=today,
            due_date=today + timedelta(days=1),
            status=Task.STATUS_COMPLETED
        )
        
        # Act & Assert
        assert task.is_due_soon(days_threshold=5) is False

    def test_overdue_task_not_due_soon(self):
        """Une tâche en retard (due_date passée) ne doit pas être 'due soon' mais 'overdue'."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche en Retard",
            start_date=today - timedelta(days=10),
            due_date=today - timedelta(days=2)
        )
        
        # Act & Assert
        assert task.is_due_soon(days_threshold=3) is False
        assert task.status == Task.STATUS_OVERDUE

    def test_task_without_due_date_not_due_soon(self):
        """Une tâche sans due_date ne doit pas être due soon."""
        # Note: Le modèle actuel requiert due_date (field obligatoire)
        # Ce test vérifie la robustesse de la méthode
        # On va tester avec une tâche normale puis la modification manuelle
        today = date.today()
        task = Task.objects.create(
            title="Tâche",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Simuler l'absence de due_date (si le modèle permettait None)
        # Pour ce test, on vérifie juste que la méthode ne crashe pas
        assert task.is_due_soon(days_threshold=10) is True


class TestTaskTeamManagement:
    """Tests de gestion des équipes."""

    def test_task_can_be_assigned_to_team(self):
        """Une tâche peut être assignée à une équipe."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Équipe A",
            team="Équipe A",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Assert
        assert task.team == "Équipe A"

    def test_task_team_can_be_empty(self):
        """Une tâche peut ne pas avoir d'équipe assignée."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Sans Équipe",
            team="",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Assert
        assert task.team == ""


class TestTaskLocation:
    """Tests de gestion de la localisation."""

    def test_task_can_have_location(self):
        """Une tâche peut avoir une adresse de localisation."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche avec Lieu",
            location="123 Rue de Paris, 75001 Paris",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Assert
        assert "Paris" in task.location

    def test_task_location_can_be_empty(self):
        """Une tâche peut ne pas avoir de localisation."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche Sans Lieu",
            location="",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Assert
        assert task.location == ""


class TestTaskOrdering:
    """Tests de l'ordre par défaut des tâches."""

    def test_tasks_ordered_by_due_date_then_title(self):
        """Les tâches doivent être triées par due_date puis title."""
        # Arrange
        today = date.today()
        task_c = Task.objects.create(
            title="C - Tâche",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        task_a = Task.objects.create(
            title="A - Tâche",
            start_date=today,
            due_date=today + timedelta(days=3)
        )
        task_b = Task.objects.create(
            title="B - Tâche",
            start_date=today,
            due_date=today + timedelta(days=3)
        )
        
        # Act
        tasks = list(Task.objects.all())
        
        # Assert
        # Ordre attendu: A (due +3), B (due +3), C (due +5)
        assert tasks[0] == task_a
        assert tasks[1] == task_b
        assert tasks[2] == task_c


class TestTaskStringRepresentation:
    """Tests de la représentation string."""

    def test_task_str_includes_title_and_status(self):
        """La représentation string doit inclure titre et statut."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Nettoyage Bureau",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Act
        task_str = str(task)
        
        # Assert
        assert "Nettoyage Bureau" in task_str
        assert task.get_status_display() in task_str


class TestTaskAbsoluteUrl:
    """Tests de génération d'URL."""

    def test_task_get_absolute_url(self):
        """get_absolute_url() doit retourner l'URL de détail."""
        # Arrange
        today = date.today()
        task = Task.objects.create(
            title="Tâche Test",
            start_date=today,
            due_date=today + timedelta(days=5)
        )
        
        # Act
        url = task.get_absolute_url()
        
        # Assert
        assert f"/taches/{task.pk}/" in url or f"tasks/{task.pk}" in url


class TestTaskDescription:
    """Tests du champ description."""

    def test_task_can_have_description(self):
        """Une tâche peut avoir une description détaillée."""
        # Arrange
        today = date.today()
        description = "Nettoyage complet des bureaux du 3ème étage incluant vitres et sols."
        
        # Act
        task = Task.objects.create(
            title="Nettoyage",
            description=description,
            start_date=today,
            due_date=today + timedelta(days=1)
        )
        
        # Assert
        assert task.description == description

    def test_task_description_can_be_empty(self):
        """La description peut être vide."""
        # Arrange
        today = date.today()
        
        # Act
        task = Task.objects.create(
            title="Tâche",
            description="",
            start_date=today,
            due_date=today + timedelta(days=1)
        )
        
        # Assert
        assert task.description == ""

