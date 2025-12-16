from .base import * # noqa
import os

DEBUG = True

# Forcer l'utilisation du SMTP (Gmail) au lieu de la console
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# On s'assure que ces variables sont bien lues
# Si le .env n'est pas chargé, cela plantera, ce qui nous confirmera le problème.
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')