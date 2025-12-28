"""
Template tags pour les URLs de notifications selon le portail.
"""

from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag(takes_context=True)
def notification_count_url(context):
    """Obtenir l'URL correcte pour notification_count selon le portail actuel."""
    request = context.get('request')
    if not request:
        return '#'
    
    path = request.path
    
    # Déterminer le namespace selon le chemin
    if path.startswith('/worker/'):
        try:
            return reverse('worker:notification_count')
        except NoReverseMatch:
            pass
    elif path.startswith('/client/'):
        try:
            return reverse('client_portal:notification_count')
        except NoReverseMatch:
            pass
    elif path.startswith('/admin-dashboard/'):
        try:
            # Les notifications admin sont dans core:notification_count
            return reverse('core:notification_count')
        except NoReverseMatch:
            pass
    
    # Fallback vers core
    try:
        return reverse('core:notification_count')
    except NoReverseMatch:
        return '#'


@register.simple_tag(takes_context=True)
def notification_list_url(context):
    """Obtenir l'URL correcte pour notification_list selon le portail actuel."""
    request = context.get('request')
    if not request:
        return '#'
    
    path = request.path
    
    # Déterminer le namespace selon le chemin
    if path.startswith('/worker/'):
        try:
            return reverse('worker:notification_list')
        except NoReverseMatch:
            pass
    elif path.startswith('/client/'):
        try:
            return reverse('client_portal:notification_list')
        except NoReverseMatch:
            pass
    elif path.startswith('/admin-dashboard/'):
        try:
            return reverse('core:notification_list')
        except NoReverseMatch:
            pass
    
    # Fallback vers core
    try:
        return reverse('core:notification_list')
    except NoReverseMatch:
        return '#'

