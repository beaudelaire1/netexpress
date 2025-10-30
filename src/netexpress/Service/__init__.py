"""
Package ``Service`` – catalogue des services (version refondue 2025).

Cette application est un alias historique de l’app ``services``. Elle
subsiste pour conserver la rétro‑compatibilité avec d’anciens imports,
mais l’ensemble des fonctionnalités a été modernisé. Chaque modèle,
vue et template a été revu pour proposer une expérience utilisateur
agréable et responsive : descriptions enrichies, durées estimatives,
tarification transparente et images illustratives issues de la
photothèque libre de droits d’Unsplash【668280112401708†L16-L63】.  Les
URL sont générées automatiquement à partir des titres via la méthode
``get_absolute_url`` définie sur le modèle ``Service``.

Le code reste pleinement utilisable ; il s’appuie toutefois sur
l’app ``services`` comme référence pour la logique de présentation.  Il
est recommandé de migrer vos imports vers ``services`` à terme.
"""