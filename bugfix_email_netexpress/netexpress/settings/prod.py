"""
Django settings for netexpress project - PRODUCTION CONFIGURATION
"""

from .base import *  # noqa
import os

# ============================================================
# ⚙️ MODE PRODUCTION
# ============================================================

DEBUG = False

# ============================================================
# 🔑 SECRET KEY (OBLIGATOIRE EN PROD)
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("❌ DJANGO_SECRET_KEY must be set in production environment!")

# ============================================================
# 🌍 HÔTES AUTORISÉS (CRITIQUE)
# ============================================================

# Récupérer les hôtes depuis la variable d'environnement
env_hosts_raw = os.getenv("ALLOWED_HOSTS", "")

if env_hosts_raw:
    # Si la variable d'environnement existe, parser et nettoyer
    env_hosts = [host.strip() for host in env_hosts_raw.split(",") if host.strip()]
    
    # Fusionner avec les hôtes de base.py (éviter les doublons)
    ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + env_hosts))
    print(f"✅ ALLOWED_HOSTS complété depuis ENV: {ALLOWED_HOSTS}")
else:
    # Garder les valeurs de base.py
    print(f"✅ ALLOWED_HOSTS depuis base.py: {ALLOWED_HOSTS}")

# ============================================================
# 🔐 CSRF TRUSTED ORIGINS (CRITIQUE)
# ============================================================

# Récupérer les origines CSRF depuis la variable d'environnement
env_csrf_raw = os.getenv("CSRF_TRUSTED_ORIGINS", "")

if env_csrf_raw:
    # Si la variable d'environnement existe, parser et nettoyer
    env_csrf = [origin.strip() for origin in env_csrf_raw.split(",") if origin.strip()]
    
    # Fusionner avec les origines de base.py (éviter les doublons)
    CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS + env_csrf))
    print(f"✅ CSRF_TRUSTED_ORIGINS complété depuis ENV: {CSRF_TRUSTED_ORIGINS}")
else:
    # Garder les valeurs de base.py
    print(f"✅ CSRF_TRUSTED_ORIGINS depuis base.py: {CSRF_TRUSTED_ORIGINS}")

# ============================================================
# 🔐 SÉCURITÉ HTTPS (RENDER)
# ============================================================

# Render est derrière un proxy HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Rediriger HTTP vers HTTPS
SECURE_SSL_REDIRECT = True

# Cookies sécurisés (HTTPS uniquement)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Autres en-têtes de sécurité
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# ============================================================
# 🗄️ BASE DE DONNÉES (POSTGRESQL SUR RENDER)
# ============================================================

# Parser l'URL de la base de données depuis Render
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ============================================================
# 📊 LOGGING EN PRODUCTION
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ============================================================
# 📧 EMAIL (OPTIONNEL - À CONFIGURER SELON VOS BESOINS)
# ============================================================

# Exemple avec un service SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# Configure SMTP for Infomaniak.  The default host points to
# mail.infomaniak.com and port 465.  Both values can be overridden via
# environment variables if needed (e.g. for another provider).
EMAIL_HOST = os.getenv('EMAIL_HOST', 'mail.infomaniak.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
# Use SSL on port 465; when SSL is enabled TLS must be disabled to
# avoid handshake issues.  The environment may override these defaults.
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
# DEFAULT_FROM_EMAIL must match EMAIL_HOST_USER for Infomaniak to
# accept outgoing messages.  It falls back to EMAIL_HOST_USER if the
# environment variable is not set.
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# ============================================================
# 🔥 DEBUG - AFFICHAGE FINAL DE LA CONFIG
# ============================================================

print("=" * 60)
print("🚀 PRODUCTION MODE ACTIVÉ")
print("=" * 60)
print(f"DEBUG: {DEBUG}")
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}")
print(f"DATABASE: {DATABASES['default']['NAME'] if 'NAME' in DATABASES['default'] else 'PostgreSQL'}")
print("=" * 60)
