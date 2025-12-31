"""
Commande de gestion Django pour tester la configuration email.

Cette commande permet de vérifier rapidement si la configuration email
(SMTP ou Brevo) est correcte en envoyant un email de test.

Usage:
    python manage.py test_email_config destinataire@example.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ...models import EmailMessage


class Command(BaseCommand):
    help = "Teste la configuration email en envoyant un message de test"

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help="Adresse email du destinataire pour le test"
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        # Afficher la configuration actuelle
        self.stdout.write(self.style.WARNING('\n=== Configuration Email ==='))
        
        backend_type = getattr(settings, 'EMAIL_BACKEND_TYPE', 'smtp')
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'Non défini')
        
        self.stdout.write(f"Type de backend : {backend_type}")
        self.stdout.write(f"Backend Django  : {email_backend}")
        
        if backend_type == 'brevo':
            api_key = getattr(settings, 'ANYMAIL', {}).get('BREVO_API_KEY', '')
            if api_key:
                self.stdout.write(self.style.SUCCESS(f"✓ Clé API Brevo configurée (commence par {api_key[:10]}...)"))
            else:
                self.stdout.write(self.style.ERROR("✗ Clé API Brevo manquante"))
        else:
            email_host = getattr(settings, 'EMAIL_HOST', 'Non défini')
            email_port = getattr(settings, 'EMAIL_PORT', 'Non défini')
            email_user = getattr(settings, 'EMAIL_HOST_USER', 'Non défini')
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            
            self.stdout.write(f"Serveur SMTP    : {email_host}:{email_port}")
            self.stdout.write(f"Utilisateur     : {email_user}")
            
            if email_password:
                self.stdout.write(self.style.SUCCESS(f"✓ Mot de passe SMTP configuré"))
            else:
                self.stdout.write(self.style.ERROR("✗ Mot de passe SMTP manquant"))
        
        self.stdout.write('\n=== Envoi du test ===')
        self.stdout.write(f"Destinataire : {recipient}\n")
        
        # Créer et envoyer un email de test
        try:
            email_obj = EmailMessage.objects.create(
                recipient=recipient,
                subject="Test de configuration email - NetExpress",
                body=(
                    "Ceci est un email de test pour vérifier la configuration.\n\n"
                    f"Configuration utilisée : {backend_type.upper()}\n"
                    f"Backend Django : {email_backend}\n\n"
                    "Si vous recevez cet email, votre configuration fonctionne correctement ! ✓\n\n"
                    "---\n"
                    "NetExpress - Nettoyage Express"
                ),
            )
            
            # Tenter l'envoi
            email_obj.send()
            
            # Vérifier le statut
            email_obj.refresh_from_db()
            
            if email_obj.status == EmailMessage.STATUS_SENT:
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Email envoyé avec succès à {recipient} !'
                ))
                self.stdout.write(
                    f'Horodatage : {email_obj.sent_at}'
                )
            else:
                self.stdout.write(self.style.ERROR(
                    f'\n✗ Échec de l\'envoi'
                ))
                if email_obj.error_message:
                    self.stdout.write(self.style.ERROR(
                        f'Erreur : {email_obj.error_message}'
                    ))
                    
                    # Fournir des suggestions basées sur l'erreur
                    error = email_obj.error_message.lower()
                    self.stdout.write('\n=== Suggestions ===')
                    
                    if '401' in error or 'unauthorized' in error:
                        self.stdout.write("→ Vérifiez que votre clé API Brevo est correcte")
                        self.stdout.write("→ https://app.brevo.com/settings/keys/api")
                    elif 'authentication' in error or 'login' in error:
                        self.stdout.write("→ Vérifiez votre EMAIL_HOST_USER et EMAIL_HOST_PASSWORD")
                        self.stdout.write("→ Pour Gmail, utilisez un mot de passe d'application")
                    elif 'connection' in error or 'timeout' in error:
                        self.stdout.write("→ Vérifiez EMAIL_HOST, EMAIL_PORT, EMAIL_USE_SSL/TLS")
                    
        except Exception as e:
            raise CommandError(f'Erreur lors du test : {str(e)}')
