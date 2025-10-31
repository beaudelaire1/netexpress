from pathlib import Path
import os

# ────────────────────────────────────────────────────────────────────────────────
# Chargement du .env (facultatif en local)
# ────────────────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv  # requirements: python-dotenv
    load_dotenv()
except Exception:
    pass

# ────────────────────────────────────────────────────────────────────────────────
# Répertoires de base
# Ce fichier est supposé être: src/netexpress/netexpress/settings/base.py
# BASE_DIR = src/netexpress
# ────────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ────────────────────────────────────────────────────────────────────────────────
# Paramètres de base / sécurité
# ────────────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = False

# Hostnames
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "netexpress.onrender.com",
    "render.com",
    "*",
]

# Render injecte souvent RENDER_EXTERNAL_HOSTNAME (ex: xxxx.onrender.com)
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)

# CSRF (schéma + domaine requis)
CSRF_TRUSTED_ORIGINS = [
    "https://netexpress.onrender.com",
    "https://nettoyage-express.fr",
    "https://www.nettoyage-express.fr",
     "https://www.render.com",
]
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

# ────────────────────────────────────────────────────────────────────────────────
# Applications
# ────────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # WhiteNoise: désactive le staticfiles dev de Django
    "whitenoise.runserver_nostatic",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Projet
    "core",
    "services",
    "devis",
    "factures",
    "contact",
    "tasks",
    "messaging",
]

# Jazzmin si dispo
try:
    import jazzmin  # noqa: F401
    INSTALLED_APPS.insert(0, "jazzmin")
except Exception:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise DOIT être juste après SecurityMiddleware
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

# ────────────────────────────────────────────────────────────────────────────────
# Base de données : Postgres (DATABASE_URL) ou SQLite par défaut
# ────────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # requirements: dj-database-url
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )

# ────────────────────────────────────────────────────────────────────────────────
# Internationalisation
# ────────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Cayenne")
USE_I18N = True
USE_L10N = True  # toléré sur 3.2
USE_TZ = True

# ────────────────────────────────────────────────────────────────────────────────
# Fichiers statiques & médias (WhiteNoise)
# ────────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"            # cible de collectstatic
STATICFILES_DIRS = [BASE_DIR / "static"]          # sources (ex: static/css, static/js)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Stockage optimisé pour la prod (manifest + compression)
#STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"


# ────────────────────────────────────────────────────────────────────────────────
# E-mail (configure via variables d’environnement)
# ────────────────────────────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = "vilmebeaudelaire5@gmail.com"
EMAIL_HOST_PASSWORD = "ymgx trrs tpqw kkwk"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Destinataires par défaut (optionnel)
CONTACT_RECEIVER_EMAIL = EMAIL_HOST_USER
TASK_NOTIFICATION_EMAIL = EMAIL_HOST_USER


# ────────────────────────────────────────────────────────────────────────────────
# Branding factures (existant)
# ────────────────────────────────────────────────────────────────────────────────
INVOICE_BRANDING = {
    "name": "Nettoyage Express",
    "tagline": "Espaces verts, nettoyage, peinture, bricolage",
    "email": os.getenv("BRAND_EMAIL", DEFAULT_FROM_EMAIL),
    "logo_path": "static:img/logo.png",
    "address": "753, Chemin de la Désirée\n97351 Matoury",
    "phone": "05 94 30 23 68 / 06 94 46 20 12",
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
}

# ────────────────────────────────────────────────────────────────────────────────
# Sécurité prod (activées automatiquement si DEBUG=False)
# ────────────────────────────────────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS (ajuste la durée après validation)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # X-Content-Type / XSS
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# ────────────────────────────────────────────────────────────────────────────────
# Logs (succincts mais utiles en prod)
# ────────────────────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

# ────────────────────────────────────────────────────────────────────────────────
# Paramètre par défaut pour les clés primaires
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
