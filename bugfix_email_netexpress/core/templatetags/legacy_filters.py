"""
Template tags et filtres personnalisés pour NetExpress.

Ce module contient :
- length_is : backport du filtre Django supprimé
- active_nav : simple tag pour détecter la page active dans la navigation

Pour utiliser ces tags dans un template :
    {% load legacy_filters %}
"""

from django import template
from django.urls import resolve, Resolver404


register = template.Library()


@register.simple_tag(takes_context=True)
def active_nav(context, url_name: str, css_class: str = "is-active") -> str:
    """
    Retourne une classe CSS si l'URL courante correspond au nom d'URL donné.

    Usage dans un template :
        <a class="nav-link {% active_nav 'core:home' %}" href="{% url 'core:home' %}">Accueil</a>

    Parameters
    ----------
    context : dict
        Le contexte du template (contient 'request').
    url_name : str
        Le nom de l'URL à vérifier (ex: 'core:home', 'services:list').
    css_class : str, optional
        La classe CSS à retourner si l'URL correspond (défaut: 'is-active').

    Returns
    -------
    str
        La classe CSS si l'URL correspond, sinon une chaîne vide.
    """
    request = context.get("request")
    if not request:
        return ""

    try:
        resolved = resolve(request.path)
        # Construire le nom complet de l'URL résolue
        if resolved.namespace:
            current_url_name = f"{resolved.namespace}:{resolved.url_name}"
        else:
            current_url_name = resolved.url_name

        # Vérifier si l'URL courante correspond
        if current_url_name == url_name:
            return css_class

        # Vérifier aussi les préfixes (pour les sous-pages)
        if url_name.endswith(":") and current_url_name.startswith(url_name):
            return css_class

    except Resolver404:
        pass

    return ""


@register.simple_tag(takes_context=True)
def active_nav_aria(context, url_name: str) -> str:
    """
    Retourne 'page' si l'URL courante correspond, pour aria-current.

    Usage :
        <a aria-current="{% active_nav_aria 'core:home' %}" href="...">

    Returns 'page' if current, empty string otherwise.
    """
    result = active_nav(context, url_name, "page")
    return result if result == "page" else ""


@register.filter(name="length_is")
def length_is(value, arg) -> bool:
    """
    Return True if the value has a length exactly equal to ``arg``.

    This is a backport of the removed Django template filter.  The
    original filter compared the length of a string or list with the
    provided argument.  If ``value`` has no length, returns False.

    Examples::

        {{ "abc"|length_is:"3" }} -> True
        {{ [1, 2]|length_is:1 }} -> False

    Parameters
    ----------
    value : Any
        The object whose length to compare.
    arg : Any
        The expected length (will be coerced to an integer).

    Returns
    -------
    bool
        True if the length matches, False otherwise.
    """
    try:
        expected = int(arg)
    except Exception:
        return False
    try:
        length = len(value)
    except Exception:
        return False
    return length == expected