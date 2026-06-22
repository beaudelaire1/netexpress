from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = False

# --------------------------------------------------------------------
# HTTPS / TLS
# --------------------------------------------------------------------
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Derrière un reverse proxy (Render, etc.) le TLS est terminé par le proxy.
# Sans cet en-tête, ``SECURE_SSL_REDIRECT`` provoque une boucle de redirection.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --------------------------------------------------------------------
# En-têtes de sécurité supplémentaires
# --------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Origines de confiance pour la protection CSRF (https://example.com,...).
# À renseigner via la variable d'environnement DJANGO_CSRF_TRUSTED_ORIGINS.
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# --------------------------------------------------------------------
# Fichiers statiques : manifest activé uniquement en production
# (nécessite ``python manage.py collectstatic`` au déploiement).
# --------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
