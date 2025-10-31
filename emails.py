import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

from django.db import models
from django.utils import timezone

from decouple import config

"""import smtplib
import emails_config




def envoyer_email(email_destinataire, sujet, message):

    multipart_message = MIMEMultipart()
    multipart_message["Subject"] = sujet
    multipart_message["From"] = emails_config.config_email
    multipart_message["To"] = email_destinataire

    multipart_message.attach(MIMEText(message, "plain"))

    serveur_mail = smtplib.SMTP(emails_config.config_server, emails_config.config_server_port)
    serveur_mail.starttls()
    serveur_mail.login(emails_config.config_email, emails_config.config_password)
    serveur_mail.sendmail(emails_config.config_email, email_destinataire, multipart_message.as_string())
    serveur_mail.quit() """

#message_email = """Bonjour, Comment allez-vous ?Merci.


#envoyer_email("jonathan@codeavecjonathan.com", "Email depuis Python", message_email)


"""CONFIG_EMAIL = config('CONFIG_EMAIL')
CONFIG_PASSWORD = config('CONFIG_PASSWORD')
CONFIG_SERVER = config('CONFIG_SERVER')
CONFIG_SERVER_PORT = config('CONFIG_SERVER_PORT', cast=int)
CONFIG_RECIPIENT = config('CONFIG_RECIPIENT')"""

CONFIG_EMAIL = "ne-pas-repondre@nettoyage-express-sarl.fr"
CONFIG_PASSWORD = "Luxama973@"  # "zuvoozfusikgciba"
CONFIG_SERVER = "mail.nettoyage-express-sarl.fr"            # "smtp.gmail.com"
CONFIG_SERVER_PORT = 465  # 465  # 587
CONFIG_RECIPIENT ="vilmebeaudelaire5@gmail.com" # 

logger = logging.getLogger(__name__)


class Tache(models.Model):
    EN_ATTENTE = 'En attente'
    EN_COURS = 'En cours'
    TERMINE = 'Terminé'
    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (EN_COURS, 'En cours'),
        (TERMINE, 'Terminé'),
    ]

    titre = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, default="Aucune description.")
    localisation = models.CharField(max_length=100, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=EN_ATTENTE)
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(blank=True, null=True)

    def is_due_soon(self, days_threshold=3):
        if not self.date_fin:
            return False
        return (self.date_fin - timezone.now().date()).days <= days_threshold

    def generer_notification(self):
        base_message = f"Bonjour,\n\nLa tâche {self.titre.upper()} ({self.statut})"
        if self.statut == self.TERMINE:
            return f"{base_message} est terminée.\n\nDescription: {self.description}\nCordialement,"
        delta = (self.date_fin - timezone.now().date()).days
        return f"{base_message} doit être terminée dans {delta} jours.\n\nDescription: {self.description}\nCordialement,"

    def save(self, *args, **kwargs):
        if self.pk:
            original = Tache.objects.get(pk=self.pk)
            if original.statut != self.TERMINE and self.statut == self.TERMINE:
                self.date_fin = timezone.now().date()
        if self.date_fin and self.date_fin < self.date_debut:
            raise ValueError("La date de fin ne peut pas être antérieure à la date de début.")
        super().save(*args, **kwargs)

class EmailService:
    @staticmethod
    def envoyer_email(message, subject="NOTIFICATION NETTOYAGE EXPRESS", retries=3):
        for attempt in range(retries):
            try:
                multipart_message = MIMEMultipart()
                multipart_message["Subject"] = subject
                multipart_message["From"] = CONFIG_EMAIL
                multipart_message["To"] = CONFIG_RECIPIENT
                multipart_message.attach(MIMEText(message, "plain"))

                with smtplib.SMTP_SSL(CONFIG_SERVER, CONFIG_SERVER_PORT) as server:
                    server.login(CONFIG_EMAIL, CONFIG_PASSWORD)
                    server.sendmail(CONFIG_EMAIL, CONFIG_RECIPIENT, multipart_message.as_string())
                logger.info(f"Email envoyé avec succès à {CONFIG_RECIPIENT}.")
                break
            except Exception as e:
                logger.error(f"Tentative {attempt + 1} échouée : {str(e)}")
                if attempt == retries - 1:
                    logger.critical("Échec de l'envoi après plusieurs tentatives.")


EmailService.envoyer_email("Bonjour, Comment allez-vous ?Merci.")   

import uuid
from django.db import models
from django.utils import timezone

class Devis(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="devis")
    services = models.ManyToManyField(Service, related_name="devis")
    prix_initial = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    reduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    date_validite = models.DateField(default=lambda: timezone.now() + timezone.timedelta(days=30))
    numero_devis = models.CharField(max_length=50, unique=True, editable=False)

    def generate_numero_devis(self):
        return f'DEV-{uuid.uuid4().hex[:8]}'

    def save(self, *args, **kwargs):
        if not self.numero_devis:
            self.numero_devis = self.generate_numero_devis()
        super().save(*args, **kwargs)

    @property
    def prix_total(self):
        reduction = self.reduction or 0
        return self.prix_initial * (1 - reduction / 100)

    def __str__(self):
        return f"Devis: {self.client} - {self.prix_total}€"
