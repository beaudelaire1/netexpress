"""Application de messagerie interne.

Ce module centralise la gestion et l'envoi de messages e‑mail internes
et externes.  Les messages sont stockés dans la base de données et
peuvent être visualisés depuis le tableau de bord ou l'interface
d'administration.  Les e‑mails sont envoyés via le service SMTP
configuré dans les paramètres du projet.
"""

__all__ = ["apps"]