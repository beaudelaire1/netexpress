"""
Initialisation de l'app ``services``.

Cette application représente la version modernisée du catalogue de
services de NetExpress.  Conçue en 2025, elle apporte une interface
    responsive, l’utilisation exclusive d’images locales (``static/img``) en
    fallback et une meilleure structuration du code.  Les vues filtrent
    uniquement les services actifs et les templates ont été travaillés pour
    offrir une expérience utilisateur de qualité sans dépendance à des
    bibliothèques externes comme Unsplash.
"""
default_app_config = 'services.apps.ServicesConfig'
