"""
Middleware d'accès NetExpress - Gestion des rôles, sessions et audit.
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseForbidden
from django.contrib import messages
import re
import logging

logger = logging.getLogger(__name__)


class RoleBasedAccessMiddleware:
    """
    Middleware pour contrôler l'accès aux portails basé sur les rôles utilisateur.
    
    Logique d'accès :
    - Superuser : UNIQUEMENT /gestion/ (interface technique)
    - Admin Technical : UNIQUEMENT /gestion/
    - Admin Business : /admin-dashboard/ + lecture /gestion/
    - Worker : UNIQUEMENT /worker/
    - Client : UNIQUEMENT /client/
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Patterns d'URLs par portail
        self.portal_patterns = {
            'gestion': re.compile(r'^/gestion/'),
            'admin_dashboard': re.compile(r'^/admin-dashboard/'),
            'worker': re.compile(r'^/worker/'),
            'client': re.compile(r'^/client/'),
        }
        
        # URLs publiques (accessibles à tous)
        self.public_urls = [
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/password-setup/',
            '/contact/',
            '/services/',
            '/devis/',
            '/static/',
            '/media/',
            '/ckeditor/',
            '/sitemap.xml',
            '/robots.txt',
            '/health/',
        ]
        
        # Patterns d'URLs publiques (racine du site)
        self.public_patterns = [
            re.compile(r'^/$'),  # Page d'accueil
            re.compile(r'^/a-propos/$'),
            re.compile(r'^/excellence/$'),
            re.compile(r'^/realisations/$'),
        ]
    
    def __call__(self, request):
        # Traitement avant la vue
        redirect_response = self._process_request(request)
        if redirect_response:
            return redirect_response
        
        # Traitement de la requête
        response = self.get_response(request)
        
        # Traitement après la vue
        self._process_response(request, response)
        
        return response
    
    def _process_request(self, request):
        """Traiter la requête avant qu'elle atteigne la vue."""
        path = request.path
        
        # Ignorer les URLs publiques
        if self._is_public_url(path):
            return None
        
        # Ignorer pour les utilisateurs anonymes (Django auth s'en charge)
        if isinstance(request.user, AnonymousUser):
            return None
        
        # Vérifier l'accès aux portails
        return self._check_portal_access(request)
    
    def _process_response(self, request, response):
        """Traiter la réponse après la vue."""
        # Mettre à jour l'heure de dernière activité
        if request.user.is_authenticated:
            self._update_user_activity(request)
    
    def _is_public_url(self, path):
        """Vérifier si une URL est publique."""
        if any(path.startswith(url) for url in self.public_urls):
            return True
        
        if any(pattern.match(path) for pattern in self.public_patterns):
            return True
        
        return False
    
    def _check_portal_access(self, request):
        """Vérifier l'accès aux portails selon les rôles."""
        path = request.path
        user = request.user
        user_role = self._get_user_role(user)
        
        # 1. Superuser/Admin technical -> /gestion/
        if user.is_superuser or user_role == 'admin_technical':
            if not self.portal_patterns['gestion'].match(path):
                return redirect('/gestion/')
            return None
        
        # 2. Admin business -> /admin-dashboard/ + lecture seule /gestion/
        if user_role == 'admin_business':
            if self.portal_patterns['gestion'].match(path):
                if request.method not in ['GET', 'HEAD', 'OPTIONS']:
                    messages.error(request, "Accès en lecture seule à l'interface technique.")
                    return redirect('/admin-dashboard/')
                return None
            elif not self.portal_patterns['admin_dashboard'].match(path):
                # Rediriger vers son dashboard s'il tente d'aller ailleurs (client/worker)
                if any(self.portal_patterns[p].match(path) for p in ['client', 'worker']):
                    return redirect('/admin-dashboard/')
            return None
        
        # 3. Worker -> /worker/
        if user_role == 'worker':
            if not self.portal_patterns['worker'].match(path):
                return redirect('/worker/')
            return None
        
        # 4. Client -> /client/
        if user_role == 'client':
            if not self.portal_patterns['client'].match(path):
                return redirect('/client/')
            return None
        
        return None
    
    def _get_user_role(self, user):
        """Récupérer le rôle utilisateur."""
        if user.is_superuser:
            return 'admin_technical'
        
        try:
            if hasattr(user, 'profile') and user.profile:
                return user.profile.role
        except Exception:
            pass
        
        # Fallbacks
        if user.is_staff:
            return 'admin_business'
        if user.groups.filter(name='Workers').exists():
            return 'worker'
        return 'client'

    def _update_user_activity(self, request):
        """Mettre à jour la date de dernière activité."""
        try:
            if hasattr(request.user, 'profile') and request.user.profile:
                request.user.profile.last_portal_access = timezone.now()
                request.user.profile.save(update_fields=['last_portal_access'])
        except Exception:
            pass


class PortalSessionMiddleware:
    """
    Middleware pour le suivi des sessions par portail.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            for portal, pattern in {
                'technical': re.compile(r'^/gestion/'),
                'business': re.compile(r'^/admin-dashboard/'),
                'worker': re.compile(r'^/worker/'),
                'client': re.compile(r'^/client/'),
            }.items():
                if pattern.match(path):
                    request.session['current_portal'] = portal
                    break
        
        return self.get_response(request)


class SecurityAuditMiddleware:
    """
    Middleware d'audit pour détecter les accès suspects.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.suspicious_patterns = [
            re.compile(r'/admin/'),  # Ancien admin
            re.compile(r'/dashboard/'),  # Ancien dashboard
        ]
    
    def __call__(self, request):
        path = request.path
        for pattern in self.suspicious_patterns:
            if pattern.match(path):
                logger.warning(f"Accès suspect détecté : {request.user} -> {path}")
        
        return self.get_response(request)


# Helpers
def get_user_portal_redirect_url(user):
    """URL de redirection selon le rôle."""
    if user.is_superuser: return '/gestion/'
    try:
        role = user.profile.role
        return {
            'admin_technical': '/gestion/',
            'admin_business': '/admin-dashboard/',
            'worker': '/worker/',
            'client': '/client/',
        }.get(role, '/client/')
    except Exception:
        return '/client/'
