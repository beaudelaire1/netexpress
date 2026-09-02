"""
Aiguillage commun des notifications par courriel.

Deux règles, valables pour tous les formulaires publics :

1. L'envoi est synchrone par défaut. Le confier à Celery suppose qu'un worker
   tourne réellement ; quand ce n'est pas le cas, la tâche reste en file et
   personne n'est jamais prévenu. ``NOTIFY_EMAILS_ASYNC=True`` rebascule sur
   Celery pour les déploiements qui en exploitent un.

2. Un échec est journalisé, jamais propagé jusqu'au visiteur. Sa demande est
   déjà enregistrée en base : il n'a pas à la ressaisir parce que notre relais
   de messagerie est en panne.
"""

from __future__ import annotations

import logging
from typing import Callable, Sequence

from django.conf import settings

logger = logging.getLogger(__name__)


def send_notification(
    label: str,
    send_now: Callable[..., None],
    args: Sequence = (),
    celery_task=None,
) -> bool:
    """
    Envoie une notification et indique si elle est partie.

    ``label`` sert uniquement aux journaux : il doit désigner l'objet notifié,
    par exemple ``"message de contact 42"``.
    """
    if celery_task is not None and getattr(settings, "NOTIFY_EMAILS_ASYNC", False):
        try:
            celery_task.delay(*args)
            return True
        except Exception:
            # Courtier injoignable : on bascule en synchrone plutôt que de
            # perdre la notification.
            logger.warning(
                "Mise en file Celery impossible (%s), envoi synchrone.",
                label,
                exc_info=True,
            )

    try:
        send_now(*args)
        return True
    except Exception:
        logger.exception("Échec de l'envoi de la notification (%s)", label)
        return False
