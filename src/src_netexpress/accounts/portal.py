"""
Source de vérité : rôles applicatifs NetExpress et routing vers les portails.

Objectif:
- Centraliser la logique "user -> rôle" et "rôle -> URL portail"
- Éviter les duplications entre middleware / decorators / routing
"""

from __future__ import annotations

from django.shortcuts import redirect


# Rôles applicatifs (cf. accounts.models.Profile)
ROLE_CLIENT = "client"
ROLE_WORKER = "worker"
ROLE_ADMIN_BUSINESS = "admin_business"
ROLE_ADMIN_TECHNICAL = "admin_technical"


def get_user_role(user) -> str:
    """
    Déterminer le rôle applicatif d'un utilisateur.

    Convention NetExpress (ORDRE DE PRIORITÉ):
    1. Superuser => admin_technical (sauf si profile.role = admin_business)
    2. profile.role (SOURCE DE VÉRITÉ pour les non-superusers)
    3. Fallback legacy : is_staff => admin_business ; groupe Workers => worker
    4. Par défaut : client
    """
    # Récupérer le profile.role s'il existe
    profile_role = None
    try:
        profile = getattr(user, "profile", None)
        if profile:
            profile_role = getattr(profile, "role", None)
    except Exception:
        pass
    
    # PRIORITÉ 1: Superuser
    if getattr(user, "is_superuser", False):
        # Un superuser peut avoir un rôle admin_business explicite
        if profile_role == ROLE_ADMIN_BUSINESS:
            return ROLE_ADMIN_BUSINESS
        # Par défaut, superuser = admin_technical
        return ROLE_ADMIN_TECHNICAL
    
    # PRIORITÉ 2: profile.role EST LA SOURCE DE VÉRITÉ
    # Si le rôle est explicitement défini dans le profil, l'utiliser
    if profile_role and profile_role in [ROLE_ADMIN_BUSINESS, ROLE_ADMIN_TECHNICAL, ROLE_WORKER, ROLE_CLIENT]:
        return profile_role
    
    # PRIORITÉ 3: Fallback legacy (pour utilisateurs sans profil configuré)
    # is_staff sans rôle explicite => admin_business
    if getattr(user, "is_staff", False):
        return ROLE_ADMIN_BUSINESS
    
    # Groupe Workers => worker (compatibilité legacy)
    try:
        if user.groups.filter(name="Workers").exists():
            return ROLE_WORKER
    except Exception:
        pass

    # PRIORITÉ 4: Par défaut client
    return ROLE_CLIENT


def get_portal_home_url(user) -> str:
    """URL racine du portail correspondant au rôle utilisateur.
    
    Les superusers sont redirigés vers /admin-dashboard/ (interface métier complète)
    car ils ont accès aux deux interfaces (/gestion/ et /admin-dashboard/).
    """
    # Superusers -> interface business complète par défaut
    if getattr(user, "is_superuser", False):
        return "/admin-dashboard/"
    
    role = get_user_role(user)
    return {
        ROLE_ADMIN_TECHNICAL: "/gestion/",
        ROLE_ADMIN_BUSINESS: "/admin-dashboard/",
        ROLE_WORKER: "/worker/",
        ROLE_CLIENT: "/client/",
    }.get(role, "/")


def redirect_to_user_portal(user):
    """Réponse HTTP de redirection vers le portail approprié."""
    return redirect(get_portal_home_url(user))


def redirect_after_login(user) -> str:
    """URL de redirection après login."""
    return get_portal_home_url(user)


def get_portal_area_from_url(path: str) -> str | None:
    """
    Déterminer la "zone portail" (pour contrôle d'accès / routing).

    Retourne: 'client' | 'worker' | 'admin_dashboard' | 'gestion' | None
    """
    if path.startswith("/client/"):
        return "client"
    if path.startswith("/worker/"):
        return "worker"
    if path.startswith("/admin-dashboard/"):
        return "admin_dashboard"
    if path.startswith("/gestion/"):
        return "gestion"
    return None


def is_portal_url(path: str) -> bool:
    """Vrai si l'URL appartient à un des portails NetExpress."""
    return get_portal_area_from_url(path) is not None


def user_can_access_portal_area(user, portal_area: str) -> bool:
    """
    Vérifier si l'utilisateur peut accéder à une zone portail.

    NB: la règle "lecture seule /gestion/ pour admin_business" est gérée au middleware
    (car dépend de la méthode HTTP). Ici on répond uniquement sur l'accès global.
    """
    role = get_user_role(user)

    if role == ROLE_ADMIN_TECHNICAL:
        return portal_area == "gestion"

    if role == ROLE_ADMIN_BUSINESS:
        return portal_area in {"admin_dashboard", "gestion"}

    if role == ROLE_WORKER:
        return portal_area == "worker"

    return portal_area == "client"


