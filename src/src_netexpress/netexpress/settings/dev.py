"""
Django settings for netexpress project - DEVELOPMENT CONFIGURATION
"""

from .base import *  # noqa
import os

# ============================================================
# ⚙️ MODE DÉVELOPPEMENT
# ============================================================

DEBUG = True

# ============================================================
# 🌍 HÔTES AUTORISÉS EN DEV
# ============================================================

# Ajouter des hôtes locaux supplémentaires si nécessaire
ALLOWED_HOSTS += [
    '*.localhost',
    '*.127.0.0.1',
    '[::1]',  # IPv6 localhost
]

# ============================================================
# 🗄️ BASE DE DONNÉES (SQLITE EN DEV)
# ============================================================

# base.py utilise déjà SQLite par défaut, mais on peut le surcharger ici si besoin
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# 📧 EMAIL (CONSOLE EN DEV)
# ============================================================

# Afficher les emails dans la console au lieu de les envoyer
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================
# 🔧 DEBUG TOOLBAR (OPTIONNEL)
# ============================================================

# Si vous utilisez Django Debug Toolbar
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
    except ImportError:
        pass

# ============================================================
# 📊 LOGGING EN DÉVELOPPEMENT
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Voir les requêtes SQL
            'propagate': False,
        },
    },
}

# ============================================================
# 🔐 SÉCURITÉ (DÉSACTIVÉE EN DEV)
# ============================================================

# Pas de HTTPS forcé en dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ============================================================
# 🔥 DEBUG - AFFICHAGE DE LA CONFIG
# ============================================================

print("=" * 60)
print("🛠️  DEVELOPMENT MODE ACTIVÉ")
print("=" * 60)
print(f"DEBUG: {DEBUG}")
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"DATABASE: SQLite")
print("=" * 60)
