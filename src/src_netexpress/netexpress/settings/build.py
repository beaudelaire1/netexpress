"""Static asset build only. Never use this module to serve requests."""
from .base import *  # noqa
DEBUG = False
SECRET_KEY = "build-only-not-a-runtime-secret"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
