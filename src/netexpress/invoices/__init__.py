"""
Application ``invoices`` (legacy).

Cette application contient l’implémentation d’origine pour la gestion des
factures.  Elle subsiste pour compatibilité avec du code existant.  En
2025, nous avons amélioré la gestion des PDF pour signaler clairement
l’absence de la bibliothèque ReportLab plutôt que de générer une
exception technique et nous avons ajouté un ``verbose_name`` dans
``apps.py``.  Une migration vers l’app ``factures`` est recommandée.
"""