"""
Template tags for portal navigation.

Provides unified navigation system with role-based menu items.
"""

from django import template
from django.urls import reverse
from core.portal_routing import (
    PortalRouter,
    get_portal_home_url,
    get_portal_messages_route as resolve_portal_messages_route,
    get_user_role,
)

register = template.Library()


@register.simple_tag
def portal_home_url(user):
    """Retourne l'URL du portail principal de l'utilisateur authentifié."""
    if not getattr(user, 'is_authenticated', False):
        return '/accounts/login/'
    return get_portal_home_url(user)


@register.simple_tag
def portal_messages_route(user, route_name='thread_list', *args):
    """Retourne une route de messagerie dans le namespace du portail courant."""
    if not getattr(user, 'is_authenticated', False):
        return '/accounts/login/'
    return resolve_portal_messages_route(user, route_name, *args)


@register.simple_tag(takes_context=True)
def portal_navigation(context):
    """
    Get portal navigation data based on user role.
    
    Returns navigation items appropriate for the current user's role.
    """
    request = context['request']
    user = request.user
    
    if not user.is_authenticated:
        return {
            'nav_items': [],
            'user_menu_items': [],
            'user': user,
            'request': request
        }
    
    role = get_user_role(user)
    router = PortalRouter(user)
    messages_url = router.get_messages_url()
    messages_base_url = resolve_portal_messages_route(user, 'list')
    
    # Base navigation items (common to all roles)
    nav_items = []
    
    # Role-specific navigation items
    if role == 'admin_business':
        nav_items = [
            {
                'label': 'Dashboard Admin',
                'url': '/admin-dashboard/',
                'icon': 'fas fa-tachometer-alt',
                'active_patterns': ['/admin-dashboard/']
            },
            {
                'label': 'Planning Global',
                'url': '/admin-dashboard/planning/',
                'icon': 'fas fa-calendar-alt',
                'active_patterns': ['/admin-dashboard/planning/']
            },
            {
                'label': 'Messages',
                'url': messages_url,
                'icon': 'fas fa-envelope',
                'active_patterns': [messages_base_url]
            },
            {
                'label': 'Gestion',
                'url': '/gestion/',
                'icon': 'fas fa-cogs',
                'active_patterns': ['/gestion/']
            }
        ]
    elif role == 'admin_technical':
        nav_items = [
            {
                'label': 'Dashboard Admin',
                'url': '/admin-dashboard/',
                'icon': 'fas fa-tachometer-alt',
                'active_patterns': ['/admin-dashboard/']
            },
            {
                'label': 'Planning Global',
                'url': '/admin-dashboard/planning/',
                'icon': 'fas fa-calendar-alt',
                'active_patterns': ['/admin-dashboard/planning/']
            },
            {
                'label': 'Messages',
                'url': messages_url,
                'icon': 'fas fa-envelope',
                'active_patterns': [messages_base_url]
            }
        ]
    elif role == 'worker':
        nav_items = [
            {
                'label': 'Mes Tâches',
                'url': '/worker/',
                'icon': 'fas fa-tasks',
                'active_patterns': ['/worker/']
            },
            {
                'label': 'Planning',
                'url': '/worker/schedule/',
                'icon': 'fas fa-calendar',
                'active_patterns': ['/worker/schedule/']
            },
            {
                'label': 'Messages',
                'url': messages_url,
                'icon': 'fas fa-envelope',
                'active_patterns': [messages_base_url]
            }
        ]
    else:  # client
        nav_items = [
            {
                'label': 'Mon Dashboard',
                'url': '/client/',
                'icon': 'fas fa-home',
                'active_patterns': ['/client/']
            },
            {
                'label': 'Mes Devis',
                'url': '/client/quotes/',
                'icon': 'fas fa-file-alt',
                'active_patterns': ['/client/quotes/']
            },
            {
                'label': 'Mes Factures',
                'url': '/client/invoices/',
                'icon': 'fas fa-receipt',
                'active_patterns': ['/client/invoices/']
            },
            {
                'label': 'Messages',
                'url': messages_url,
                'icon': 'fas fa-envelope',
                'active_patterns': [messages_base_url]
            }
        ]
    
    # Add active state to navigation items
    current_path = request.path
    for item in nav_items:
        item['is_active'] = any(
            current_path.startswith(pattern) 
            for pattern in item['active_patterns']
        )
    
    # User menu items (common to all authenticated users)
    user_menu_items = [
        {
            'label': 'Mon Profil',
            'url': reverse('accounts:profile'),
            'icon': 'fas fa-user'
        }
    ]
    
    # Add role-specific user menu items
    if role == 'admin_business':
        user_menu_items.insert(0, {
            'label': 'Dashboard Admin',
            'url': '/admin-dashboard/',
            'icon': 'fas fa-tachometer-alt'
        })
    elif role == 'admin_technical':
        user_menu_items.insert(0, {
            'label': 'Dashboard Admin',
            'url': '/admin-dashboard/',
            'icon': 'fas fa-tachometer-alt'
        })
        user_menu_items.insert(1, {
            'label': 'Interface technique',
            'url': '/gestion/',
            'icon': 'fas fa-cogs'
        })
    elif role == 'worker':
        user_menu_items.insert(0, {
            'label': 'Mon Dashboard',
            'url': '/worker/',
            'icon': 'fas fa-tasks'
        })
    else:  # client
        user_menu_items.insert(0, {
            'label': 'Mon Dashboard',
            'url': '/client/',
            'icon': 'fas fa-home'
        })
    
    return {
        'nav_items': nav_items,
        'user_menu_items': user_menu_items,
        'user': user,
        'request': request,
        'user_role': role
    }


