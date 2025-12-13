"""Domain layer definitions for NetExpress.

The domain layer contains the core business concepts of the
application.  Entities defined here should be expressed using plain
Python dataclasses or simple classes with minimal dependencies.  They
encapsulate business rules and validation logic and are designed to
remain independent of the persistence mechanism or the web framework.

For the initial version of the hexagonal architecture, the domain
layer exposes a handful of representative entities—``Service``,
``QuoteItem``, ``Quote`` and ``Task``—to illustrate how the existing
Django models can be mirrored in a framework‑agnostic way.  These
classes can be expanded and refined as the application evolves.
"""

from .models import Service, QuoteItem, Quote, Task

__all__ = ["Service", "QuoteItem", "Quote", "Task"]