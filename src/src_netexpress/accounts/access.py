"""Explicit client ownership; an email string alone never grants document access."""
from django.contrib.auth import get_user_model
from .models import Profile


def verified_client_id(user):
    if not user.is_authenticated or not user.is_active:
        return None
    profile = getattr(user, "profile", None)
    if profile and profile.role == Profile.ROLE_CLIENT and profile.has_verified_email:
        return profile.client_id
    return None


def portal_user_for_client(client):
    return get_user_model().objects.filter(profile__client=client, profile__role="client").first()


def confirm_email(user):
    """Only called after a single-use token delivered to the current email is checked."""
    from django.utils import timezone
    profile = user.profile
    profile.verified_email = user.email.strip().lower()
    profile.email_verified_at = timezone.now()
    profile.force_password_change = False
    # Legacy accounts require proof of mailbox ownership before linking.
    if profile.role == Profile.ROLE_CLIENT and not profile.client_id:
        from devis.models import Client
        clients = list(Client.objects.filter(email__iexact=user.email)[:2])
        if len(clients) == 1:
            profile.client = clients[0]
    profile.save(update_fields=["verified_email", "email_verified_at", "client", "force_password_change"])
