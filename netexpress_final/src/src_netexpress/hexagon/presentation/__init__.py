"""Presentation adapters for NetExpress.

This package is reserved for user‑facing adapters such as web views,
API endpoints or command‑line interfaces.  These components convert
incoming requests into calls to application services and translate
responses back into HTML, JSON or other formats.  In the current
project the existing Django views continue to live in their respective
apps (``contact``, ``devis``, ``services``, etc.).  New features may
choose to define their views here to emphasise the separation between
presentation and business logic.

At this stage the package contains no concrete implementation and
serves as a placeholder for future growth.
"""