"""
Django settings for netexpress project - TEST CONFIGURATION
"""

from .base import *  # noqa
import os

# ============================================================
# ⚙️ TEST MODE
# ============================================================

DEBUG = True

# ============================================================
# 🔑 SECRET KEY (TEST)
# ============================================================

SECRET_KEY = 'test-secret-key-not-for-production'

# ============================================================
# 🌍 HÔTES AUTORISÉS (TEST)
# ============================================================

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# ============================================================
# 🗄️ BASE DE DONNÉES (SQLITE POUR LES TESTS)
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
    }
}

# ============================================================
# 📧 EMAIL (TEST - CONSOLE BACKEND)
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# ============================================================
# 🔐 SÉCURITÉ (DISABLED FOR TESTS)
# ============================================================

# Disable security features for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# ============================================================
# 📊 LOGGING (MINIMAL FOR TESTS)
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Reduce log noise during tests
    },
}

# ============================================================
# 🧪 TEST-SPECIFIC SETTINGS
# ============================================================

# Flag to indicate we're in test mode
TESTING = True

# Speed up password hashing during tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test database creation
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Uncomment the line below to disable migrations during tests (faster but may miss migration issues)
# MIGRATION_MODULES = DisableMigrations()

print("[TEST] TEST MODE ACTIVATED - Using SQLite in-memory database")
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
if os.getenv("TEST_DATABASE_URL"):
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(os.environ["TEST_DATABASE_URL"])}
