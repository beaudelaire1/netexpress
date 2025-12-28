#!/usr/bin/env python
"""
Test SMTP Brevo avec differentes configurations de login.
"""
import smtplib

import os

# Cle SMTP Brevo via variable d'environnement
SMTP_KEY = os.getenv("BREVO_SMTP_PASSWORD", "")

# Configurations a tester
configs = [
    # Config 1: Email comme login
    {
        'host': 'smtp-relay.brevo.com',
        'port': 587,
        'login': os.getenv("BREVO_SMTP_LOGIN", ""),
        'password': SMTP_KEY,
        'name': 'Email + Cle SMTP'
    },
    # Config 2: Cle comme login et password
    {
        'host': 'smtp-relay.brevo.com',
        'port': 587,
        'login': SMTP_KEY,
        'password': SMTP_KEY,
        'name': 'Cle SMTP comme login et password'
    },
    # Config 3: Sendinblue ancien format
    {
        'host': 'smtp-relay.sendinblue.com',
        'port': 587,
        'login': 'nettoyageexpress01@gmail.com',
        'password': SMTP_KEY,
        'name': 'Ancien domaine Sendinblue'
    },
]

print("=" * 60)
print("TEST SMTP BREVO - MULTIPLES CONFIGURATIONS")
print("=" * 60)

if not SMTP_KEY or not os.getenv("BREVO_SMTP_LOGIN", ""):
    raise SystemExit("Definis BREVO_SMTP_LOGIN et BREVO_SMTP_PASSWORD avant de lancer ce test.")

for i, config in enumerate(configs, 1):
    print(f"\n>>> Config {i}: {config['name']}")
    print(f"    Host: {config['host']}:{config['port']}")
    print(f"    Login: {config['login'][:30]}...")
    print("-" * 40)
    
    try:
        server = smtplib.SMTP(config['host'], config['port'], timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config['login'], config['password'])
        server.quit()
        print(f"    [SUCCES] Authentification reussie!")
        print(f"\n>>> CONFIGURATION VALIDE TROUVEE!")
        print(f"    Host: {config['host']}")
        print(f"    Port: {config['port']}")
        print(f"    Login: {config['login']}")
        break
    except smtplib.SMTPAuthenticationError as e:
        print(f"    [ECHEC] Auth failed: {e.smtp_code}")
    except Exception as e:
        print(f"    [ERREUR] {type(e).__name__}: {e}")
else:
    print("\n" + "=" * 60)
    print("[ECHEC] Aucune configuration n'a fonctionne.")
    print("La cle SMTP Brevo fournie semble invalide ou expiree.")
    print("=" * 60)

