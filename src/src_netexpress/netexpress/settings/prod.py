"""Production derrière le proxy HTTPS de Coolify ; les dépendances critiques échouent fermées."""

import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .runtime_validation import normalize_bic, normalize_iban


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} est obligatoire en production.")
    return value


def https_origin(name: str, value: str) -> str:
    origin = value.rstrip("/")
    parsed = urlparse(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ImproperlyConfigured(f"{name} doit être une origine HTTPS sans chemin ni paramètres.")
    return origin


DEBUG = False
SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Utilisez une DJANGO_SECRET_KEY aléatoire d’au moins 50 caractères.")

SITE_URL = https_origin("SITE_URL", required("SITE_URL"))
site = urlparse(SITE_URL)
ALLOWED_HOSTS = list(
    {
        site.hostname,
        "localhost",
        "127.0.0.1",
        *[
            value.strip()
            for value in os.getenv("ALLOWED_HOSTS", "").split(",")
            if value.strip()
        ],
    }
)
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS ne doit pas contenir de joker.")

_extra_csrf_origins = [
    value.strip()
    for value in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if value.strip()
]
CSRF_TRUSTED_ORIGINS = [SITE_URL] + [
    https_origin("CSRF_TRUSTED_ORIGINS", origin) for origin in _extra_csrf_origins
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^healthz/$", r"^readyz/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

DATABASES = {
    "default": dj_database_url.parse(
        required("DATABASE_URL"),
        conn_max_age=60,
        conn_health_checks=True,
    )
}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("PostgreSQL est obligatoire en production.")

REDIS_URL = required("REDIS_URL")
if urlparse(REDIS_URL).scheme not in {"redis", "rediss"}:
    raise ImproperlyConfigured("REDIS_URL doit utiliser redis:// ou rediss://.")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 86400
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
    }
}

EMAIL_BACKEND = "core.backends.brevo_backend.BrevoEmailBackend"
BREVO_API_KEY = required("BREVO_API_KEY")
BREVO_CONSOLE_FALLBACK = False
DEFAULT_FROM_EMAIL = required("DEFAULT_FROM_EMAIL")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Nettoyage Express")

TURNSTILE_REQUIRED = True
TURNSTILE_SITE_KEY = required("TURNSTILE_SITE_KEY")
TURNSTILE_SECRET_KEY = required("TURNSTILE_SECRET_KEY")

# Les factures de production ne doivent jamais être émises sans identité légale
# ni coordonnées de règlement. Les valeurs restent exclusivement dans l'environnement.
_company_siret = required("COMPANY_SIRET")
_bank_account_name = required("BANK_ACCOUNT_NAME")
_bank_iban = normalize_iban(required("BANK_ACCOUNT_NUMBER"))
_bank_bic = normalize_bic(os.getenv("COMPANY_BIC", ""))
INVOICE_BRANDING = {
    **INVOICE_BRANDING,
    "siret": _company_siret,
    "bank_account_name": _bank_account_name,
    "iban": _bank_iban,
    "bic": _bank_bic,
}

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media"))
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", "/app/private_media"))
if (
    MEDIA_ROOT.resolve() == PRIVATE_MEDIA_ROOT.resolve()
    or PRIVATE_MEDIA_ROOT.resolve().is_relative_to(MEDIA_ROOT.resolve())
):
    raise ImproperlyConfigured("Les pièces privées doivent être hors du répertoire média public.")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Variante tolérante : voir core.storage. Jazzmin référence un
        # répertoire que le manifeste ne peut pas contenir, ce qui rendait
        # /gestion/ inaccessible en 500.
        "BACKEND": "core.storage.ToleranteStaticFilesStorage"
    },
}

# Cloudinary reste optionnel pour les images publiques. Les FileField privés
# utilisent explicitement PrivateStorage et demeurent sur PRIVATE_MEDIA_ROOT.
if os.getenv("CLOUDINARY_CLOUD_NAME"):
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": required("CLOUDINARY_CLOUD_NAME"),
        "API_KEY": required("CLOUDINARY_API_KEY"),
        "API_SECRET": required("CLOUDINARY_API_SECRET"),
    }
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
    STORAGES["default"]["BACKEND"] = "cloudinary_storage.storage.MediaCloudinaryStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
    },
}
