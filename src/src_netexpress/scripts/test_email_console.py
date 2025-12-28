#!/usr/bin/env python
"""
Script de test pour verifier l'envoi d'emails via SMTP.
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.settings.dev')

# Setup Django
django.setup()

from django.core.mail import send_mail, EmailMessage
from django.conf import settings

print("=" * 60)
print("TEST D'ENVOI D'EMAIL - BACKEND SMTP")
print("=" * 60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)
print()

# Demander l'email de destination
dest_email = input("Entrez votre email pour recevoir le test: ").strip()
if not dest_email or '@' not in dest_email:
    print("[ERREUR] Email invalide")
    sys.exit(1)

# Test: send_mail simple
print(f"\n>>> Envoi d'un email de test a {dest_email}...")
print("-" * 60)

try:
    result = send_mail(
        subject='Test SMTP NetExpress - Ca fonctionne!',
        message='Felicitations! Si vous recevez cet email, la configuration SMTP fonctionne correctement.\n\n-- Nettoyage Express',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[dest_email],
        fail_silently=False,
    )
    print(f"\n[OK] Email envoye avec succes! (result={result})")
    print(f"[INFO] Verifiez votre boite mail: {dest_email}")
except Exception as e:
    print(f"\n[ERREUR] {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("FIN DU TEST")
print("=" * 60)

