"""
Django settings for netexpress project - DEVELOPMENT CONFIGURATION
"""

from .base import *  # noqa
import os
from pathlib import Path

# ============================================================
# 📁 CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
# ============================================================

# Charger d'abord le fichier .env principal, puis .env.local pour override
from dotenv import load_dotenv

# Charger .env principal
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Charger .env.local pour override (priorité plus élevée)
env_local_path = BASE_DIR / '.env.local'
if env_local_path.exists():
    load_dotenv(env_local_path, override=True)

# ============================================================
# ⚙️ MODE DÉVELOPPEMENT
# ============================================================

DEBUG = True

# ============================================================
# 🔑 SECRET KEY (POUR LE DÉVELOPPEMENT)
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-not-for-production-use-only")

# ============================================================
# 🌍 HÔTES AUTORISÉS (DÉVELOPPEMENT)
# ============================================================

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# ============================================================
# 🔐 CSRF TRUSTED ORIGINS (DÉVELOPPEMENT)
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ============================================================
# 🗄️ BASE DE DONNÉES (SQLITE POUR LE DÉVELOPPEMENT)
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# 🔐 SÉCURITÉ (DÉSACTIVÉE EN DÉVELOPPEMENT)
# ============================================================

# Pas de HTTPS en développement
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# ============================================================
# EMAIL (DEVELOPPEMENT) - MODE API OU SMTP (BREVO)
# ============================================================

from django.core.exceptions import ImproperlyConfigured

# Mode email (force le comportement en dev)
# - "api": envoi via API transactionnelle Brevo
# - "smtp": envoi via SMTP Brevo
# Par defaut: "smtp" en dev (tu veux SMTP en dev)
BREVO_EMAIL_MODE = (os.getenv("BREVO_EMAIL_MODE", "") or "").strip().lower()

# Cle API Brevo (optionnelle)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()

# Expediteur (doit etre un sender/une adresse valide dans Brevo)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "contact@nettoyageexpresse.fr")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Nettoyage Express")

if BREVO_EMAIL_MODE not in ("", "api", "smtp"):
    raise ImproperlyConfigured("BREVO_EMAIL_MODE doit etre vide, 'api' ou 'smtp'")

effective_mode = BREVO_EMAIL_MODE
if not effective_mode:
    effective_mode = "smtp"

if effective_mode == "api":
    if not BREVO_API_KEY:
        raise ImproperlyConfigured("BREVO_EMAIL_MODE=api mais BREVO_API_KEY est vide")
    # API transactionnelle Brevo
    EMAIL_BACKEND = "core.backends.brevo_backend.BrevoEmailBackend"
    # En dev, on veut eviter que l'envoi "tombe" en console silencieusement.
    # Si l'API echoue (sender non verifie, etc.), on prefere une erreur claire.
    BREVO_CONSOLE_FALLBACK = False
    print("[DEV] Email backend: Brevo (API)")
else:
    # SMTP (fallback) si pas de cle API
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    EMAIL_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
    EMAIL_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("BREVO_SMTP_USE_TLS", "True") == "True"
    EMAIL_USE_SSL = os.getenv("BREVO_SMTP_USE_SSL", "False") == "True"
    EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))

    EMAIL_HOST_USER = os.getenv("BREVO_SMTP_LOGIN", "").strip()
    EMAIL_HOST_PASSWORD = (os.getenv("BREVO_SMTP_PASSWORD", "") or "").strip()

    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured(
            "Email non configure en dev. "
            "Soit definis BREVO_API_KEY (API), soit definis BREVO_SMTP_LOGIN et BREVO_SMTP_PASSWORD (SMTP) dans .env.local."
        )

    # Evite les erreurs smtplib du type: UnicodeEncodeError ascii (auth_cram_md5)
    # Brevo attend une cle SMTP ASCII (xsmtpsib-...)
    def _first_non_ascii(value: str):
        for idx, ch in enumerate(value):
            if ord(ch) > 127:
                return idx, ord(ch)
        return None

    bad_user = _first_non_ascii(EMAIL_HOST_USER)
    bad_pwd = _first_non_ascii(EMAIL_HOST_PASSWORD)
    if bad_user or bad_pwd:
        where = "BREVO_SMTP_LOGIN" if bad_user else "BREVO_SMTP_PASSWORD"
        idx, codepoint = bad_user or bad_pwd
        raise ImproperlyConfigured(
            f"{where} contient un caractere non-ASCII (index={idx}, codepoint={codepoint}). "
            "Copie-colle la valeur depuis Brevo (sans accents, sans espaces, sans texte autour)."
        )

    print(f"[DEV] Email backend: SMTP ({EMAIL_HOST}:{EMAIL_PORT}) - Login: {EMAIL_HOST_USER}")

# ============================================================
# 📊 LOGGING EN DÉVELOPPEMENT
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================
# 🔥 DEBUG - AFFICHAGE FINAL DE LA CONFIG
# ============================================================

print("[DEV] MODE DEVELOPPEMENT ACTIVE - SQLite")
print(f"DATABASE: {DATABASES['default']['NAME']}")
print(f"EMAIL_BACKEND: {EMAIL_BACKEND}")
if EMAIL_HOST_USER:
    print(f"EMAIL configuré avec: {EMAIL_HOST_USER}")
else:
    print("EMAIL: Mode console (pas de SMTP configuré)")
