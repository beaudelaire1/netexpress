from .base import *  # noqa
import os

# ============================================================
# ⚙️ MODE PRODUCTION
# ============================================================

DEBUG = False

# ============================================================
# 🔐 SÉCURITÉ HTTPS (RENDER)
# ============================================================

# Render est derrière un proxy HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# ============================================================
# 🌍 HÔTES AUTORISÉS (CRITIQUE)
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# ============================================================
# 🔐 CSRF TRUSTED ORIGINS (CRITIQUE)
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# ============================================================
# 🔑 SECRET KEY (OBLIGATOIRE EN PROD)
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
