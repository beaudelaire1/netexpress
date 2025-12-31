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
    2. profile.role (SOURCE DE VÉRITÉ si explicitement défini à un rôle non-client)
    3. Fallback legacy : is_staff => admin_business ; groupe Workers => worker
    4. Par défaut : client
    
    Note: Le rôle 'client' dans le profil est traité comme "non configuré" si
    l'utilisateur a is_staff=True, pour permettre la compatibilité avec les
    utilisateurs existants qui n'ont pas été migrés.
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
    
    # PRIORITÉ 2: profile.role EST LA SOURCE DE VÉRITÉ pour les rôles admin/worker
    # Note: On traite 'client' séparément car c'est le défaut et on veut
    # permettre le fallback is_staff pour la compatibilité legacy
    if profile_role in [ROLE_ADMIN_BUSINESS, ROLE_ADMIN_TECHNICAL, ROLE_WORKER]:
        return profile_role
    
    # PRIORITÉ 3: Fallback legacy (pour utilisateurs avec profil client par défaut)
    # is_staff => admin_business (même si profile.role == 'client')
    if getattr(user, "is_staff", False):
        return ROLE_ADMIN_BUSINESS
    
    # Groupe Workers => worker (compatibilité legacy)
    try:
        if user.groups.filter(name="Workers").exists():
            return ROLE_WORKER
    except Exception:
        pass
    
    # PRIORITÉ 4: Utiliser le profile.role s'il est défini à 'client', sinon défaut
    if profile_role == ROLE_CLIENT:
        return ROLE_CLIENT

    # PRIORITÉ 5: Par défaut client
    return ROLE_CLIENT


def get_portal_home_url(user) -> str:
    """URL racine du portail correspondant au rôle utilisateur.
    
    Utilise get_user_role() comme source de vérité pour déterminer le portail.
    """
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
    
    Note: Accepte les URLs avec ou sans trailing slash pour éviter les problèmes
    de redirection en boucle sur les serveurs de production (Render, nginx, etc.)
    """
    # Vérifier avec ou sans trailing slash pour éviter les boucles de redirection
    if path.startswith("/client/") or path == "/client":
        return "client"
    if path.startswith("/worker/") or path == "/worker":
        return "worker"
    if path.startswith("/admin-dashboard/") or path == "/admin-dashboard":
        return "admin_dashboard"
    if path.startswith("/gestion/") or path == "/gestion":
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


