#!/usr/bin/env python
"""
Script de test pour le backend email Brevo avec fallback.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.settings.dev')
django.setup()

from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from core.backends.brevo_backend import BrevoEmailBackend
import logging

# Configuration du logging pour voir les détails
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class EmailBackendTester:
    """Testeur pour le backend email Brevo."""
    
    def __init__(self):
        self.backend = BrevoEmailBackend()
        
    def test_backend_initialization(self):
        """Tester l'initialisation du backend."""
        print("\n" + "="*60)
        print("🧪 TEST 1: INITIALISATION DU BACKEND")
        print("="*60)
        
        print(f"📋 Configuration actuelle:")
        print(f"  - BREVO_API_KEY: {'✅ Configurée' if settings.BREVO_API_KEY else '❌ Manquante'}")
        print(f"  - DEBUG: {settings.DEBUG}")
        print(f"  - EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        
        if hasattr(self.backend, 'use_fallback'):
            print(f"  - Fallback activé: {'✅ Oui' if self.backend.use_fallback else '❌ Non'}")
        
        if hasattr(self.backend, 'api_instance'):
            print(f"  - API Brevo: {'✅ Initialisée' if self.backend.api_instance else '❌ Échec'}")
        
        print(f"  - Console backend: {'✅ Disponible' if self.backend.console_backend else '❌ Indisponible'}")
        
    def test_simple_email(self):
        """Tester l'envoi d'un email simple."""
        print("\n" + "="*60)
        print("📧 TEST 2: ENVOI EMAIL SIMPLE")
        print("="*60)
        
        try:
            result = send_mail(
                subject='Test NetExpress - Email Simple',
                message='Ceci est un test d\'envoi d\'email depuis NetExpress v2.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['test@example.com'],
                fail_silently=False,
            )
            
            print(f"✅ Email envoyé avec succès")
            print(f"📊 Résultat: {result} email(s) envoyé(s)")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi: {e}")
            
    def test_html_email(self):
        """Tester l'envoi d'un email HTML."""
        print("\n" + "="*60)
        print("🎨 TEST 3: ENVOI EMAIL HTML")
        print("="*60)
        
        try:
            email = EmailMessage(
                subject='Test NetExpress - Email HTML',
                body='Version texte de l\'email de test.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['test@example.com'],
            )
            
            # Ajouter contenu HTML
            html_content = """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #0f6b4c;">Test NetExpress v2</h2>
                <p>Ceci est un <strong>email HTML</strong> de test.</p>
                <ul>
                    <li>✅ Backend Brevo fonctionnel</li>
                    <li>🔄 Fallback console disponible</li>
                    <li>🎨 Support HTML complet</li>
                </ul>
                <p style="color: #666;">
                    Envoyé depuis NetExpress v2 - Système ERP
                </p>
            </body>
            </html>
            """
            
            email.attach_alternative(html_content, "text/html")
            
            result = email.send()
            
            print(f"✅ Email HTML envoyé avec succès")
            print(f"📊 Résultat: {result} email(s) envoyé(s)")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi HTML: {e}")
    
    def test_email_with_attachment(self):
        """Tester l'envoi d'un email avec pièce jointe."""
        print("\n" + "="*60)
        print("📎 TEST 4: ENVOI EMAIL AVEC PIÈCE JOINTE")
        print("="*60)
        
        try:
            email = EmailMessage(
                subject='Test NetExpress - Email avec Pièce Jointe',
                body='Email de test avec pièce jointe.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['test@example.com'],
            )
            
            # Créer une pièce jointe de test
            test_content = """
# Rapport de Test NetExpress v2

## Backend Email
- ✅ Brevo API configurée
- 🔄 Fallback console disponible
- 📧 Envoi d'emails fonctionnel

## Tests Effectués
1. Initialisation du backend
2. Email simple
3. Email HTML
4. Email avec pièce jointe

Date: {date}
            """.format(date=django.utils.timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            email.attach('rapport_test.txt', test_content, 'text/plain')
            
            result = email.send()
            
            print(f"✅ Email avec pièce jointe envoyé avec succès")
            print(f"📊 Résultat: {result} email(s) envoyé(s)")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi avec pièce jointe: {e}")
    
    def test_backend_fallback(self):
        """Tester le mécanisme de fallback."""
        print("\n" + "="*60)
        print("🔄 TEST 5: MÉCANISME DE FALLBACK")
        print("="*60)
        
        # Sauvegarder la configuration actuelle
        original_api_key = self.backend.api_key
        original_use_fallback = getattr(self.backend, 'use_fallback', False)
        
        try:
            # Forcer le fallback
            self.backend.api_key = None
            self.backend.use_fallback = True
            
            print("🔄 Fallback forcé activé")
            
            result = send_mail(
                subject='Test NetExpress - Fallback Console',
                message='Ce message devrait apparaître dans la console.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['test@example.com'],
                fail_silently=False,
            )
            
            print(f"✅ Fallback console fonctionne")
            print(f"📊 Résultat: {result} email(s) traité(s)")
            
        except Exception as e:
            print(f"❌ Erreur lors du test fallback: {e}")
        finally:
            # Restaurer la configuration
            self.backend.api_key = original_api_key
            self.backend.use_fallback = original_use_fallback
    
    def test_brevo_api_direct(self):
        """Tester directement l'API Brevo."""
        print("\n" + "="*60)
        print("🔗 TEST 6: API BREVO DIRECTE")
        print("="*60)
        
        if not self.backend.api_instance:
            print("⚠️ API Brevo non initialisée, test ignoré")
            return
        
        try:
            # Créer un message de test simple
            from django.core.mail import EmailMessage
            
            test_message = EmailMessage(
                subject='Test Direct API Brevo',
                body='Test direct de l\'API Brevo depuis NetExpress v2.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['test@example.com'],
            )
            
            # Utiliser directement la méthode Brevo
            result = self.backend._send_message_brevo(test_message)
            
            if result:
                print("✅ API Brevo fonctionne directement")
            else:
                print("❌ Échec de l'API Brevo directe")
                
        except Exception as e:
            print(f"❌ Erreur API Brevo directe: {e}")
    
    def run_all_tests(self):
        """Exécuter tous les tests."""
        print("🚀 TESTS DU BACKEND EMAIL NETEXPRESS V2")
        print("="*60)
        
        try:
            self.test_backend_initialization()
            self.test_simple_email()
            self.test_html_email()
            self.test_email_with_attachment()
            self.test_backend_fallback()
            self.test_brevo_api_direct()
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrompus par l'utilisateur")
        except Exception as e:
            print(f"\n❌ Erreur générale lors des tests: {e}")
        
        print("\n" + "="*60)
        print("🏁 TESTS TERMINÉS")
        print("="*60)
        
        print("\n📋 Résumé:")
        print("- Vérifiez la console pour les emails en mode fallback")
        print("- Vérifiez les logs pour les détails des envois Brevo")
        print("- En cas d'erreur, le fallback console devrait fonctionner")
        
        print("\n🔍 Prochaines étapes:")
        print("1. Vérifier les logs d'application")
        print("2. Tester depuis l'interface admin Django")
        print("3. Vérifier la réception des emails si Brevo fonctionne")


if __name__ == '__main__':
    import django.utils.timezone
    
    tester = EmailBackendTester()
    
    print("⚠️ Ce script va envoyer des emails de test")
    print("📧 Les emails seront envoyés à 'test@example.com'")
    print("🔄 En cas d'erreur Brevo, fallback vers console")
    
    confirm = input("\n🤔 Continuer les tests? (oui/non): ").lower().strip()
    
    if confirm in ['oui', 'o', 'yes', 'y']:
        tester.run_all_tests()
    else:
        print("❌ Tests annulés par l'utilisateur")