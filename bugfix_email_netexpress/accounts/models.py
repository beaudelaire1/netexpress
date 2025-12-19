from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Profil utilisateur (rôle + infos) pour l'ERP.

    Rôles:
      - client : accès au dashboard client
      - worker : accès au dashboard ouvrier
      - staff/admin : utilise l'admin Django et le dashboard interne
    """

    ROLE_CLIENT = "client"
    ROLE_WORKER = "worker"
    ROLE_TEAM = "team"

    ROLE_CHOICES = [
        (ROLE_CLIENT, "Client"),
        (ROLE_WORKER, "Ouvrier"),
        (ROLE_TEAM, "Équipe"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    phone = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "profil"
        verbose_name_plural = "profils"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
