#!/usr/bin/env python
"""
Test rapide du backend email Brevo.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.settings.dev')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("🚀 TEST RAPIDE EMAIL BACKEND")
print("="*40)

# Vérifier la config
print(f"📋 BREVO_API_KEY: {'✅' if settings.BREVO_API_KEY else '❌'}")
print(f"📋 EMAIL_BACKEND: {settings.EMAIL_BACKEND}")

# Test simple
try:
    print("\n📧 Envoi email de test...")
    
    result = send_mail(
        subject='Test Rapide NetExpress',
        message='Test rapide du backend email.',
        from_email='test@nettoyageexpresse.fr',
        recipient_list=['test@example.com'],
        fail_silently=False,
    )
    
    print(f"✅ SUCCESS: {result} email envoyé")
    
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n🏁 Test terminé")