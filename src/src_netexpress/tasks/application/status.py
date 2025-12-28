from __future__ import annotations

from datetime import date
from typing import Optional

from tasks.domain.status import compute_task_status


def sync_task_status(task, *, today: Optional[date] = None, save_if_changed: bool = True) -> str:
    """Synchronise le statut d'une Task Django avec les règles métier.

    - Ne force jamais le statut si la tâche est déjà `completed`.
    - Met à jour la base (best-effort) si `save_if_changed` est True.
    """
    if getattr(task, "status", None) == "completed":
        return "completed"

    today = today or date.today()
    new_status = compute_task_status(
        start_date=getattr(task, "start_date", None),
        due_date=getattr(task, "due_date", None),
        today=today,
    )

    if new_status != getattr(task, "status", None):
        task.status = new_status
        if save_if_changed:
            task.save(update_fields=["status"])
    return new_status


