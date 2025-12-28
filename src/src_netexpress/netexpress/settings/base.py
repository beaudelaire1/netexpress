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

    # Third-party apps
    'whitenoise.runserver_nostatic',
    'ckeditor',
    'ckeditor_uploader',

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
    "custom_js": None,
    "use_google_fonts_cdn": True,
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # Doit être avant RoleBasedAccessMiddleware
    'accounts.middleware.RoleBasedAccessMiddleware',  # Add role-based access control
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
# 📝 CKEDITOR CONFIGURATION
# ============================================================

# CKEditor settings for WYSIWYG messaging
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_JQUERY_URL = 'https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ],
        'height': 200,
        'width': '100%',
        'toolbarCanCollapse': True,
        'forcePasteAsPlainText': True,
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
    },
    'messaging': {
        'toolbar': 'Messaging',
        'toolbar_Messaging': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList'],
            ['Link', 'Unlink'],
            ['RemoveFormat']
        ],
        'height': 150,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'forcePasteAsPlainText': True,
        'enterMode': 2,  # Use <br> instead of <p>
        'shiftEnterMode': 1,  # Use <p> for Shift+Enter
    },
    'admin': {
        'toolbar': 'Admin',
        'toolbar_Admin': [
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink', 'Anchor'],
            ['Image', 'Table', 'HorizontalRule'],
            ['TextColor', 'BGColor'],
            ['Smiley', 'SpecialChar'],
            ['RemoveFormat', 'Source']
        ],
        'height': 300,
        'width': '100%',
        'filebrowserWindowWidth': 940,
        'filebrowserWindowHeight': 725,
    }
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

# ============================================================
# 🏢 BRANDING FACTURES/DEVIS
# ============================================================

INVOICE_BRANDING = {
    "name": "Nettoyage Express",
    "tagline": "Espaces verts, nettoyage, peinture, bricolage",
    "email": "contact@nettoyageexpresse.fr",
    "logo_path": "static:img/logo.png",
    "address": "753, Chemin de la Désirée\n97351 Matoury",
    "phone": "05 94 30 23 68 / 06 94 46 20 12",
    "siret": "123 456 789 00012",
    "tva_intra": "FR1234567890",
    "iban": "FR76 3000 4000 1234 5678 9012 345",
    "bic": "NETEEXFRXXX",
    "payment_terms": "Paiement comptant à réception de facture",
    "default_notes": "Nous vous remercions de votre confiance.",
    "penalty_rate": "10%",
    "address_lines": [
        "753, Chemin de la Désirée",
        "97351 Matoury",
    ],
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


