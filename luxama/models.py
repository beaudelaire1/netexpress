import os
import datetime
from random import  randint
from num2words import num2words
from datetime import datetime, timedelta
import smtplib
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, EmailValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import timedelta
from django.utils import timezone

def date_de_validite_default():
    return timezone.now() + timedelta(days=30)

# import numpy as np


# Configuration externe (à placer dans settings.py ou variables d'environnement)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.netexpress.settings')


CONFIG_EMAIL = "ne-pas-repondre@nettoyage-express-sarl.fr"
CONFIG_PASSWORD = "Luxama973@"  # "zuvoozfusikgciba"
CONFIG_SERVER = "mail.nettoyage-express-sarl.fr"            # "smtp.gmail.com"
CONFIG_SERVER_PORT = 465  # 465  # 587
CONFIG_RECIPIENT ="vilmebeaudelaire5@gmail.com" # "n.express@orange.fr"  # Adresse de l'administrateur


# Modèle Service (inchangé)
class Service(models.Model):
    CATEGORIES = [
        ("Nettoyage", "Nettoyage"),
        ("Peinture", "Peinture"),
        ("Renovation", "Rénovation"),
        ("Bricolage", "Bricolage"),
        ("Espace Vert", "Espace Vert"),
        ("Autre", "Autre"),
    ]
    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    service = models.CharField(max_length=100, choices=CATEGORIES, default="Autre")

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('service_detail', kwargs={'pk': self.pk})


# Modèle Client (inchangé)
class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, default="")
    email = models.EmailField(validators=[EmailValidator()])
    telephone = models.CharField(max_length=15)
    adresse = models.CharField(max_length=150)
    code_postal = models.CharField(max_length=5, default="97300")

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    def get_absolute_url(self):
        return reverse('client_detail', kwargs={'pk': self.pk})


# Modèle Devis (inchangé)
class Devis(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="devis")
    service = models.ManyToManyField(Service, related_name="devis")
    prix_initial = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    reduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_de_creation = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    date_de_validite = models.DateField(default=date_de_validite_default)
    numero_devis = models.CharField(max_length=50, unique=True, editable=False)

    def generate_numero_devis(self):
        while True:
            numero = 'DEV-' + str(datetime.datetime.now().year) + str(randint(1000, 9999))
            if not Devis.objects.filter(numero_devis=numero).exists():
                return numero

    def save(self, *args, **kwargs):
        if not self.numero_devis:
            self.numero_devis = self.generate_numero_devis()
        super(Devis, self).save(*args, **kwargs)

    @property
    def prix_total(self):
        if self.prix_initial is not None: # and self.reduction is not None:
            return self.prix_initial - (self.prix_initial * self.reduction / 100)
        elif self.prix_initial is not None:
            return self.prix_initial  # Retourne le prix initial si la réduction est None
        else:
            return 0  # Retourne 0 si le prix initial est None

    def prix_total_lettre(self):
        return num2words(float(self.prix_total), to='currency', lang='fr')

    def __str__(self):
        return f"Devis: {self.client} - {self.prix_total}€"

    class Meta:
        ordering = ['-date_de_creation']
        verbose_name = "Devis"
        verbose_name_plural = "Devis"


