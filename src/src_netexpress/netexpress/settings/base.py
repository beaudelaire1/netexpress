"""
Django settings for the netexpress project with proper static file handling for Render.

This settings file consolidates duplicated values, adds WhiteNoise
for serving static files in production, and removes hard‑coded secrets.
Replace placeholders like `YOUR_SECRET_KEY` and `YOUR_EMAIL_PASSWORD`
with environment variables in your actual deployment to avoid committing
sensitive data to version control.
""""""
Django base settings for NetExpress
Production-ready (Render compatible)
"""

from pathlib import Path
import os
import environ

# ============================================================
# 📁 BASE DIR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# 🌱 ENVIRONMENT
# ============================================================

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DEBUG=(bool, False),
)

env_path = BASE_DIR / ".env"
if env_path.exists():
    environ.Env.read_env(env_file=env_path)

# ============================================================
# 🔐 SECURITY
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is not set")

raw_debug = env("DJANGO_DEBUG", default=env("DEBUG", default=False))
if isinstance(raw_debug, str):
    DEBUG = raw_debug.strip().lower() in {"1", "true", "yes", "on"}
else:
    DEBUG = bool(raw_debug)

# ============================================================
# 🌍 ALLOWED HOSTS  (BUG FIX DÉFINITIF)
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# Sécurité : ne jamais démarrer en prod sans hosts
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS is empty in production")

# ============================================================
# 📦 APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",

    # Static files (prod)
    "whitenoise.runserver_nostatic",

    # Project apps
    "core",
    "services",
    "devis",
    "factures",
    "contact",
    "tasks",
    "messaging",
    "accounts",
]

# Optional Jazzmin
try:
    import jazzmin  # noqa
    INSTALLED_APPS.insert(0, "jazzmin")
except Exception:
    pass

# ============================================================
# 🧩 MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ============================================================
# 🌐 URLS / WSGI
# ============================================================

ROOT_URLCONF = "netexpress.urls"
WSGI_APPLICATION = "netexpress.wsgi.application"

# ============================================================
# 🎨 TEMPLATES
# ============================================================

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
            "builtins": [
                "core.templatetags.legacy_filters",
            ],
        },
    },
]

# ============================================================
# 🗄️ DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ============================================================
# 🌍 I18N / TIMEZONE
# ============================================================

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "America/Cayenne"
USE_I18N = True
USE_TZ = True

# ============================================================
# 📦 STATIC / MEDIA
# ============================================================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# 📧 EMAIL (SMTP INFOMANIAK)
# ============================================================

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="mail.infomaniak.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

CONTACT_RECEIVER_EMAIL = env(
    "CONTACT_RECEIVER_EMAIL", default=DEFAULT_FROM_EMAIL
)
TASK_NOTIFICATION_EMAIL = env(
    "TASK_NOTIFICATION_EMAIL", default=DEFAULT_FROM_EMAIL
)

# ============================================================
# ⚙️ CELERY (OPTIONNEL)
# ============================================================

CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default="redis://localhost:6379/0"
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ============================================================
# 🌐 SITE URL
# ============================================================

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# ============================================================
# 🧾 LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


from pathlib import Path
import os
import environ

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------
# Environment configuration
# --------------------------------------------------------------------
# Load environment variables from a .env file if present.  The
# ``django‑environ`` library converts values to the appropriate types.
env = environ.Env(
    # Compat: certains environnements utilisent DEBUG/ALLOWED_HOSTS
    # plutôt que DJANGO_DEBUG/DJANGO_ALLOWED_HOSTS.
    DJANGO_DEBUG=(bool, False),
    DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
env_path = BASE_DIR / ".env"
if env_path.exists():
    environ.Env.read_env(env_file=env_path)

# --------------------------------------------------------------------
# Security settings
# --------------------------------------------------------------------
# Secret key used for cryptographic signing.  It must be set via the
# environment.  If not provided, an exception is raised to avoid
# running with an insecure default.
SECRET_KEY = env("DJANGO_SECRET_KEY")

# Convert the DEBUG environment variable to a proper boolean.  Support
# common truthy/falsey strings in addition to booleans for robustness.
# Supporte DJANGO_DEBUG (préféré) puis DEBUG (compat .env).
raw_debug = env("DJANGO_DEBUG", default=env("DEBUG", default=True))
if isinstance(raw_debug, str):
    DEBUG = raw_debug.strip().lower() in {"1", "true", "yes", "on"}
else:
    DEBUG = bool(raw_debug)

# Parse ALLOWED_HOSTS from a comma‑separated string or a list.  If the
# environment provides a single string, split it on commas; otherwise
# assume it is already a list.  Empty values result in an empty list.
raw_hosts = env("DJANGO_ALLOWED_HOSTS", default=env("ALLOWED_HOSTS", default=""))
if isinstance(raw_hosts, str):
    ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = list(raw_hosts)

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

    "django.contrib.sitemaps",
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
    "accounts",
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
    "django.middleware.locale.LocaleMiddleware",
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
            # Register custom builtins so that the legacy filter 'length_is'
            # is available in all templates without requiring {% load %}.
            "builtins": [
                "core.templatetags.legacy_filters",
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
#
# Configuration du branding utilisée par l'application ``factures``.
# Le chemin du logo est maintenant résolu en valeur absolue grâce à
# ``Path`` afin de simplifier sa recherche lors de la génération du
# PDF.  Si vous placez votre logo ailleurs, ajustez ce chemin en
# conséquence.  Il est également possible de définir ``logo_path`` via
# une variable d'environnement dans votre fichier ``.env``.
INVOICE_BRANDING = {
    # Nom et slogan utilisés dans le header des documents
    "name": "Nettoyage Express",
    "tagline": "Espaces verts, nettoyage, peinture, bricolage",
    "email": "netexpress@orange.fr",
    # Chemin absolu vers le logo dans le dossier static du projet. Ce chemin
    # est utilisé par le template PDF ; ajustez‑le si votre logo est
    # ailleurs.
    "logo_path": str((BASE_DIR / "static" / "img" / "logo.png").resolve()),
    # Adresse de l'émetteur formatée sur plusieurs lignes (sera splittée)
    "address": "753, Chemin de la Désirée\n97351 Matoury",
    "phone": "05 94 30 23 68 / 06 94 46 20 12",
    # Coordonnées bancaires pour le pied de page
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
    # Mentions légales supplémentaires
    "siret": "123 456 789 00012",
    "tva_intra": "FR1234567890",
    # Conditions de paiement par défaut affichées si aucune valeur n'est
    # renseignée sur la facture elle‑même
    "payment_terms": "Paiement comptant à réception de facture",
    # Texte par défaut pour le champ notes si le champ est vide sur la facture
    "default_notes": "Nous vous remercions de votre confiance.",
    # Taux de pénalité de retard (affiché dans les mentions légales)
    "penalty_rate": "10%",
    # La liste d'adresses est dérivée de la chaîne ``address`` pour
    # permettre un rendu correct dans le template PDF (une ligne par
    # élément).  Si ``address`` change, mettez à jour cette liste en
    # conséquence.
    "address_lines": [
        "753, Chemin de la Désirée",
        "97351 Matoury",
    ],
}

# -------------------------------------------------------------
# E‑mail configuration
# -------------------------------------------------------------
# Configure e‑mail via environment variables.  By default we assume
# usage of SMTP over SSL on port 465.  If you need to adjust the
# parameters, define the corresponding variables in your ``.env`` file.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="mail.infomaniak.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)

EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="noreply@example.com")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER
)

