from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class TaskDates:
    start_date: Optional[date]
    due_date: Optional[date]


def compute_task_status(*, start_date: Optional[date], due_date: Optional[date], today: date) -> str:
    """Calcule le statut d'une tâche à partir des dates.

    Règles (alignées avec le comportement historique):
    - Si `due_date` est passée -> overdue
    - Si `due_date` est aujourd'hui ou demain -> almost_overdue
    - Si `start_date` est dans le futur -> upcoming
    - Sinon -> in_progress
    """
    if due_date and due_date < today:
        return "overdue"
    if due_date and (due_date - today).days <= 1:
        return "almost_overdue"
    if start_date and start_date > today:
        return "upcoming"
    return "in_progress"


def validate_task_dates(*, start_date: Optional[date], due_date: Optional[date]) -> None:
    if start_date and due_date and due_date < start_date:
        raise ValueError("La date d'échéance ne peut pas être antérieure à la date de début.")


