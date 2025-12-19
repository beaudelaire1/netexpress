"""
Legacy template filters to maintain compatibility with templates
expecting filters removed in newer versions of Django.  In Django 5,
the built‑in filter ``length_is`` has been deprecated and removed.
Some third‑party templates (including Jazzmin/admin) still reference
``length_is``.  This module reimplements the filter so that those
templates continue to render without error.

To make this filter available globally, it is declared as a builtin
template library via the ``TEMPLATES`` setting in ``settings/base.py``.
"""

from django import template


register = template.Library()


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