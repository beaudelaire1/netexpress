"""Utilitaires de copie pour les e-mails de NOTIFICATION ADMINISTRATIVE.

Ce module centralise le calcul des destinataires en copie (CC visible et CCI
cachée) appliqués aux e-mails internes destinés à l'administration du site
(par exemple la réception d'un message de contact).

Il ne s'applique **pas** aux e-mails envoyés aux clients (factures, devis).

Pendant la période de garantie (jusqu'à ``settings.REVIEW_COPY_UNTIL``),
l'adresse ``settings.REVIEW_COPY_EMAIL`` est ajoutée automatiquement en copie
afin de permettre l'évaluation de la qualité du service.  Au-delà de cette
date, plus aucune copie de garantie n'est ajoutée, sans modification de code.
"""

from __future__ import annotations

import datetime
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _within_guarantee() -> bool:
    """Retourne ``True`` si la date du jour est dans la période de garantie."""
    raw = getattr(settings, "REVIEW_COPY_UNTIL", "") or ""
    if not raw:
        return False
    try:
        until = datetime.date.fromisoformat(str(raw).strip())
    except ValueError:
        logger.warning("REVIEW_COPY_UNTIL invalide (%r), copie de garantie ignorée.", raw)
        return False
    return datetime.date.today() <= until


def notification_copies() -> tuple[list[str], list[str]]:
    """Calcule les listes ``(cc, bcc)`` pour les notifications administratives.

    - ``cc`` : ``settings.NOTIFICATION_CC`` + adresse de garantie (si active).
    - ``bcc`` : ``settings.NOTIFICATION_BCC`` + adresse de garantie (si active).

    Les doublons sont supprimés en préservant l'ordre.
    """
    cc = list(getattr(settings, "NOTIFICATION_CC", []) or [])
    bcc = list(getattr(settings, "NOTIFICATION_BCC", []) or [])

    review_email = getattr(settings, "REVIEW_COPY_EMAIL", "") or ""
    if review_email and _within_guarantee():
        # Pendant la garantie : copie visible (CC) et copie cachée (CCI).
        cc.append(review_email)
        bcc.append(review_email)

    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    return _dedupe(cc), _dedupe(bcc)