# Modèle Tâche (avec améliorations)
class Tache(models.Model):
    """ Modèle représentant une tâche avec un statut, une localisation et des dates associées. """

    # Définition des statuts possibles
    EN_ATTENTE = 'En attente'
    EN_COURS = 'En cours'
    TERMINE = 'Terminé'

    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (EN_COURS, 'En cours'),
        (TERMINE, 'Terminé'),
    ]

    # Champs du modèle
    titre = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, default="Il n'y a aucune description pour cette tâche.")
    localisation = models.CharField(max_length=100, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=EN_ATTENTE)
    date_debut = models.DateField()
    date_fin = models.DateField()

    def __str__(self):
        """ Représentation en string de l'objet. """
        return f"{self.titre} ({self.statut})"


    def get_absolute_url(self):
        """ Retourne l'URL pour accéder au détail de la tâche. """
        return reverse('tache_detail', kwargs={'pk': self.pk})

    def statut_changed(self):
        """ Vérifie si le statut a changé. """
        return self.statut == self.statut
    def is_due_soon(self, days_threshold=3):
        """
        Vérifie si la tâche est proche de son échéance (dans `days_threshold` jours).
        :param days_threshold: Nombre de jours avant la date de fin pour déclencher l'alerte.
        :return: True si la tâche arrive bientôt à échéance, sinon False.
        """
        if not self.date_fin:
            return False  # Pas de date de fin définie
        return (self.date_fin - timezone.now().date()).days <= days_threshold

    def generer_notification(self):
        """
        Génère un message de notification en fonction du statut et de la date de fin.
        :return: Message de notification sous forme de chaîne de caractères.
        """
        base_message = f"Bonjour,\n\nLa tâche {self.titre.upper()}, située à {self.localisation}"

        if self.statut == self.TERMINE:
            return f"{base_message} est terminée.\n\nDescription: \n{self.description}\n\nCordialement,"

        if not self.date_fin:
            return f"{base_message} est en cours, mais la date de fin n'est pas définie.\n\nDescription:\n{self.description}\n\nCordialement,"

        delta = (self.date_fin - timezone.now().date()).days

        if self.statut_changed():
            return f"la tâche {self.titre.upper()} a changé de statut.\n\nElle passe à {self.statut}\n\nCordialement,"

        if delta == 0:
            return f"{base_message}, actuellement {self.statut}, doit être terminée AUJOURD’HUI.\n\nDescription: \n{self.description}\n\nCordialement,"

        if 0 < delta <= 3:
            return f"{base_message}, actuellement {self.statut}, doit être terminée dans {delta} jours.\n\nDescription: \n{self.description}\n\nCordialement,"

        return f"{base_message}, actuellement {self.statut}, doit être terminée dans {delta} jours.\n\nDescription:\n{self.description}\n\nCordialement,"

    def save(self, *args, **kwargs):
        """
        Surcharge de la méthode save() pour :
        - Vérifier la cohérence des dates (date_fin >= date_debut)
        - Déclencher des actions en cas de changement de statut
        """

        # Vérifier si l'instance existait déjà avant modification
        if self.pk:
            original = Tache.objects.get(pk=self.pk)

            # Si le statut passe à "Terminé", enregistrer la date de fin
            if original.statut != self.TERMINE and self.statut == self.TERMINE:
                self.date_fin = timezone.now().date()

        # Vérifier la cohérence des dates
        if self.date_fin < self.date_debut:
            raise ValueError("La date de fin ne peut pas être antérieure à la date de début.")

        super().save(*args, **kwargs)


# Service d'envoi d'email
class EmailService:
    @staticmethod
    def envoyer_email(message_email, destinataire, subject="NOTIFICATION NETTOYAGE EXPRESS"):
        multipart_message = MIMEMultipart()
        multipart_message["Subject"] = subject
        multipart_message["From"] = CONFIG_EMAIL
        multipart_message["To"] = destinataire
        multipart_message.attach(MIMEText(message_email, "plain"))

        try:
            # Connexion au serveur SMTP
            print("🟢 Connexion au serveur SMTP...")
            serveur_mail = smtplib.SMTP_SSL(CONFIG_SERVER, CONFIG_SERVER_PORT)
            print("✅ Connexion réussie")

            serveur_mail.login(CONFIG_EMAIL, CONFIG_PASSWORD)
            print("✅ Authentification réussie")

            serveur_mail.sendmail(CONFIG_EMAIL, destinataire, multipart_message.as_string())
            serveur_mail.quit()
            print("✅ Email envoyé avec succès à", destinataire)

        except smtplib.SMTPAuthenticationError:
            print("❌ Erreur d'authentification SMTP : vérifiez votre email/mot de passe.")
        except smtplib.SMTPConnectError:
            print("❌ Impossible de se connecter au serveur SMTP : vérifiez l'hôte et le port.")
        except smtplib.SMTPRecipientsRefused:
            print(f"❌ Le destinataire {destinataire} a refusé l'email.")
        except smtplib.SMTPSenderRefused:
            print(f"❌ L'expéditeur {CONFIG_EMAIL} a été refusé par le serveur.")
        except smtplib.SMTPDataError:
            print("❌ Le serveur SMTP a rejeté le message.")
        except Exception as e:
            print(f"❌ Une erreur inattendue s'est produite : {str(e)}")


# Signal pour envoyer une notification lors de la création ou mise à jour d'une tâche
@receiver(post_save, sender=Tache)
def send_notification(sender, instance, created,  **kwargs):
    if created :
        message = instance.generer_notification()
        EmailService.envoyer_email(message, CONFIG_RECIPIENT)
    if instance.statut_changed():
        message = instance.generer_notification()
        EmailService.envoyer_email(message, CONFIG_RECIPIENT, "CHANGEMENT DE STATUT DE TÂCHE NETTOYAGE EXPRESS")
    if instance.is_due_soon():
        message = instance.generer_notification()
        EmailService.envoyer_email(message, CONFIG_RECIPIENT, "ALERTE - TÂCHE À ÉCHEANCE IMMINENTE NETTOYAGE EXPRESS")
