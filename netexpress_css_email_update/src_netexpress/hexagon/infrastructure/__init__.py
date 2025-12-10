"""Infrastructure adapters for NetExpress.

The infrastructure layer contains concrete implementations of the
abstract ports used by the application layer.  Here you will find
repositories that wrap Django models, gateways for sending e‑mails,
PDF generators and adapters for background task queues.  The goal is
to isolate the application logic from framework specifics.

Only a minimal set of adapters is provided in this initial version of
the hexagonal architecture.  As new features are implemented, new
adapters should be added to this layer.  Other layers must depend on
the abstractions defined here (e.g. repository interfaces) rather
than on Django models directly.
"""

from .repositories import QuoteRepository, TaskRepository

__all__ = ["QuoteRepository", "TaskRepository"]