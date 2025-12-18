"""
Django settings for netexpress project - BASE CONFIGURATION
"""

import os
from pathlib import Path

# ============================================================
# 📂 CHEMINS DE BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# 🔑 SECRET KEY (DÉFAUT POUR DEV - OVERRIDÉ EN PROD)
# ============================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-this-in-production"
)

# ============================================================
# 🐛 DEBUG MODE (DÉFAUT - OVERRIDÉ PAR ENV)
# ============================================================

DEBUG = True

# ============================================================
# 🌍 HÔTES AUTORISÉS
# ============================================================

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'www.nettoyageexpresse.fr',
    'nettoyageexpresse.fr',
    'netexpress.onrender.com',
]

# ============================================================
# 🔐 CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'https://www.nettoyageexpresse.fr',
    'https://nettoyageexpresse.fr',
    'https://netexpress.onrender.com',
]

# ============================================================
# 📦 APPLICATIONS INSTALLÉES
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Vos apps ici
]

# ============================================================
# 🔧 MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Pour les fichiers statiques
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# 🌐 URL ET WSGI
# ============================================================

ROOT_URLCONF = 'netexpress.urls'
WSGI_APPLICATION = 'netexpress.wsgi.application'

# ============================================================
# 📄 TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================
# 🗄️ BASE DE DONNÉES
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# 🔐 VALIDATION DES MOTS DE PASSE
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================
# 🌍 INTERNATIONALISATION
# ============================================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# ============================================================
# 📁 FICHIERS STATIQUES
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Configuration WhiteNoise pour la compression et le cache
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# 📁 FICHIERS MÉDIAS
# ============================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# 🆔 TYPE DE CLÉ PRIMAIRE PAR DÉFAUT
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# 📊 LOGGING (POUR DEBUG)
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
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
# 🔥 DEBUG - AFFICHAGE DE LA CONFIG AU CHARGEMENT
# ============================================================

print("🔥 BASE.PY CHARGÉ 🔥", __file__)
print(f"🔥 ALLOWED_HOSTS = {ALLOWED_HOSTS}")
print(f"🔥 CSRF_TRUSTED_ORIGINS = {CSRF_TRUSTED_ORIGINS}")
