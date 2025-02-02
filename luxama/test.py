

"""
from django.test import TestCase
from django.utils import timezone
from .models import Tache

class NotificationTestCase(TestCase):
    def test_notification_envoi_email(self):
        # Créer une tâche avec une échéance urgente
        tache = Tache.objects.create(
            titre="Test Urgence",
            description="Tâche urgente test",
            date_debut=timezone.now(),
            date_fin=timezone.now() + timezone.timedelta(days=1),
            statut=Tache.EN_ATTENTE
        )
        self.assertIn("URGENTE", tache.notification)  # Vérifier la notification
"""

from .models import Tache
from django.utils import timezone
from datetime import timedelta

# Créer une tâche de test
tache = Tache.objects.create(
    titre="Tâche de test",
    description="Ceci est une description de test.",
    statut=Tache.EN_ATTENTE,
    date_debut=timezone.now(),
    date_fin=timezone.now() + timedelta(days=1)  # La tâche doit être terminée dans 1 jour
)

# Simuler une mise à jour pour déclencher le signal
tache.statut = Tache.EN_COURS
tache.save()