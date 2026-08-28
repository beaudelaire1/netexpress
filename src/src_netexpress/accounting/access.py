from __future__ import annotations

from accounts.models import Profile
from accounts.portal import get_user_role

ADMIN_ROLES = {Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL}


def is_verified_accountant(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    return bool(
        profile
        and profile.role == Profile.ROLE_ACCOUNTANT
        and profile.has_verified_email
    )


def can_access_accounting_exchange(user, exchange=None) -> bool:
    """Return whether a user may enter the shared company/cabinet workspace."""
    if not getattr(user, "is_authenticated", False):
        return False
    role = get_user_role(user)
    return role in ADMIN_ROLES or is_verified_accountant(user)


def can_access_accounting_exchange_document(user, document) -> bool:
    """Apply document visibility on top of the accounting workspace boundary."""
    if not can_access_accounting_exchange(user, document.exchange):
        return False

    role = get_user_role(user)
    if role in ADMIN_ROLES:
        return True

    return document.visibility == document.Visibility.SHARED
