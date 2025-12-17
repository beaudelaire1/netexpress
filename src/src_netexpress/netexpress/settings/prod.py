"""
Production settings for NetExpress.

Ces paramètres renforcent la sécurité et les performances pour un déploiement
en production. Ils héritent de base.py et ajoutent des configurations
spécifiques à l'environnement de production.
"""

from .base import *  # noqa

# =============================================================================
# Core Security Settings
# =============================================================================

# Désactiver le mode debug en production
DEBUG = False

# =============================================================================
# HTTPS / SSL Settings
# =============================================================================

# Redirection automatique HTTP -> HTTPS
SECURE_SSL_REDIRECT = True

# HTTP Strict Transport Security (HSTS)
# Indique aux navigateurs de n'utiliser que HTTPS pendant 1 an
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies sécurisés (HTTPS only)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# =============================================================================
# Additional Security Headers
# =============================================================================

# Protection contre le clickjacking
X_FRAME_OPTIONS = "DENY"

# Protection contre le MIME sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# Protection XSS du navigateur (déprécié mais encore utile pour anciens navigateurs)
SECURE_BROWSER_XSS_FILTER = True

# Referrer Policy - ne pas envoyer le referrer pour les requêtes cross-origin
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# =============================================================================
# Proxy Settings (pour déploiements derrière reverse proxy)
# =============================================================================

# Si derrière un proxy qui gère HTTPS (Nginx, Cloudflare, etc.)
# Décommentez la ligne suivante:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =============================================================================
# Database (Production)
# =============================================================================

# En production, utilisez PostgreSQL via DATABASE_URL
# La configuration est gérée dans base.py via dj-database-url

# =============================================================================
# Static Files (Production)
# =============================================================================

# WhiteNoise est configuré dans base.py pour servir les fichiers statiques
# En production avec compression:
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =============================================================================
# Email (Production)
# =============================================================================

# S'assurer que les emails ne sont pas envoyés en mode console
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# =============================================================================
# Logging (Production)
# =============================================================================

# En production, on peut ajouter un handler fichier ou un service externe
# La configuration de base est dans base.py
