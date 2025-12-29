"""
Django settings for netexpress project - LOCAL DEVELOPMENT CONFIGURATION
"""

from .base import *  # noqa
import os

# ============================================================
# ⚙️ MODE DÉVELOPPEMENT LOCAL
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
# 📧 EMAIL (CONSOLE BACKEND POUR LE DÉVELOPPEMENT)
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
# DEBUG - AFFICHAGE FINAL DE LA CONFIG
# ============================================================

print("=" * 60)
print("[LOCAL] MODE DEVELOPPEMENT LOCAL ACTIVE")
print("=" * 60)
print(f"DEBUG: {DEBUG}")
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"DATABASE: SQLite (db.sqlite3)")
print("=" * 60)