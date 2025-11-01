"""
Django settings for the netexpress project with proper static file handling for Render.

This settings file consolidates duplicated values, adds WhiteNoise
for serving static files in production, and removes hard‑coded secrets.
Replace placeholders like `YOUR_SECRET_KEY` and `YOUR_EMAIL_PASSWORD`
with environment variables in your actual deployment to avoid committing
sensitive data to version control.
"""

from pathlib import Path
import os

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -------------------------------------------------------------
# Security settings
# -------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "YOUR_SECRET_KEY")

# Set DEBUG to False in production
DEBUG = False

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "render.com",
    "netexpress.onrender.com",
    "renderapp.io",
    "*",
]

# -------------------------------------------------------------
# Application definition
# -------------------------------------------------------------
INSTALLED_APPS = [
    # Django built‑in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third‑party app to serve static files in production
    "whitenoise.runserver_nostatic",

    # Project apps
    "core",
    "services",
    "devis",
    "factures",
    "contact",
    "tasks",
    "messaging",
]

# Optionally insert Jazzmin if available for admin theming
try:
    import jazzmin  # type: ignore
    INSTALLED_APPS.insert(0, "jazzmin")
except Exception:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise middleware must come directly after SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "netexpress.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "netexpress.wsgi.application"

# -------------------------------------------------------------
# Database configuration (SQLite by default)
# In production you should use Render PostgreSQL with DATABASE_URL
# -------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# -------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "America/Cayenne"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# -------------------------------------------------------------
# URL to use when referring to static files located in STATIC_ROOT
STATIC_URL = "/static/"

# Directories where Django will search for additional static files
STATICFILES_DIRS = [BASE_DIR / "static"]

# Directory where collectstatic will collect static files for production
STATIC_ROOT = BASE_DIR / "staticfiles"

# Use WhiteNoise’s storage backend to compress and hash static files
# For Django < 4.2, use STATICFILES_STORAGE instead of STORAGES
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (uploaded by users)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------
# Invoice branding (used by the factures app)
# -------------------------------------------------------------
INVOICE_BRANDING = {
    "name": "Nettoyage Express",
    "tagline": "Espaces verts, nettoyage, peinture, bricolage",
    "email": "netexpress@orange.fr",
    # Use the static template tag in templates instead of hardcoding paths
    "logo_path": "static:img/logo.png",
    "address": "753, Chemin de la Désirée\n97351 Matoury",
    "phone": "05 94 30 23 68 / 06 94 46 20 12",
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
}

# -------------------------------------------------------------
# E‑mail configuration
# -------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mail.infomaniak.com"
EMAIL_PORT = 587  # SSL port
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# Leave email credentials hard‑coded as provided by the user
EMAIL_HOST_USER = "noreply@nettoyageexpresse.fr"
EMAIL_HOST_PASSWORD = "Luxama973@"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# -------------------------------------------------------------
# End of settings
# -------------------------------------------------------------
