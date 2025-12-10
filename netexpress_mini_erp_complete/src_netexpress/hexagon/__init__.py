"""Top‑level package for the hexagonal architecture of NetExpress.

This package groups the different layers of the application following
the principles of the hexagonal (also known as ports and adapters)
architecture.  The goal of this structure is to decouple the core
domain and application logic from external concerns such as the web
framework, the database, or third‑party services.  By doing so, the
business rules become easier to test, maintain and evolve independently
of the surrounding infrastructure.

Subpackages
-----------

domain
    Contains domain entities expressed as pure Python dataclasses or
    value objects.  These classes encapsulate business rules without
    depending on Django or any other library.  They mirror, but do
    not replace, the Django models defined in the various apps.  A
    repository layer is responsible for translating between domain
    objects and Django models.

application
    Contains use cases (application services) that orchestrate domain
    entities.  Application services coordinate repositories and other
    ports to perform complex operations.  They express the behaviour
    of the system at a high level and expose a simple API to the
    presentation layer.

infrastructure
    Contains adapters for external technologies (Django ORM, email
    backends, PDF generation, Celery tasks, etc.).  These classes
    implement interfaces defined in the domain or application layer
    and allow the core logic to remain agnostic of the underlying
    technology.

presentation
    Contains adapters that expose the application to users, such as
    Django views, REST API endpoints or CLI commands.  These
    components depend on the application layer but not vice versa.

This layout is intentionally flexible: it does not force a full
migration of all existing code but instead provides a new home for
future features to be built in a more modular way.  Existing Django
apps continue to function as before, and over time their logic can be
progressively extracted into the domain and application layers.  See
the subpackages for more details.
"""

from importlib import import_module

__all__ = ["domain", "application", "infrastructure", "presentation"]

def __getattr__(name: str):  # pragma: no cover
    """Lazily import subpackages to avoid circular imports.

    This convenience function allows ``hexagon.domain`` to be
    imported on demand when accessed as an attribute of the top‑level
    package.  It keeps the initial import cost low and avoids
    repeated imports.  See PEP 562 for the implementation pattern.

    :param name: Name of the submodule to import
    :raises AttributeError: if the requested attribute is unknown
    :return: the imported module
    """
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")