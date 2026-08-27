"""Production behind the trusted Coolify HTTPS proxy; required services fail closed."""
from .base import *  # noqa
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse
import dj_database_url


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} est obligatoire en production.")
    return value


DEBUG = False
SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Utilisez une DJANGO_SECRET_KEY aléatoire d’au moins 50 caractères.")
SITE_URL = required("SITE_URL").rstrip("/")
site = urlparse(SITE_URL)
if site.scheme != "https" or not site.hostname or site.username or site.path:
    raise ImproperlyConfigured("SITE_URL doit être l’origine HTTPS publique, sans chemin.")
ALLOWED_HOSTS = list({site.hostname, "localhost", "127.0.0.1", *[v.strip() for v in os.getenv("ALLOWED_HOSTS", "").split(",") if v.strip()]})
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS ne doit pas contenir de joker.")
CSRF_TRUSTED_ORIGINS = [SITE_URL] + [v.strip() for v in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
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
DATABASES = {"default": dj_database_url.parse(required("DATABASE_URL"), conn_max_age=60, conn_health_checks=True)}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("PostgreSQL est obligatoire en production.")
REDIS_URL = required("REDIS_URL")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 86400
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL, "TIMEOUT": 300}}
EMAIL_BACKEND = "core.backends.brevo_backend.BrevoEmailBackend"
BREVO_API_KEY = required("BREVO_API_KEY")
BREVO_CONSOLE_FALLBACK = False
DEFAULT_FROM_EMAIL = required("DEFAULT_FROM_EMAIL")
DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "Nettoyage Express")
TURNSTILE_REQUIRED = True
TURNSTILE_SITE_KEY = required("TURNSTILE_SITE_KEY")
TURNSTILE_SECRET_KEY = required("TURNSTILE_SECRET_KEY")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media"))
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", "/app/private_media"))
if MEDIA_ROOT.resolve() == PRIVATE_MEDIA_ROOT.resolve() or PRIVATE_MEDIA_ROOT.resolve().is_relative_to(MEDIA_ROOT.resolve()):
    raise ImproperlyConfigured("Les pièces privées doivent être hors du répertoire média public.")
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
# Cloudinary is optional for public images only. Private FileFields use PrivateStorage explicitly.
if os.getenv("CLOUDINARY_CLOUD_NAME"):
    CLOUDINARY_STORAGE = {"CLOUD_NAME": required("CLOUDINARY_CLOUD_NAME"), "API_KEY": required("CLOUDINARY_API_KEY"), "API_SECRET": required("CLOUDINARY_API_SECRET")}
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
    STORAGES["default"]["BACKEND"] = "cloudinary_storage.storage.MediaCloudinaryStorage"
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "INFO"},
           "loggers": {"django.security": {"level": "WARNING"}, "django.request": {"level": "ERROR"}}}
