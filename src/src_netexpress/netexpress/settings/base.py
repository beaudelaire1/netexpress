"""
Django settings for netexpress project - BASE CONFIGURATION
"""

import os
from pathlib import Path

# ============================================================
# 📂 CHEMINS DE BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# 🔑 SECRET KEY (DÉFAUT POUR DEV - OVERRIDÉ EN PROD)
# ============================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-this-in-production"
)

# ============================================================
# 🐛 DEBUG MODE (DÉFAUT - OVERRIDÉ PAR ENV)
# ============================================================

DEBUG = True

# ============================================================
# 🌍 HÔTES AUTORISÉS
# ============================================================

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'www.nettoyageexpresse.fr',
    'nettoyageexpresse.fr',
    'netexpress.onrender.com',
]

# ============================================================
# 🔐 CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'https://www.nettoyageexpresse.fr',
    'https://nettoyageexpresse.fr',
    'https://netexpress.onrender.com',
]

# ============================================================
# 📦 APPLICATIONS INSTALLÉES
# ============================================================

INSTALLED_APPS = [
    # Jazzmin DOIT être AVANT django.contrib.admin
    'jazzmin',

    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third-party apps
    'whitenoise.runserver_nostatic',
    'tinymce',
    'axes',

    # Project apps
    'core.apps.CoreConfig',
    'services.apps.ServicesConfig',
    'devis.apps.DevisConfig',
    'factures.apps.FacturesConfig',
    'contact.apps.ContactConfig',
    'tasks.apps.TasksConfig',
    'messaging.apps.MessagingConfig',
    'accounts.apps.AccountsConfig',
]

# ============================================================
# 🔐 CONFIGURATION D'AUTHENTIFICATION
# ============================================================

# URLs de redirection après connexion/déconnexion
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ============================================================
# 🎨 JAZZMIN CONFIGURATION
# ============================================================

JAZZMIN_SETTINGS = {
    # Titre et branding
    "site_title": "Nettoyage Express Admin",
    "site_header": "Nettoyage Express",
    "site_brand": "Nettoyage Express",
    "site_logo": "img/logo.svg",
    "login_logo": "img/logo.svg",
    "login_logo_dark": "img/logo.svg",
    "site_logo_classes": "img-circle",
    
    # Message d'accueil
    "welcome_sign": "Bienvenue dans l'administration de Nettoyage Express",
    
    # Copyright
    "copyright": "Nettoyage Express © 2024",
    
    # Recherche de modèles
    "search_model": ["auth.User", "devis.Quote", "factures.Invoice"],
    
    # Utilisateur en haut
    "user_avatar": None,
    
    # Liens dans le menu supérieur
    "topmenu_links": [
        {"name": "Site public", "url": "/", "new_window": True},
        {"name": "Dashboard Admin", "url": "/admin-dashboard/", "new_window": False},
        {"model": "auth.User"},
    ],
    
    # Afficher la barre latérale
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    
    # Ordre des apps
    "order_with_respect_to": [
        "auth",
        "devis",
        "factures", 
        "services",
        "tasks",
        "contact",
        "messaging",
        "accounts",
    ],
    
    # Icônes personnalisées
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "devis.Quote": "fas fa-file-contract",
        "devis.QuoteItem": "fas fa-list",
        "devis.Client": "fas fa-user-tie",
        "devis.QuoteRequest": "fas fa-inbox",
        "factures.Invoice": "fas fa-file-invoice-dollar",
        "factures.InvoiceItem": "fas fa-receipt",
        "services.Service": "fas fa-broom",
        "services.Category": "fas fa-tags",
        "services.ServiceTask": "fas fa-tasks",
        "contact.Message": "fas fa-envelope",
        "tasks.Task": "fas fa-clipboard-list",
        "messaging.EmailMessage": "fas fa-paper-plane",
        "accounts.Profile": "fas fa-id-card",
    },
    
    # Icône par défaut
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    
    # Liens personnalisés
    "custom_links": {
        "devis": [{
            "name": "Nouveau devis",
            "url": "/gestion/devis/quote/add/",
            "icon": "fas fa-plus",
        }],
        "factures": [{
            "name": "Nouvelle facture", 
            "url": "/gestion/factures/invoice/add/",
            "icon": "fas fa-plus",
        }],
    },
    
    # Interface utilisateur
    "related_modal_active": True,
    "custom_css": "css/jazzmin_overrides.css",
    "custom_js": "js/jazzmin_logout_fix.js",
    "use_google_fonts_cdn": False,  # RGPD/CNIL : pas de chargement de polices depuis un CDN tiers
    "show_ui_builder": False,
    
    # Changement de langue
    "language_chooser": False,
}

