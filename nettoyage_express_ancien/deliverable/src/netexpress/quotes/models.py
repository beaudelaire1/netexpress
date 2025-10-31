"""
Models for customer quote requests.

A quote represents a prospective client asking for a price estimation for a
particular service.  Quote data is stored for follow‑up by the sales team and
may later be converted into an invoice once accepted.
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