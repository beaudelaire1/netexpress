"""Repositories bridging the domain and Django ORM.

These classes provide an interface between the pure domain objects and
the Django models used for persistence.  Application services depend
on these repositories rather than importing Django models directly.
"""

from __future__ import annotations

from typing import Iterable, Optional
from decimal import Decimal
from . import domain


class QuoteRepository:
    """Adapter for retrieving and updating quotes using Django ORM."""

    def get_by_id(self, quote_id: int):  # noqa: ANN001
        """Return the Django model instance for the given identifier.

        This method defers the import of the Quote model until runtime
        to avoid triggering configuration code when running tests or
        importing the repository in isolation.
        """
        try:
            from devis.models import Quote as QuoteModel
        except Exception:
            return None
        try:
            return QuoteModel.objects.get(pk=quote_id)
        except QuoteModel.DoesNotExist:
            return None

    def to_domain(self, quote_model) -> domain.Quote:  # noqa: ANN001
        """Map a Django Quote model to a domain Quote.

        The returned domain object contains copies of the most
        important fields (client name, items, dates and totals).  The
        link back to the Django model is not preserved in order to
        maintain the independence of the domain layer.
        """
        # Lazy import to avoid circular imports at module load time
        from devis.models import QuoteItem as QuoteItemModel
        # Build domain items
        domain_items = []
        for item in quote_model.quote_items.all():  # type: QuoteItemModel
            domain_items.append(
                domain.QuoteItem(
                    description=item.description or (item.service.name if item.service else ""),
                    quantity=item.quantity,
                    unit_price=Decimal(str(item.unit_price)),
                    tax_rate=Decimal(str(item.tax_rate)),
                )
            )
        dq = domain.Quote(
            client_name=quote_model.client.full_name,
            items=domain_items,
            issue_date=quote_model.issue_date,
            valid_until=quote_model.valid_until,
            total_ht=quote_model.total_ht,
            tva=quote_model.tva,
            total_ttc=quote_model.total_ttc,
        )
        return dq

    def update_totals(self, quote_model, domain_quote: domain.Quote) -> None:  # noqa: ANN001
        """Persist the totals of the domain quote back to the Django model."""
        quote_model.total_ht = domain_quote.total_ht
        quote_model.tva = domain_quote.tva
        quote_model.total_ttc = domain_quote.total_ttc
        quote_model.save(update_fields=["total_ht", "tva", "total_ttc"])

    def get_open_quotes(self) -> Iterable:
        """Return Django quote models that are not rejected."""
        try:
            from devis.models import Quote as QuoteModel
        except Exception:
            return []
        return QuoteModel.objects.exclude(status="rejected").order_by("-created_at")


class TaskRepository:
    """Adapter for retrieving tasks via Django ORM."""

    def get_uncompleted_tasks(self) -> Iterable:
        """Return Django task models that are not completed."""
        try:
            from tasks.models import Task as TaskModel
        except Exception:
            return []
        return TaskModel.objects.filter(completed=False).order_by("due_date")

    def to_domain(self, task_model) -> domain.Task:  # noqa: ANN001
        """Map a Django Task model to a domain Task entity."""
        return domain.Task(
            title=task_model.title,
            description=task_model.description,
            start_date=task_model.start_date,
            due_date=task_model.due_date,
            completed=task_model.completed,
        )