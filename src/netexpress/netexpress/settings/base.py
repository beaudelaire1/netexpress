from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security settings
# La clé secrète doit être fournie via les variables d'environnement en
# production. Une valeur par défaut est définie pour l'environnement de
# développement afin de démarrer rapidement sans erreur.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me-reworked")

# Enable debug during development only.  In production this should be set to False.
DEBUG = True

# Allow local hosts during development; adjust in production as required.
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Application definition
# Liste des applications installées.
#
# Pour améliorer l’interface d’administration, nous proposons une
# intégration facultative du thème Jazzmin.  Si django‑jazzmin est
# installé dans votre environnement (par exemple via `pip install
# django‑jazzmin`), il sera ajouté automatiquement en tête de
# INSTALLED_APPS.  Dans le cas contraire, l’administration utilisera
# l’interface standard de Django sans provoquer d’erreur.  Cela
# permet de bénéficier du tableau de bord amélioré sans imposer
# obligatoirement une dépendance dans tous les environnements.
INSTALLED_APPS = [
    # Django built‑in apps
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
    # Gestion des tâches
    "tasks",
]

# Insérer Jazzmin en premier si disponible.  Cela doit se faire après
# l’initialisation de la liste pour ne pas altérer l’ordre des
# applications internes.  L’import est encapsulé dans un bloc try
# pour éviter toute exception en l’absence du paquet.
try:
    import jazzmin  # type: ignore
    INSTALLED_APPS.insert(0, "jazzmin")
except Exception:
    # Jazzmin n’est pas installé ; on laisse la liste intacte.
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
        "DIRS": [BASE_DIR / "templates"],   # -> .../src/netexpress/templates
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
# Utiliser la localisation de l'utilisateur (Bucarest) pour une datation précise
TIME_ZONE = "Europe/Bucharest"
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
    "address": "123 Rue Principale\n97351 Matoury",
    "phone": "+594 594 00 00 00",
    # Coordonnées bancaires et légales pour la facturation (pied de page)
    "siret": "123 456 789 00012",
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
}
