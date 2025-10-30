"""
Modèles pour les demandes de devis client (app ``quotes``).

Un devis représente la demande d’un client potentiel pour une estimation
de prix concernant un service particulier.  Les données sont stockées
pour un suivi ultérieur par l’équipe commerciale et pourront être
transformées en facture une fois acceptées.  Depuis 2025, un numéro de
téléphone est obligatoire et les modèles ont été simplifiés pour
faciliter l’intégration dans des projets existants.  Le libellé
"service" est libre afin de couvrir des demandes personnalisées.  Les
pages associées à ces modèles utilisent des images libres de droits
dans leur mise en page【668280112401708†L16-L63】.
"""

from django.db import models


class Quote(models.Model):
    STATUS_CHOICES = [
        ("new", "Nouveau"),
        ("in_progress", "En cours"),
        ("completed", "Terminé"),
        ("rejected", "Rejeté"),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    service = models.CharField(max_length=200, blank=True, help_text="Service demandé")
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "demande de devis"
        verbose_name_plural = "demandes de devis"

    def __str__(self) -> str:
        return f"Devis de {self.name} pour {self.service or 'Service personnalisé'}"