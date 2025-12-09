"""Application services for NetExpress.

Application services coordinate domain entities through ports and
adapters.  They express the use cases of the system (e.g. computing
the totals for a quote, sending notifications for a task).  These
services depend on domain entities and on abstractions of the
infrastructure (repositories, gateways) but they do not depend on
Django directly.  This separation makes the business logic testable
without a database or web server.

When extending the project with new features, consider adding a
dedicated service here to encapsulate the necessary orchestration.
"""

from .services import QuoteService, TaskService

__all__ = ["QuoteService", "TaskService"]