@register.inclusion_tag('core/partials/portal_navigation.html', takes_context=True)
def render_portal_navigation(context):
    """
    Render the unified portal navigation based on user role.
    """
    nav_data = portal_navigation(context)
    return nav_data


@register.simple_tag(takes_context=True)
def portal_breadcrumb(context):
    """
    Generate breadcrumb navigation for portal pages.
    """
    request = context['request']
    user = request.user
    
    if not user.is_authenticated:
        return []
    
    path = request.path
    role = get_user_role(user)
    breadcrumbs = []
    
    # Add home breadcrumb
    if role == 'admin_business':
        breadcrumbs.append({
            'label': 'Dashboard Admin',
            'url': '/admin-dashboard/'
        })
    elif role == 'admin_technical':
        breadcrumbs.append({
            'label': 'Dashboard Admin',
            'url': '/admin-dashboard/'
        })
    elif role == 'worker':
        breadcrumbs.append({
            'label': 'Dashboard Worker',
            'url': '/worker/'
        })
    else:  # client
        breadcrumbs.append({
            'label': 'Dashboard Client',
            'url': '/client/'
        })
    
    # Add specific page breadcrumbs based on path
    if 'messages' in path:
        breadcrumbs.append({
            'label': 'Messages',
            'url': None  # Current page
        })
    elif 'quotes' in path:
        breadcrumbs.append({
            'label': 'Devis',
            'url': None
        })
    elif 'invoices' in path:
        breadcrumbs.append({
            'label': 'Factures',
            'url': None
        })
    elif 'schedule' in path:
        breadcrumbs.append({
            'label': 'Planning',
            'url': None
        })
    elif 'planning' in path:
        breadcrumbs.append({
            'label': 'Planning Global',
            'url': None
        })
    
    return breadcrumbs


@register.simple_tag
def portal_notification_count(user):
    """
    Get the count of unread notifications for a user.
    """
    if not user.is_authenticated:
        return 0
    
    try:
        from core.models import UINotification
        return UINotification.objects.filter(user=user, read=False).count()
    except ImportError:
        return 0


@register.filter
def user_role(user):
    """
    Template filter to get user role.
    """
    return get_user_role(user)


@register.simple_tag(takes_context=True)
def portal_quick_actions(context):
    """
    Generate quick action buttons based on user role.
    """
    request = context['request']
    user = request.user
    
    if not user.is_authenticated:
        return []
    
    role = get_user_role(user)
    actions = []
    
    if role == 'admin_business':
        actions = [
            {
                'label': 'Nouveau Devis',
                'url': reverse('core:admin_create_quote'),
                'icon': 'fas fa-plus',
                'class': 'btn-primary'
            },
            {
                'label': 'Nouvelle Tâche',
                'url': reverse('core:admin_create_task'),
                'icon': 'fas fa-tasks',
                'class': 'btn-secondary'
            }
        ]
    elif role == 'admin_technical':
        actions = [
            {
                'label': 'Nouvelle Tâche',
                'url': reverse('core:admin_create_task'),
                'icon': 'fas fa-tasks',
                'class': 'btn-primary'
            },
            {
                'label': 'Planning Global',
                'url': reverse('core:admin_global_planning'),
                'icon': 'fas fa-calendar-alt',
                'class': 'btn-secondary'
            }
        ]
    elif role == 'worker':
        actions = [
            {
                'label': 'Marquer Tâche Terminée',
                'url': '#',
                'icon': 'fas fa-check',
                'class': 'btn-success',
                'onclick': 'showCompleteTaskModal()'
            }
        ]
    else:  # client
        actions = [
            {
                'label': 'Nouveau Devis',
                'url': reverse('devis:request_quote'),
                'icon': 'fas fa-file-alt',
                'class': 'btn-primary'
            },
            {
                'label': 'Nouveau Message',
                'url': '/client/messages/compose/',
                'icon': 'fas fa-envelope',
                'class': 'btn-secondary'
            }
        ]
    
    return actions