# Configuration de l'interface Jazzmin (couleurs Nettoyage Express)
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,  # Désactivé pour utiliser CSS personnalisé
    "accent": False,        # Désactivé pour utiliser CSS personnalisé
    "navbar": False,        # Désactivé pour utiliser CSS personnalisé
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": False,       # Désactivé pour utiliser CSS personnalisé
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
}

# ============================================================
# 🔧 MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.security_headers.SecurityHeadersMiddleware',  # CSP + Permissions-Policy
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.PermissionSyncMiddleware',  # Auto-sync permissions (must be after auth)
    'accounts.middleware.ForcePasswordChangeMiddleware',  # Force password change on first login
    'core.middleware.session_tracking.PortalSessionTrackingMiddleware',  # Analytics sessions portail
    'django.contrib.messages.middleware.MessageMiddleware',  # Doit être avant RoleBasedAccessMiddleware
    'accounts.middleware.RoleBasedAccessMiddleware',  # Add role-based access control
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',  # Brute-force protection (must be last auth-related)
]

# ============================================================
# 🌐 URL ET WSGI
# ============================================================

ROOT_URLCONF = 'netexpress.urls'
WSGI_APPLICATION = 'netexpress.wsgi.application'

# ============================================================
# 📄 TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'core.templatetags.legacy_filters',
            ],
        },
    },
]

# ============================================================
# 🗄️ BASE DE DONNÉES
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# 🔐 VALIDATION DES MOTS DE PASSE
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================
# 🌍 INTERNATIONALISATION
# ============================================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Cayenne'
USE_I18N = True
USE_TZ = True

# ============================================================
# 📁 FICHIERS STATIQUES
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Configuration WhiteNoise pour la compression et le cache
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# 📁 FICHIERS MÉDIAS
# ============================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# 📝 TINYMCE CONFIGURATION
# ============================================================

TINYMCE_DEFAULT_CONFIG = {
    'theme': 'silver',
    'height': 300,
    'menubar': False,
    'plugins': [
        'advlist', 'autolink', 'lists', 'link', 'charmap', 'preview',
        'searchreplace', 'visualblocks', 'code', 'fullscreen',
        'insertdatetime', 'table', 'wordcount'
    ],
    'toolbar': 'undo redo | formatselect | bold italic underline strikethrough | '
               'forecolor backcolor | alignleft aligncenter alignright alignjustify | '
               'bullist numlist outdent indent | link | removeformat',
    'content_css': 'default',
    'branding': False,
    'promotion': False,
    'license_key': 'gpl',
}

# Configuration simplifiée pour les messages
TINYMCE_MESSAGING_CONFIG = {
    'theme': 'silver',
    'height': 200,
    'menubar': False,
    'plugins': ['advlist', 'autolink', 'lists', 'link'],
    'toolbar': 'bold italic underline | forecolor | bullist numlist | link | removeformat',
    'content_css': 'default',
    'branding': False,
    'promotion': False,
    'license_key': 'gpl',
}

# ============================================================
# 🆔 TYPE DE CLÉ PRIMAIRE PAR DÉFAUT
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# 📧 CONFIGURATION EMAIL (optionnel)
# ============================================================

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
SITE_URL = (os.getenv('SITE_URL', '') or '').rstrip('/')

# ============================================================
# 📧 BREVO API CONFIGURATION
# ============================================================

# Brevo API configuration for transactional emails
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
USE_BREVO_API = bool(BREVO_API_KEY)

# ============================================================
# 🛡️ CLOUDFLARE TURNSTILE (anti-bot)
# ============================================================

TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

