"""
Décorateurs d'accès pour NetExpress - Contrôle par rôles et permissions.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def get_user_role(user):
    """
    Récupérer le rôle d'un utilisateur avec fallback.
    """
    if user.is_superuser:
        return 'admin_technical'
    
    try:
        if hasattr(user, 'profile') and user.profile:
            return user.profile.role
    except Exception:
        pass
    
    if user.is_staff:
        return 'admin_business'
    elif user.groups.filter(name='Workers').exists():
        return 'worker'
    else:
        return 'client'


def redirect_to_appropriate_portal(user):
    """
    Rediriger un utilisateur vers son portail approprié.
    """
    role = get_user_role(user)
    portal_urls = {
        'admin_technical': '/gestion/',
        'admin_business': '/admin-dashboard/',
        'worker': '/worker/',
        'client': '/client/',
    }
    return redirect(portal_urls.get(role, '/'))


def technical_admin_required(view_func):
    """Accès réservé aux administrateurs techniques."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or get_user_role(request.user) == 'admin_technical':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès réservé aux administrateurs techniques.")
        raise PermissionDenied
    return wrapper


def business_admin_required(view_func):
    """Accès réservé aux administrateurs business."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or get_user_role(request.user) == 'admin_business':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès réservé aux administrateurs business.")
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def client_portal_required(view_func):
    """Accès réservé aux clients."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or get_user_role(request.user) == 'client':
            return view_func(request, *args, **kwargs)
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def worker_portal_required(view_func):
    """Accès réservé aux ouvriers."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or get_user_role(request.user) == 'worker':
            return view_func(request, *args, **kwargs)
        return redirect_to_appropriate_portal(request.user)
    return wrapper


def role_required(*allowed_roles):
    """Décorateur générique pour vérifier les rôles autorisés."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser or get_user_role(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"Accès refusé. Rôles autorisés : {', '.join(allowed_roles)}")
            return redirect_to_appropriate_portal(request.user)
        return wrapper
    return decorator


def user_has_permission(user, permission_codename):
    """
    Vérification simplifiée des permissions basée sur les rôles.
    """
    if user.is_superuser:
        return True
    
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
        
        # Superusers ont accès pour support/tests
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Vérifier le rôle admin_business
        role = get_user_role(user)
        if role == 'admin_business':
            return view_func(request, *args, **kwargs)
        
        # Rediriger vers le portail approprié
        return redirect_to_appropriate_portal(user)
    
    return wrapper