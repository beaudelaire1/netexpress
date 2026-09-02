"""Static asset build only. Never use this module to serve requests."""
from .base import *  # noqa
DEBUG = False
SECRET_KEY = "build-only-not-a-runtime-secret"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
# Même stockage qu'en production, sans quoi le manifeste produit à la
# construction ne correspondrait pas à celui attendu à l'exécution.
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "core.storage.ToleranteStaticFilesStorage"}}
