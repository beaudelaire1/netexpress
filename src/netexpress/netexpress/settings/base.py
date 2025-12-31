from pathlib import Path
import os
import warnings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security settings
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me-reworked")
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Application definition
INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "core",
    "services",
    "devis",
    "factures",
    "contact",
    "tasks",
    "messaging",
]

# Activer Jazzmin si disponible
try:
    import jazzmin  # type: ignore
    INSTALLED_APPS.insert(0, "jazzmin")
except Exception:
    pass

# Activer Anymail si disponible (pour Brevo et autres services d'email)
try:
    import anymail  # type: ignore
    INSTALLED_APPS.append("anymail")
except Exception:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "America/Cayenne"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Branding factures ---
INVOICE_BRANDING = {
    "name": "Nettoyage Express",
    "tagline": "Espaces verts, nettoyage, peinture, bricolage",
    "email": "netexpress@orange.fr",
    "logo_path": "static:img/logo.png",
    # Adresse (chaque ligne sera affichée séparément dans le PDF)
    "address": "753, Chemin de la Désirée\n97351 Matoury",
    # Téléphones (fixe / mobile)
    "phone": "05 94 30 23 68 / 06 94 46 20 12",
    # Coordonnées bancaires (pied de page)
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
}

# ---------------------------------------------------------------------------
# Configuration e-mail
# ---------------------------------------------------------------------------
# Choix du backend email basé sur la variable d'environnement
# Supporte SMTP (Gmail, Zoho, etc.) ou Brevo API via django-anymail
EMAIL_BACKEND_TYPE = os.getenv("EMAIL_BACKEND_TYPE", "smtp").lower()

if EMAIL_BACKEND_TYPE == "brevo":
    # Configuration Brevo (ancien Sendinblue) via django-anymail
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    ANYMAIL = {
        "BREVO_API_KEY": os.getenv("BREVO_API_KEY", ""),
    }
    if not ANYMAIL["BREVO_API_KEY"]:
        warnings.warn(
            "BREVO_API_KEY n'est pas définie. "
            "L'envoi d'emails via Brevo échouera. "
            "Définissez la variable d'environnement BREVO_API_KEY."
        )
else:
    # Configuration SMTP standard (Gmail par défaut)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True").lower() == "true"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    if not EMAIL_HOST_PASSWORD:
        warnings.warn(
            "EMAIL_HOST_PASSWORD n'est pas définie. "
            "L'envoi d'emails via SMTP échouera. "
            "Définissez la variable d'environnement EMAIL_HOST_PASSWORD."
        )

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", os.getenv("EMAIL_HOST_USER", "noreply@example.com"))



# These settings are overridden in dev.py and prod.py
# --
