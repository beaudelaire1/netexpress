"""
Application ``core`` – infrastructure du site NetExpress.

Cette app rassemble les vues générales (accueil, à propos) et la
configuration des URL racines.  En 2025, toutes les pages ont été
modernisées avec une interface responsive, des images locales libres de
droits (stockées dans ``static/img``) et des messages clairs.  Le
projet ne dépend plus de services externes comme Unsplash pour
l’illustration.
"""

# Importer explicitement les signaux ou registres lorsque nécessaire.