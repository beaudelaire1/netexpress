"""
Configuration Django pour l'environnement de PRODUCTION.

Ce fichier hérite de base.py et ajoute les paramètres de sécurité,
performance et monitoring nécessaires pour un déploiement professionnel.

IMPORTANT:
- Toutes les variables d'environnement doivent être configurées (voir .env.example)
- La base de données doit être PostgreSQL (DATABASE_URL)
- Redis doit être configuré pour Celery
- Certificat SSL/TLS requis
"""

from .base import *  # noqa
import os

# =============================================================================
# DEBUG & SÉCURITÉ DE BASE
# =============================================================================

DEBUG = False

# Les tests ne doivent JAMAIS tourner en mode production
TESTING = False

# Templates: ne pas afficher les erreurs détaillées
TEMPLATES[0]['OPTIONS']['debug'] = False

# =============================================================================
# SÉCURITÉ HTTPS / SSL
# =============================================================================

# Forcer HTTPS pour toutes les requêtes
SECURE_SSL_REDIRECT = True

# HSTS (HTTP Strict Transport Security)
# Force les navigateurs à utiliser HTTPS pendant 1 an
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True  # Permet inscription liste HSTS des navigateurs

# =============================================================================
# COOKIES SÉCURISÉS
# =============================================================================

# Cookies de session uniquement via HTTPS
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True  # Pas accessible en JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # Protection CSRF
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_COOKIE_NAME = 'netexpress_sessionid'  # Nom personnalisé

# Cookies CSRF sécurisés
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'netexpress_csrftoken'

# =============================================================================
# HEADERS DE SÉCURITÉ
# =============================================================================

# Empêcher le browser de deviner le content-type
SECURE_CONTENT_TYPE_NOSNIFF = True

# Protection XSS intégrée au navigateur
SECURE_BROWSER_XSS_FILTER = True

# Empêcher l'affichage dans une iframe (clickjacking)
X_FRAME_OPTIONS = 'DENY'

# Politique de referrer (ne pas envoyer URL complète à sites externes)
SECURE_REFERRER_POLICY = 'same-origin'

# Forcer proxy à rediriger en HTTPS si header X-Forwarded-Proto présent
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =============================================================================
# BASE DE DONNÉES
# =============================================================================

# En production, utiliser OBLIGATOIREMENT PostgreSQL via DATABASE_URL
# Exemple: postgresql://user:pass@host:5432/netexpress

if env('DATABASE_URL', default=None):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600,  # Connection pooling (10 minutes)
        conn_health_checks=True,  # Vérifier connexions avant utilisation
        ssl_require=True,  # Forcer SSL pour connexion DB
    )
else:
    # Fallback SQLite (générera WARNING au démarrage)
    pass

# =============================================================================
# CELERY PRODUCTION
# =============================================================================

# En production, Celery doit tourner en mode asynchrone
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# Optimisations Celery production
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Redémarrer worker après 1000 tâches
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # 1 tâche à la fois par worker
CELERY_TASK_ACKS_LATE = True  # ACK après exécution (pas avant)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Relancer si worker crash

# Retry automatique sur erreurs réseau
CELERY_TASK_AUTORETRY_FOR = (
    ConnectionError,
    TimeoutError,
)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute

# =============================================================================
# LOGGING PRODUCTION
# =============================================================================

# Créer dossier logs si n'existe pas
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

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

    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },

    'handlers': {
        # Fichier pour toutes les erreurs
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'django_errors.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },

        # Fichier pour tous les logs (INFO+)
        'file_all': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'django.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },

        # Email aux admins pour erreurs critiques
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'include_html': True,
        },

        # Console (utile pour Docker logs)
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'loggers': {
        # Logger Django principal
        'django': {
            'handlers': ['file_all', 'file_errors', 'console'],
            'level': 'INFO',
            'propagate': False,
        },

        # Logs de sécurité (tentatives CSRF, permissions, etc.)
        'django.security': {
            'handlers': ['file_errors', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },

        # Requêtes DB (mettre en WARNING en prod pour performances)
        'django.db.backends': {
            'handlers': ['file_all'],
            'level': 'WARNING',
            'propagate': False,
        },

        # Celery
        'celery': {
            'handlers': ['file_all', 'file_errors', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },

    # Logger root (catch-all)
    'root': {
        'handlers': ['console', 'file_all'],
        'level': 'INFO',
    },
}

# =============================================================================
# ADMINS & MANAGERS
# =============================================================================

# Emails pour notifications erreurs critiques
ADMINS = [
    ('Admin NetExpress', env('ADMIN_EMAIL', default='admin@example.com')),
]
MANAGERS = ADMINS

# Email "from" pour erreurs serveur
SERVER_EMAIL = env('SERVER_EMAIL', default='server@example.com')

# =============================================================================
# FICHIERS STATIQUES PRODUCTION
# =============================================================================

# WhiteNoise avec compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# MONITORING (Optionnel)
# =============================================================================

# Sentry pour monitoring erreurs (décommenter si configuré)
# if env('SENTRY_DSN', default=None):
#     import sentry_sdk
#     from sentry_sdk.integrations.django import DjangoIntegration
#     from sentry_sdk.integrations.celery import CeleryIntegration
#
#     sentry_sdk.init(
#         dsn=env('SENTRY_DSN'),
#         integrations=[DjangoIntegration(), CeleryIntegration()],
#         traces_sample_rate=0.1,
#         environment=env('ENVIRONMENT', default='production'),
#     )

print("✓ NetExpress - Configuration PRODUCTION chargée")
print(f"  - DEBUG: {DEBUG}")
print(f"  - ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"  - DATABASE: {DATABASES['default']['ENGINE']}")
print(f"  - HTTPS forcé: {SECURE_SSL_REDIRECT}")
print(f"  - Logs: {LOGS_DIR}")
