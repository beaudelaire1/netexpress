from __future__ import annotations

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Profil utilisateur (rôle + infos) pour l'ERP.

    Rôles:
      - client : accès au dashboard client (/client/)
      - worker : accès au dashboard ouvrier (/worker/)
      - admin_business : accès au dashboard admin business (/admin-dashboard/) + lecture /gestion/
      - admin_technical : accès à l'interface technique Django Admin (/gestion/)
    
    IMPORTANT: Le rôle définit les permissions et l'accès aux portails.
    Les signaux dans accounts/signals.py gèrent la création automatique du profil
    et la synchronisation des permissions.
    """

    ROLE_ACCOUNTANT = "accountant"
    ROLE_CLIENT = "client"
    ROLE_WORKER = "worker"
    ROLE_ADMIN_BUSINESS = "admin_business"
    ROLE_ADMIN_TECHNICAL = "admin_technical"

    ROLE_CHOICES = [
        (ROLE_ACCOUNTANT, "Comptable"),
        (ROLE_CLIENT, "Client"),
        (ROLE_WORKER, "Ouvrier"),
        (ROLE_ADMIN_BUSINESS, "Administrateur Business"),
        (ROLE_ADMIN_TECHNICAL, "Administrateur Technique"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    client = models.ForeignKey("devis.Client", null=True, blank=True, on_delete=models.SET_NULL, related_name="portal_profiles")
    verified_email = models.EmailField(blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    accounting_firm = models.CharField("Cabinet comptable", max_length=200, blank=True)

    @property
    def has_verified_email(self):
        return bool(self.email_verified_at and self.verified_email and
                    self.verified_email.casefold() == self.user.email.strip().casefold())

    phone = models.CharField(max_length=50, blank=True)
    
    # Force password change on first login
    force_password_change = models.BooleanField(
        default=False,
        help_text="Si True, l'utilisateur doit changer son mot de passe à la prochaine connexion"
    )
    
    # New fields for portal functionality
    last_portal_access = models.DateTimeField(null=True, blank=True, help_text="Last time user accessed their portal")
    notification_preferences = models.JSONField(
        default=dict, 
        blank=True,
        help_text="User preferences for email and UI notifications"
    )

    class Meta:
        verbose_name = "profil"
        verbose_name_plural = "profils"
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"
    
    def save(self, *args, **kwargs):
        """Override save to trigger permission sync after role change."""
        super().save(*args, **kwargs)
        # Note: La synchronisation des permissions est gérée par le signal post_save


# Note: Le signal de création de profil est maintenant dans accounts/signals.py
# pour une gestion centralisée des permissions
