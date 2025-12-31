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
    print(f"[OK] ALLOWED_HOSTS complete depuis ENV: {ALLOWED_HOSTS}")
else:
    # Garder les valeurs de base.py
    print(f"[OK] ALLOWED_HOSTS depuis base.py: {ALLOWED_HOSTS}")

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
    print(f"[OK] CSRF_TRUSTED_ORIGINS complete depuis ENV: {CSRF_TRUSTED_ORIGINS}")
else:
    # Garder les valeurs de base.py
    print(f"[OK] CSRF_TRUSTED_ORIGINS depuis base.py: {CSRF_TRUSTED_ORIGINS}")

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
# 📧 EMAIL - CONFIGURATION BREVO (PRODUCTION)
# ============================================================

# Configuration Brevo (ex-Sendinblue) - Backend principal en production
BREVO_API_KEY = (os.getenv('BREVO_API_KEY') or '').strip()

# Utiliser le backend Brevo si la clé API est configurée
if BREVO_API_KEY and BREVO_API_KEY.startswith('xkeysib-'):
    EMAIL_BACKEND = 'core.backends.brevo_backend.BrevoEmailBackend'
    BREVO_CONSOLE_FALLBACK = False  # Pas de fallback en prod
    print("[OK] Email backend: Brevo (API) - Production")
elif BREVO_API_KEY:
    # Clé configurée mais format invalide
    EMAIL_BACKEND = 'core.backends.brevo_backend.BrevoEmailBackend'
    BREVO_CONSOLE_FALLBACK = False
    print(f"[WARN] BREVO_API_KEY configuree mais format suspect (ne commence pas par 'xkeysib-')")
    print("[WARN] Les cles API Brevo valides commencent par 'xkeysib-'")
else:
    # Pas de clé - utiliser console backend pour ne pas bloquer l'app
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("[WARN] ============================================")
    print("[WARN] BREVO_API_KEY non configuree!")
    print("[WARN] Les emails seront affiches dans la console.")
    print("[WARN] Pour activer les emails, configurez BREVO_API_KEY")
    print("[WARN] dans le Dashboard Render > Environment Variables")
    print("[WARN] ============================================")

# Configuration de l'expéditeur
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
DEFAULT_FROM_NAME = os.getenv('DEFAULT_FROM_NAME', 'Nettoyage Express')

# ============================================================
# 🔥 DEBUG - AFFICHAGE FINAL DE LA CONFIG
# ============================================================

