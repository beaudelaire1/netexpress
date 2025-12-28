#!/usr/bin/env python
"""
Script de test SMTP direct (sans Django) pour diagnostiquer la connexion.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration SMTP Brevo (via variables d'environnement)
# Exemples a mettre dans .env.local:
# BREVO_SMTP_HOST=smtp-relay.brevo.com
# BREVO_SMTP_PORT=587
# BREVO_SMTP_LOGIN=9e61f6001@smtp-brevo.com
# BREVO_SMTP_PASSWORD=xxxxxx
import os

SMTP_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
SMTP_USER = os.getenv("BREVO_SMTP_LOGIN", "")
SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "")

print("=" * 60)
print("TEST SMTP DIRECT - BREVO")
print("=" * 60)
print(f"Serveur: {SMTP_HOST}:{SMTP_PORT}")
print(f"Utilisateur: {SMTP_USER or '[VIDE]'}")
print(f"Mot de passe: {'[DEFINI]' if SMTP_PASSWORD else '[VIDE]'}")
print("=" * 60)
print()

# Test de connexion
print(">>> Test 1: Connexion au serveur SMTP...")
try:
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("BREVO_SMTP_LOGIN/BREVO_SMTP_PASSWORD non definis")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    server.set_debuglevel(1)  # Active le mode debug
    print("[OK] Connexion etablie")
    
    print("\n>>> Test 2: EHLO...")
    server.ehlo()
    print("[OK] EHLO reussi")
    
    print("\n>>> Test 3: STARTTLS...")
    server.starttls()
    print("[OK] TLS active")
    
    print("\n>>> Test 4: Authentification...")
    server.login(SMTP_USER, SMTP_PASSWORD)
    print("[OK] Authentification reussie!")
    
    server.quit()
    print("\n" + "=" * 60)
    print("[SUCCES] La configuration SMTP est correcte!")
    print("=" * 60)
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n[ERREUR] Echec d'authentification: {e}")
    print("[INFO] Verifiez le login et le mot de passe SMTP")
except smtplib.SMTPException as e:
    print(f"\n[ERREUR] Erreur SMTP: {e}")
except Exception as e:
    print(f"\n[ERREUR] {e}")
    import traceback
    traceback.print_exc()

