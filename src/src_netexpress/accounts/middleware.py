"""
Middleware d'accès NetExpress - Gestion des rôles, sessions et audit.
"""
import logging
import re

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .portal import get_portal_home_url, get_user_role
from .models import Profile

logger = logging.getLogger(__name__)


class PermissionSyncMiddleware:
    """
    Middleware qui synchronise automatiquement les permissions des utilisateurs.
    
    Ce middleware s'assure que:
    1. Chaque utilisateur a un profil
    2. Les permissions correspondent au rôle du profil
    3. is_staff est correctement configuré pour les admins
    
    Il utilise un flag en session pour éviter de vérifier à chaque requête.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and not isinstance(request.user, AnonymousUser):
            self._ensure_permissions_synced(request)
        
        return self.get_response(request)
    
    def _ensure_permissions_synced(self, request):
        """S'assure que les permissions de l'utilisateur sont synchronisées."""
        user = request.user
        
        # Vérifier si on a déjà synchronisé dans cette session
        sync_key = f'permissions_synced_{user.pk}'
        if request.session.get(sync_key):
            return
        
        try:
            # S'assurer que le profil existe
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': self._determine_initial_role(user)
                }
            )
            
            if created:
                logger.info(f"[MIDDLEWARE] Created profile for {user.username} with role={profile.role}")
            
            # Vérifier si les permissions sont correctes
            needs_sync = self._check_needs_sync(user, profile)
            
            if needs_sync:
                from .signals import setup_user_permissions
                setup_user_permissions(user, profile.role)
                logger.info(f"[MIDDLEWARE] Synced permissions for {user.username}")
            
            # Marquer comme synchronisé pour cette session
            request.session[sync_key] = True
            
        except Exception as e:
            logger.warning(f"[MIDDLEWARE] Error syncing permissions for {user.username}: {e}")
    
    def _determine_initial_role(self, user):
        """Détermine le rôle initial pour un nouvel utilisateur."""
        if user.is_superuser:
            return Profile.ROLE_ADMIN_TECHNICAL
        elif user.is_staff:
            return Profile.ROLE_ADMIN_BUSINESS
        return Profile.ROLE_CLIENT
    
    def _check_needs_sync(self, user, profile):
        """Vérifie si les permissions doivent être synchronisées."""
        role = profile.role
        
        # Admin technique doit être superuser et staff
        if role == Profile.ROLE_ADMIN_TECHNICAL:
            return not user.is_superuser or not user.is_staff
        
        # Admin business doit être staff mais pas superuser
        if role == Profile.ROLE_ADMIN_BUSINESS:
            return not user.is_staff
        
        # Worker et client ne doivent pas être staff
        if role in [Profile.ROLE_WORKER, Profile.ROLE_CLIENT]:
            return user.is_staff or user.is_superuser
        
        return False


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
        # Note: Les patterns acceptent maintenant les URLs avec ou sans trailing slash
        # pour éviter les problèmes de redirection en boucle sur les serveurs de production
        # (Render, nginx, etc.) où les requêtes peuvent arriver avant APPEND_SLASH
        self.portal_patterns = {
            'gestion': re.compile(r'^/gestion(/|$)'),
            'admin_dashboard': re.compile(r'^/admin-dashboard(/|$)'),
            'worker': re.compile(r'^/worker(/|$)'),
            'client': re.compile(r'^/client(/|$)'),
        }
        
        # URLs publiques (accessibles à tous)
        self.public_urls = [
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/password-setup/',
            '/gestion/logout/',  # Django Admin logout
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
        user_role = get_user_role(user)
        
        # 1. Superuser ou Admin technical -> accès à /gestion/ ET /admin-dashboard/
        if user.is_superuser or user_role == 'admin_technical':
            # Permettre l'accès à /gestion/ et /admin-dashboard/
            if self.portal_patterns['gestion'].match(path) or self.portal_patterns['admin_dashboard'].match(path):
                return None
            # Bloquer l'accès aux portails client/worker
            if any(self.portal_patterns[p].match(path) for p in ['client', 'worker']):
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
                return redirect(get_portal_home_url(user))
            return None
        
        # 4. Client -> /client/
        if user_role == 'client':
            if not self.portal_patterns['client'].match(path):
                return redirect(get_portal_home_url(user))
            return None
        
        return None
    
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
    return get_portal_home_url(user)