# IMPORTANT : ne force PAS le backend console en DEBUG.
# Si vous voulez afficher les emails dans le terminal, définissez :
#   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# dans le fichier .env.

# Notification routing
TASK_NOTIFICATION_EMAIL = env(
    "TASK_NOTIFICATION_EMAIL", default=DEFAULT_FROM_EMAIL
)

# Exigence projet : aucune notification automatique (admin/client) en texte.
# Les e-mails sont envoyés uniquement sur action explicite (devis, messages).
TASK_NOTIFICATIONS_ENABLED = env.bool("TASK_NOTIFICATIONS_ENABLED", default=False)
ADMINS = [("Admin", TASK_NOTIFICATION_EMAIL)]
MANAGERS = ADMINS
# -------------------------------------------------------------
# Jazzmin configuration
# -------------------------------------------------------------
# Pour harmoniser l'interface d'administration avec l'identité visuelle de
# Nettoyage Express, nous appliquons ci‑dessous des réglages Jazzmin.
# Ces options personnalisent le titre, le logo, les icônes et la couleur
# principale de l'interface.  Jazzmin n'est activé que si installé.

JAZZMIN_SETTINGS = {
    # Entête et titre du site admin
    "site_title": "Nettoyage Express Admin",
    "site_header": "Nettoyage Express",
    "site_brand": "Nettoyage Express",
    # Logos (les chemins sont relatifs à static/)
    "site_logo": "img/logo.svg",
    "login_logo": "img/logo.svg",
    "login_logo_dark": "img/logo.svg",
    # Message d'accueil sur le tableau de bord
    "welcome_sign": "Bienvenue dans l'administration de Nettoyage Express",
    # Lien vers le site public depuis le menu supérieur
    "topmenu_links": [
        {"name": "Site public", "url": "/", "permissions": []},
    ],
    # Icônes personnalisées pour certains modèles
    "icons": {
        "factures.Invoice": "fas fa-file-invoice-dollar",
        "factures.InvoiceItem": "fas fa-list",
        "devis.Quote": "fas fa-file-contract",
        "services.Service": "fas fa-broom",
        "services.Category": "fas fa-tags",
        "contact.Message": "fas fa-envelope",
        "tasks.Task": "fas fa-clipboard-list",
    },
    # Ordre des applications dans la barre latérale
    "order_with_respect_to": ["factures", "devis", "services", "tasks", "contact", "messaging"],
    # Activer l'expansion de la navigation par défaut
    "navigation_expanded": True,
    # Activer l'affichage de la barre latérale
    "show_sidebar": True,
    # Couleur principale adaptée à la marque
    "theme_color": "#0B5D46",
    # Feuille de style supplémentaire pour des surcharges légères (définie dans static/css/jazzmin_overrides.css)
    "custom_css": "css/jazzmin_overrides.css",
}
# -------------------------------------------------------------
# End of settings
# -------------------------------------------------------------


# -------------------------------------------------------------
# Celery configuration (asynchronous emails, background jobs)
# -------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Default payment terms for documents (can be overridden per invoice/quote)
INVOICE_BRANDING.setdefault("payment_terms", "Paiement : 30 jours après démarrage des travaux.")


# Public URL of the site (used for email CTA links)
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# Enrich branding for emails (optional)
INVOICE_BRANDING.setdefault("site_url", SITE_URL)
# If you host a public logo URL for emails, set INVOICE_BRANDING["logo_url"]


# --- Logging (production-friendly) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
