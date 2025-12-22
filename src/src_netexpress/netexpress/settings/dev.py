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
# 📧 EMAIL (UTILISE LES VARIABLES D'ENVIRONNEMENT)
# ============================================================

# Utiliser la configuration email des variables d'environnement
# Si pas configuré, utiliser le backend console par défaut
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Configuration SMTP (pour Gmail ou autre)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Configuration Brevo (ex-Sendinblue)
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')

# Configuration de l'expéditeur
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
DEFAULT_FROM_NAME = os.getenv('DEFAULT_FROM_NAME', 'Nettoyage Express')

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

print("🛠️  MODE DÉVELOPPEMENT ACTIVÉ - SQLite")
print(f"DATABASE: {DATABASES['default']['NAME']}")
print(f"EMAIL_BACKEND: {EMAIL_BACKEND}")
if EMAIL_HOST_USER:
    print(f"EMAIL configuré avec: {EMAIL_HOST_USER}")
else:
    print("EMAIL: Mode console (pas de SMTP configuré)")
