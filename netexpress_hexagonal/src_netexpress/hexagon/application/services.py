"""Application service classes for NetExpress.

These services implement high‑level use cases by coordinating domain
entities and infrastructure repositories.  They hide the details of
data access and persistence from the presentation layer.  New
features should be developed in this layer to promote separation of
concerns.
"""

from __future__ import annotations

from typing import Iterable
from . import domain


class QuoteService:
    """Service for operations related to quotes."""

    def __init__(self, repository: "QuoteRepository") -> None:
        self.repository = repository

    def compute_totals(self, quote_id: int) -> None:
        """Compute totals for the given quote and persist the results.

        This method retrieves the quote through its repository, maps it
        to a domain entity, computes the totals and writes the results
        back to persistence.  If the quote has no items, totals will
        remain zero.  This encapsulates the computation in one place.

        :param quote_id: Identifier of the quote in persistence
        """
        quote_model = self.repository.get_by_id(quote_id)
        if not quote_model:
            return
        domain_quote = self.repository.to_domain(quote_model)
        domain_quote.compute_totals()
        self.repository.update_totals(quote_model, domain_quote)

    def list_open_quotes(self) -> Iterable[domain.Quote]:
        """Return a list of non‑rejected quotes as domain entities."""
        for quote_model in self.repository.get_open_quotes():
            yield self.repository.to_domain(quote_model)


class TaskService:
    """Service for operations related to tasks."""

    def __init__(self, repository: "TaskRepository") -> None:
        self.repository = repository

    def list_due_tasks(self) -> Iterable[domain.Task]:
        """Return tasks that are due soon (within 7 days) and not completed."""
        for task_model in self.repository.get_uncompleted_tasks():
            domain_task = self.repository.to_domain(task_model)
            if domain_task.days_remaining() <= 7:
                yield domain_task