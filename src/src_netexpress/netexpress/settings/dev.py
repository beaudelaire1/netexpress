"""
Django settings for netexpress project - DEVELOPMENT CONFIGURATION
"""

# ============================================================
# 📁 CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
# ============================================================
#
# Les fichiers .env sont chargés AVANT base.py, et c'est essentiel : base.py
# lit l'environnement au moment de son import (email, Turnstile, destinataires
# des notifications, branding des factures). Chargé après, .env.local n'était
# vu par aucun de ces réglages, qui retombaient silencieusement sur leurs
# valeurs par défaut.

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# .env de base : ne masque pas les variables déjà posées par le shell.
_env_path = _ROOT_DIR / '.env'
if _env_path.exists():
    load_dotenv(_env_path)

# .env.local : réglages personnels, prioritaires.
_env_local_path = _ROOT_DIR / '.env.local'
if _env_local_path.exists():
    load_dotenv(_env_local_path, override=True)

from .base import *  # noqa: E402,F401,F403

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
# 📧 EMAIL (DÉVELOPPEMENT)
# ============================================================
#
# Le transport par défaut, hérité de base.py, est le SMTP standard de Django :
# il marche avec le relais de n'importe quel hébergeur de messagerie. Trois
# réglages possibles via EMAIL_BACKEND :
#
#   - non défini            -> SMTP (identifiants obligatoires, voir plus bas)
#   - django...console...   -> affichage dans le terminal, aucun envoi réel
#   - core.backends...Brevo -> API transactionnelle Brevo (BREVO_API_KEY requise)
#
# BREVO_EMAIL_MODE=api|smtp reste accepté pour les .env.local existants.

from django.core.exceptions import ImproperlyConfigured

CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

_legacy_mode = (os.getenv("BREVO_EMAIL_MODE", "") or "").strip().lower()
if _legacy_mode not in ("", "api", "smtp"):
    raise ImproperlyConfigured("BREVO_EMAIL_MODE doit être vide, 'api' ou 'smtp'")
if _legacy_mode == "api" and not os.getenv("EMAIL_BACKEND"):
    EMAIL_BACKEND = BREVO_EMAIL_BACKEND  # noqa: F405

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "contact@nettoyageexpresse.fr")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Nettoyage Express")

if EMAIL_BACKEND == BREVO_EMAIL_BACKEND:  # noqa: F405
    if not BREVO_API_KEY:  # noqa: F405
        raise ImproperlyConfigured("EMAIL_BACKEND vise l'API Brevo mais BREVO_API_KEY est vide")
    # En dev on veut une erreur nette plutôt qu'un envoi qui « réussit » en
    # console sans jamais partir.
    BREVO_CONSOLE_FALLBACK = False
    print("[DEV] Email backend: Brevo (API)")

elif EMAIL_BACKEND == CONSOLE_EMAIL_BACKEND:
    print("[DEV] Email backend: console (aucun envoi réel)")

else:
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:  # noqa: F405
        raise ImproperlyConfigured(
            "Email non configuré en dev. Renseigne EMAIL_HOST, EMAIL_HOST_USER et "
            "EMAIL_HOST_PASSWORD dans .env.local (les anciens noms BREVO_SMTP_HOST, "
            "BREVO_SMTP_LOGIN et BREVO_SMTP_PASSWORD restent acceptés), ou pose "
            f"EMAIL_BACKEND={CONSOLE_EMAIL_BACKEND} pour travailler sans envoi."
        )

    # Evite les erreurs smtplib du type: UnicodeEncodeError ascii (auth_cram_md5).
    # Un identifiant SMTP est toujours ASCII : un accent trahit un copier-coller
    # qui a emporté du texte autour de la valeur.
    def _first_non_ascii(value: str):
        for idx, ch in enumerate(value):
            if ord(ch) > 127:
                return idx, ord(ch)
        return None

    _bad_user = _first_non_ascii(EMAIL_HOST_USER)  # noqa: F405
    _bad_pwd = _first_non_ascii(EMAIL_HOST_PASSWORD)  # noqa: F405
    if _bad_user or _bad_pwd:
        _where = "EMAIL_HOST_USER" if _bad_user else "EMAIL_HOST_PASSWORD"
        _idx, _codepoint = _bad_user or _bad_pwd
        raise ImproperlyConfigured(
            f"{_where} contient un caractère non-ASCII (index={_idx}, codepoint={_codepoint}). "
            "Recopie la valeur depuis ton hébergeur, sans accent, sans espace, sans texte autour."
        )

    print(f"[DEV] Email backend: SMTP ({EMAIL_HOST}:{EMAIL_PORT}) - Login: {EMAIL_HOST_USER}")  # noqa: F405

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
