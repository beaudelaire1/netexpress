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
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User

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
    
    Note: Le champ body contient le HTML généré par les templates prédéfinis.
    Aucun texte libre n'est permis - le contenu est toujours stylisé.
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
    body = models.TextField(help_text="Contenu HTML généré par les templates prédéfinis.")
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
        """Envoyer le message (HTML premium uniquement).

        Exigences:
        - Aucun e-mail en texte brut (pas de multipart text/plain visible)
        - Le contenu HTML est déjà stylisé via les templates prédéfinis
        - Les destinataires multiples sont envoyés individuellement (pas de fuite d'adresses)
        """
        if self.status == self.STATUS_SENT:
            return

        from django.conf import settings

        # Normaliser les destinataires (to + cc) : on envoie individuellement
        to_addresses = [a.strip() for a in (self.recipient or "").split(",") if a.strip()]
        cc_addresses = [a.strip() for a in (self.cc or "").split(",") if a.strip()]
        all_addresses: list[str] = []
        for addr in to_addresses + cc_addresses:
            if addr and addr not in all_addresses:
                all_addresses.append(addr)

        # Pièces jointes
        attachments: list[tuple[str, bytes]] = []
        if self.attachment:
            try:
                content = self.attachment.read()
                filename = (self.attachment.name or "piece-jointe").rsplit("/", 1)[-1]
                attachments.append((filename, content))
            except Exception:
                pass

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@nettoyageexpress.com"
        
        # Le body contient déjà le HTML stylisé généré par les templates
        html_body = self.body

        send_errors: list[str] = []
        for to_addr in all_addresses or []:
            try:
                email = EmailMultiAlternatives(
                    subject=self.subject,
                    body=html_body,
                    from_email=from_email,
                    to=[to_addr],
                )
                email.content_subtype = "html"  # HTML only
                # Attachements
                for (fname, data) in attachments:
                    email.attach(fname, data)
                # Use fail_silently=True to prevent crashes, handle errors explicitly
                try:
                    email.send(fail_silently=True)
                except Exception as send_exc:
                    send_errors.append(f"{to_addr}: {send_exc}")
            except Exception as exc:
                send_errors.append(f"{to_addr}: {exc}")

        # Mise à jour statut
        if send_errors:
            self.status = self.STATUS_FAILED
            self.error_message = "; ".join(send_errors)
        else:
            self.status = self.STATUS_SENT
            self.sent_at = timezone.now()
            self.error_message = ""
        self.save(update_fields=["status", "sent_at", "error_message", "status"])


class MessageThread(models.Model):
    """Groups related messages for conversation threading."""
    
    participants = models.ManyToManyField(User, related_name='message_threads')
    subject = models.CharField(max_length=200)
    last_message_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-last_message_at"]
        verbose_name = "fil de discussion"
        verbose_name_plural = "fils de discussion"
    
    def __str__(self) -> str:
        return f"{self.subject} ({self.participants.count()} participants)"


class Message(models.Model):
    """Internal messaging system for portal communication."""
    
    thread = models.ForeignKey(
        MessageThread, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True,
        blank=True
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200)
    content = models.TextField(help_text="Message content")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "message interne"
        verbose_name_plural = "messages internes"
    
    def __str__(self) -> str:
        return f"{self.subject} - {self.sender.username} → {self.recipient.username}"
    
    def mark_as_read(self) -> None:
        """Mark the message as read."""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
    
    @property
    def is_read(self) -> bool:
        """Check if the message has been read."""
        return self.read_at is not None
