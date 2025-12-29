"""
Middleware de tracking des sessions de portails.

Objectif:
- Alimenter `core.models.PortalSession` (analytics) sans logique métier.
- Garder le tracking aligné avec la séparation des portails:
  - /client/  -> portal_type='client'
  - /worker/  -> portal_type='worker'
  - /admin-dashboard/ et /gestion/ -> portal_type='admin'
"""

from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin

from core.models import PortalSession
from core.portal_routing import get_portal_type_from_url


class PortalSessionTrackingMiddleware(MiddlewareMixin):
    """
    Track les sessions et pages visitées sur les URLs de portails.

    Notes:
    - On ne track que les utilisateurs authentifiés.
    - On ne track que les URLs appartenant à un portail NetExpress.
    - On mappe admin_dashboard/gestion -> 'admin' pour rester compatible avec le modèle existant.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        portal_area = get_portal_type_from_url(request.path)
        if not portal_area:
            return None

        portal_type = "admin" if portal_area in ("admin_dashboard", "gestion") else portal_area

        # Récupérer ou créer une session "active"
        session = (
            PortalSession.objects.filter(
                user=request.user,
                portal_type=portal_type,
                logout_time__isnull=True,
            )
            .order_by("-login_time")
            .first()
        )

        if session is None:
            session = PortalSession.start_session(request.user, portal_type, request)

        request.portal_session = session
        return None

    def process_response(self, request, response):
        session = getattr(request, "portal_session", None)
        if session is not None and 200 <= response.status_code < 400:
            session.increment_page_visit()
        return response


