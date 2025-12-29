"""
Décorateurs d'accès pour NetExpress - Contrôle par rôles et permissions.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from accounts.portal import get_user_role, redirect_to_user_portal

def redirect_to_appropriate_portal(user):
    """Compat: redirection vers le portail approprié."""
    return redirect_to_user_portal(user)


def technical_admin_required(view_func):
    """Accès réservé aux administrateurs techniques."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_user_role(request.user) == 'admin_technical':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès réservé aux administrateurs techniques.")
        raise PermissionDenied
    return wrapper


def business_admin_required(view_func):
    """Accès réservé aux administrateurs business."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_user_role(request.user) == 'admin_business':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès réservé aux administrateurs business.")
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def client_portal_required(view_func):
    """Accès réservé aux clients."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_user_role(request.user) == 'client':
            return view_func(request, *args, **kwargs)
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def worker_portal_required(view_func):
    """Accès réservé aux ouvriers."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_user_role(request.user) == 'worker':
            return view_func(request, *args, **kwargs)
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def role_required(*allowed_roles):
    """Décorateur générique pour vérifier les rôles autorisés."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_user_role(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"Accès refusé. Rôles autorisés : {', '.join(allowed_roles)}")
            return redirect_to_appropriate_portal(request.user)
        return wrapper
    return decorator


def user_has_permission(user, permission_codename):
    """
    Vérification simplifiée des permissions basée sur les rôles.
    """
    role = get_user_role(user)
    
    # Mapping temporaire rôle -> permissions
    role_permissions = {
        'admin_technical': ['*'],
        'admin_business': [
            'quotes.view', 'quotes.create', 'quotes.edit',
            'invoices.view', 'invoices.create', 'invoices.edit',
            'tasks.view', 'tasks.create', 'tasks.assign',
            'users.view', 'users.create', 'users.edit',
        ],
        'worker': ['tasks.view', 'tasks.complete'],
        'client': ['quotes.view', 'invoices.view'],
    }
    
    permissions = role_permissions.get(role, [])
    return '*' in permissions or permission_codename in permissions


def permission_required(permission_codename, raise_exception=False):
    """Vérification de permission granulaire."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if user_has_permission(request.user, permission_codename):
                return view_func(request, *args, **kwargs)
            
            if raise_exception:
                raise PermissionDenied
            
            messages.error(request, f"Permission insuffisante : {permission_codename}")
            return redirect_to_appropriate_portal(request.user)
        return wrapper
    return decorator


def admin_portal_required(view_func):
    """
    Décorateur pour les vues du portail admin business.
    
    Accès autorisé pour:
    - Users avec profile.role = 'admin_business'
    - Superusers (pour tests/support)
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # Vérifier le rôle admin_business
        role = get_user_role(user)
        if role == 'admin_business':
            return view_func(request, *args, **kwargs)
        
        # Rediriger vers le portail approprié
        return redirect_to_appropriate_portal(user)
    
    return wrapper


def portal_access_required(allowed_roles):
    """
    Décorateur générique : accès autorisé si le rôle de l'utilisateur appartient à allowed_roles.

    Exemple: @portal_access_required(['client', 'worker'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_user_role(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)
            return redirect_to_appropriate_portal(request.user)
        return wrapper
    return decorator


def ajax_portal_access_required(allowed_roles):
    """
    Variante AJAX : renvoie 403 au lieu d'une redirection si la requête est AJAX.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_user_role(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)

            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
            if is_ajax:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Accès refusé.")
            return redirect_to_appropriate_portal(request.user)
        return wrapper
    return decorator