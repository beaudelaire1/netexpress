import os
import django
import smtplib
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, EmailValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np


# Configuration externe (à placer dans settings.py ou variables d'environnement)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.netexpress.settings')
#django.setup()

# Maintenant, vous pouvez accéder aux paramètres Django


CONFIG_EMAIL = "ne-pas-repondre@nettoyage-express-sarl.fr"      #"ne-pas-repondre@nettoyage-express-sarl.fr"
CONFIG_PASSWORD = "Luxama973@"  #"zuvoozfusikgciba"
CONFIG_SERVER = "mail.nettoyage-express-sarl.fr"            #"smtp.gmail.com"  #"mail.nettoyage-express-sarl.fr"
CONFIG_SERVER_PORT = 465 #465  #587
CONFIG_RECIPIENT = "n.express@orange.fr"  #"n.express@orange.fr"  # Adresse de l'administrateur


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
    prix_initial = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_de_creation = models.DateTimeField(auto_now_add=True)

    @property
    def prix_total(self):
        return self.prix_initial - (self.prix_initial * self.reduction / 100)

    def __str__(self):
        return f"Devis: {self.client} - {self.prix_total}€"

    class Meta:
        ordering = ['-date_de_creation']
        verbose_name = "Devis"
        verbose_name_plural = "Devis"

# Modèle Tâche (avec améliorations)
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
    description = models.TextField()
    localisation = models.CharField(max_length=100, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=EN_ATTENTE)
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse('tache_detail', kwargs={'pk': self.pk})

    def generer_notification(self):
        if self.statut == self.TERMINE:
            return f"Bonjour,\n\nLa tâche {self.titre.upper()}, située à {self.localisation} située à {self.localisation} est terminée.\n\nDescription: \n{self.description}\n\n\nCordialement,"

        if not self.date_fin:
            return f"Bonjour,\n\nLa tâche {self.titre.upper()}, située à {self.localisation} est en cours, date de fin non définie. \n\nDescription:\n {self.description}\n\n\nCordialement, "

        delta = np.abs((self.date_fin - timezone.now()).days)

        if delta <= 3:
            return f"Bonjour,\n\nLa tâche {self.titre.upper()}, située à {self.localisation}, actuellement {self.statut}, doit être terminée dans {delta} jours. \n\nDescription: \n{self.description}\n\n\nCordialement,"
        else:
            return f"Bonjour,\n\nLa tâche {self.titre.upper()}, située à {self.localisation}, actuellement {self.statut}, doit être terminée dans {delta} jours.\n\n" \
                   f"Description: \n{self.description}\n\n\nCordialement,"

    def save(self, *args, **kwargs):
        if self.pk:  # Si l'instance existe déjà (mise à jour)
            original = Tache.objects.get(pk=self.pk)

        super().save(*args, **kwargs)



"""
# Service d'envoi d'email
class EmailService:
    @staticmethod
    def envoyer_email(message_email):
        multipart_message = MIMEMultipart()
        multipart_message["Subject"] = "NOTIFICATION NETTOYAGE EXPRESS"
        multipart_message["From"] = CONFIG_EMAIL
        multipart_message["To"] = CONFIG_RECIPIENT
        multipart_message.attach(MIMEText(message_email, "plain"))

        try:
            serveur_mail = smtplib.SMTP(CONFIG_SERVER, CONFIG_SERVER_PORT)
            serveur_mail.starttls()
            serveur_mail.login(CONFIG_EMAIL, CONFIG_PASSWORD)
            serveur_mail.sendmail(CONFIG_EMAIL, CONFIG_RECIPIENT, multipart_message.as_string())
            serveur_mail.quit()
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}") """


# Service d'envoi d'email
class EmailService:
    @staticmethod
    def envoyer_email(message_email):
        multipart_message = MIMEMultipart()
        multipart_message["Subject"] = "NOTIFICATION NETTOYAGE EXPRESS"
        multipart_message["From"] = CONFIG_EMAIL
        multipart_message["To"] = CONFIG_RECIPIENT
        multipart_message.attach(MIMEText(message_email, "plain"))

        try:
            # Connexion au serveur SMTP
            print("🟢 Connexion au serveur SMTP...")
            serveur_mail = smtplib.SMTP_SSL(CONFIG_SERVER, CONFIG_SERVER_PORT)
            print("✅ Connexion réussie")
            #serveur_mail.ehlo()
            #serveur_mail.starttls()


            serveur_mail.login(CONFIG_EMAIL, CONFIG_PASSWORD)
            print("✅ Authentification réussie")

            serveur_mail.sendmail(CONFIG_EMAIL, CONFIG_RECIPIENT, multipart_message.as_string())
            serveur_mail.quit()
            print("✅ Email envoyé avec succès à", CONFIG_RECIPIENT)

        except smtplib.SMTPAuthenticationError:
            print("❌ Erreur d'authentification SMTP : vérifiez votre email/mot de passe.")
        except smtplib.SMTPConnectError:
            print("❌ Impossible de se connecter au serveur SMTP : vérifiez l'hôte et le port.")
        except smtplib.SMTPRecipientsRefused:
            print(f"❌ Le destinataire {CONFIG_RECIPIENT} a refusé l'email.")
        except smtplib.SMTPSenderRefused:
            print(f"❌ L'expéditeur {CONFIG_EMAIL} a été refusé par le serveur.")
        except smtplib.SMTPDataError:
            print("❌ Le serveur SMTP a rejeté le message.")
        except Exception as e:
            print(f"❌ Une erreur inattendue s'est produite : {str(e)}")


# Signal pour envoyer une notification lors de la création ou mise à jour d'une tâche
@receiver(post_save, sender=Tache)
def send_notification(sender, instance, created, **kwargs):
    if created or instance.statut_changed or instance.dates_changed:
        message = instance.generer_notification()
        EmailService.envoyer_email(message)

# Test de la notification (dans un script de test ou un management command)
def test_notification(tache_id):
    try:
        tache = Tache.objects.get(pk=tache_id)
        send_notification(Tache, tache, created=False)  # Simule une mise à jour
        print("Notification testée.")
    except Tache.DoesNotExist:
        print("Tâche non trouvée.")
