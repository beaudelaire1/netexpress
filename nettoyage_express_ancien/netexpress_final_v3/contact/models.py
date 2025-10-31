"""
Modèles pour l'app ``contact``.

Le modèle ``Message`` stocke les demandes envoyées via le formulaire de
contact.  Chaque message comporte un sujet (prospection, SAV, partenariat,
gros volumes…), les coordonnées de l'expéditeur et le contenu du message.
Les champs ``created_at`` et ``ip`` permettent la journalisation et la
modération.
"""

from django.db import models


class Message(models.Model):
    TOPIC_CHOICES = [
        ("bricolage", "Bricolage"),
        ("peinture", "Peinture"),
        ("renovation", "Rénovation"),
        ("service_vert", "Service Espace Vert"),
        ("partenariat", "Partenariat"),
        ("autre", "Autre"),
    ]

    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    city= models.CharField(max_length=200)
    # Utiliser un champ de caractères pour le code postal afin de
    # prendre en charge à la fois les codes numériques et alphanumériques
    # (certaines régions ont des codes avec des lettres).  L'option
    # `max_length` spécifie la longueur maximale autorisée.
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=50, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "message de contact"
        verbose_name_plural = "messages de contact"
        indexes = [models.Index(fields=["topic", "created_at"])]

    def __str__(self) -> str:
        return f"Message de {self.full_name} ({self.get_topic_display()})"

    # Ajout d'une méthode utilitaire pour masquer partiellement l'adresse e-mail
    # lors de l'affichage dans certaines interfaces (ex. : admin personnalisé).
    def obfuscated_email(self) -> str:
        """Retourne l'adresse e-mail en masquant le nom d'utilisateur pour la confidentialité."""
        user, _, domain = self.email.partition("@")
        return f"{user[:1]}***@{domain}"