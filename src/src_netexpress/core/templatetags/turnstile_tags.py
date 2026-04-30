"""Template tags for Cloudflare Turnstile."""

from django import template
from core.turnstile import get_site_key, is_enabled

register = template.Library()


@register.simple_tag
def turnstile_site_key():
    return get_site_key()


@register.simple_tag
def turnstile_enabled():
    return is_enabled()