# ============================================================
# 🏢 BRANDING FACTURES/DEVIS
# ============================================================
#
# ⚠️ Les informations légales et bancaires (SIRET, TVA, IBAN, BIC) sont
# OBLIGATOIRES et doivent provenir de l'environnement (Dashboard Render),
# JAMAIS de valeurs codées en dur. Elles apparaissent sur les factures et
# devis PDF réels. En l'absence de variable d'environnement, les champs
# sensibles restent vides (aucune donnée factice n'est affichée).
# Variables attendues : COMPANY_NAME, COMPANY_EMAIL, COMPANY_PHONE,
# COMPANY_ADDRESS_LINE1, COMPANY_ADDRESS_LINE2, COMPANY_SIRET, COMPANY_TVA,
# BANK_ACCOUNT_NUMBER (IBAN), COMPANY_BIC, BANK_ACCOUNT_NAME.

_company_address_line1 = os.getenv("COMPANY_ADDRESS_LINE1", "753, Chemin de la Désirée")
_company_address_line2 = os.getenv("COMPANY_ADDRESS_LINE2", "97351 Matoury")
_company_address_lines = [line for line in (_company_address_line1, _company_address_line2) if line]

INVOICE_BRANDING = {
    "name": os.getenv("COMPANY_NAME", "Nettoyage Express"),
    "tagline": os.getenv("COMPANY_TAGLINE", "Espaces verts, nettoyage, peinture, bricolage"),
    "email": os.getenv("COMPANY_EMAIL", "contact@nettoyageexpresse.fr"),
    "logo_path": "static:img/logo.png",
    "address": "\n".join(_company_address_lines),
    "phone": os.getenv("COMPANY_PHONE", "05 94 30 23 68 / 06 94 46 20 12"),
    # Champs légaux / bancaires : aucune valeur factice par défaut.
    "siret": os.getenv("COMPANY_SIRET", ""),
    "tva_intra": os.getenv("COMPANY_TVA", ""),
    "iban": os.getenv("BANK_ACCOUNT_NUMBER", ""),
    "bic": os.getenv("COMPANY_BIC", ""),
    "bank_account_name": os.getenv("BANK_ACCOUNT_NAME", ""),
    "payment_terms": os.getenv("COMPANY_PAYMENT_TERMS", "Paiement comptant à réception de facture"),
    "default_notes": "Nous vous remercions de votre confiance.",
    "penalty_rate": os.getenv("COMPANY_PENALTY_RATE", "10%"),
    "address_lines": _company_address_lines,
}

# ============================================================
# 📊 LOGGING (POUR DEBUG)
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
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
    },
}

# ============================================================
# 🔄 CELERY CONFIGURATION (Background Tasks)
# ============================================================

# Celery settings for background task processing (notifications, emails)
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task routing
CELERY_TASK_ROUTES = {
    'messaging.tasks.*': {'queue': 'messaging'},
    'devis.tasks.*': {'queue': 'documents'},
    'factures.tasks.*': {'queue': 'documents'},
    'contact.tasks.*': {'queue': 'notifications'},
}

# Task time limits
CELERY_TASK_SOFT_TIME_LIMIT = 60  # 1 minute
CELERY_TASK_TIME_LIMIT = 120      # 2 minutes

# ============================================================
# 🛡️ DJANGO-AXES (brute-force protection)
# ============================================================

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5          # Lock after 5 failed attempts
AXES_COOLOFF_TIME = 1           # 1 hour cooloff
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True

# ============================================================
# 🧹 BLEACH — HTML sanitization (TinyMCE content)
# ============================================================

BLEACH_ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li',
    'a', 'span', 'h1', 'h2', 'h3', 'h4', 'table', 'thead',
    'tbody', 'tr', 'td', 'th',
]
BLEACH_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'span': ['style'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
}
BLEACH_STRIP_TAGS = True

# ============================================================
# 🗄️ CACHE (Redis en prod, mémoire locale en dev)
# ============================================================

REDIS_CACHE_URL = os.getenv('REDIS_CACHE_URL') or os.getenv('REDIS_URL')
USE_REDIS_CACHE = os.getenv('USE_REDIS_CACHE', '').lower() in ('1', 'true', 'yes', 'on')

if REDIS_CACHE_URL and USE_REDIS_CACHE:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_CACHE_URL,
        }
    }
else:
    # Fallback local pour éviter toute dépendance Redis en dev.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'netexpress-local-cache',
        }
    }

# Session engine backed by cache for performance
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'


