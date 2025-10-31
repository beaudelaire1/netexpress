"""Modèles de l'app ``messaging``.

``EmailMessage`` représente un message e‑mail stocké dans la base
de données.  Il permet de conserver un historique des e‑mails
envoyés (ou en attente d'envoi) avec le destinataire, le sujet,
le corps, une éventuelle pièce jointe et l'état d'envoi.  La méthode
``send`` encapsule la logique d'envoi via le service SMTP défini dans
``tasks.services.EmailNotificationService``.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

try:
    # Importer le service d'envoi depuis l'application des tâches.  La
    # dépendance est optionnelle : si l'application ``tasks`` est
    # supprimée ou non installée, l'envoi échouera proprement.
    from tasks.services import EmailNotificationService  # type: ignore
except Exception:
    EmailNotificationService = None  # type: ignore


class EmailMessage(models.Model):
    """Message e‑mail générique avec gestion d'état et envoi.

    Les adresses de destinataires (``to``) et de copie (``cc``)
    acceptent plusieurs entrées séparées par des virgules.  Les
    notifications sont envoyées individuellement à chaque adresse
    via le service SMTP configuré.
    """

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Brouillon"),
        (STATUS_SENT, "Envoyé"),
        (STATUS_FAILED, "Échec"),
    ]

    recipient = models.CharField(
        max_length=500,
        help_text="Adresse(s) e‑mail des destinataires, séparées par des virgules."
    )
    cc = models.CharField(
        max_length=500,
        blank=True,
        help_text="Adresses e‑mail en copie carbone, séparées par des virgules."
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    attachment = models.FileField(
        upload_to="messages/attachments",
        blank=True,
        null=True,
        help_text="Fichier à joindre au message, facultatif."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "message envoyé"
        verbose_name_plural = "messages envoyés"

    def __str__(self) -> str:
        return f"{self.subject} → {self.recipient}"

    def send(self) -> None:
        """Envoyer le message via le service SMTP.

        Si l'envoi réussit pour tous les destinataires, le statut est
        mis à ``sent`` et ``sent_at`` est renseigné.  En cas d'erreur,
        le statut passe à ``failed`` et l'exception est enregistrée
        dans ``error_message``.  Les messages déjà envoyés ne sont
        pas renvoyés.
        """
        # Ne rien faire si le message est déjà envoyé ou en échec
        if self.status == self.STATUS_SENT:
            return
        if EmailNotificationService is None:
            self.status = self.STATUS_FAILED
            self.error_message = "Service d'e‑mail indisponible."
            self.save(update_fields=["status", "error_message"])
            return
        attachments: list[tuple[str, bytes]] = []
        if self.attachment:
            # Lire le fichier joint pour le transférer au service SMTP
            try:
                content = self.attachment.read()
                attachments.append((self.attachment.name.rsplit("/", 1)[-1], content))
            except Exception:
                pass
        # Regrouper toutes les adresses (to + cc), en supprimant les espaces et doublons
        to_addresses = [addr.strip() for addr in self.recipient.split(",") if addr.strip()]
        cc_addresses = [addr.strip() for addr in self.cc.split(",") if addr.strip()]
        all_addresses = []
        for addr in to_addresses + cc_addresses:
            if addr and addr not in all_addresses:
                all_addresses.append(addr)
        # Envoyer l'e‑mail à chaque destinataire individuellement
        send_errors: list[str] = []
        for to_addr in all_addresses:
            try:
                EmailNotificationService.send(
                    to_email=to_addr,
                    subject=self.subject,
                    body=self.body,
                    attachments=attachments or None,
                )
            except Exception as exc:
                send_errors.append(f"{to_addr}: {exc}")
        # Mise à jour du statut et du timestamp
        if send_errors:
            self.status = self.STATUS_FAILED
            self.error_message = "; ".join(send_errors)
        else:
            self.status = self.STATUS_SENT
            self.sent_at = timezone.now()
            self.error_message = ""
        self.save(update_fields=["status", "sent_at", "error_message"])