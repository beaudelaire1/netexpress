from __future__ import annotations

import logging

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.utils import OperationalError, ProgrammingError

from .models import Profile

User = get_user_model()
logger = logging.getLogger(__name__)


class SignUpForm(UserCreationForm):
    """Création de compte public.

    SÉCURITÉ : l'inscription publique attribue TOUJOURS le rôle ``client``.
    Le rôle n'est volontairement PAS exposé dans le formulaire pour empêcher
    toute escalade de privilèges (un visiteur ne doit pas pouvoir se créer un
    compte ``admin_business`` ou ``admin_technical``). L'attribution des rôles
    privilégiés se fait exclusivement via l'administration Django ou un flux
    d'invitation contrôlé.
    """

    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            # profil — rôle forcé à « client », jamais déterminé par l'entrée utilisateur
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.ROLE_CLIENT
            profile.phone = self.cleaned_data.get("phone", "")
            profile.save()
        return user


class PortalAuthenticationForm(AuthenticationForm):
    """Authentication form that accepts the portal email or the username."""

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].label = "Email ou identifiant"
        self.fields["username"].widget.attrs.update({
            "placeholder": "client@example.com",
            "autocomplete": "username",
            "autocapitalize": "none",
        })
        self.fields["password"].widget.attrs.update({
            "autocomplete": "current-password",
        })

    @staticmethod
    def _resolve_login_identifier(identifier: str) -> str:
        cleaned_identifier = (identifier or "").strip()
        if not cleaned_identifier:
            return cleaned_identifier

        if User.objects.filter(username=cleaned_identifier).exists():
            return cleaned_identifier

        if "@" not in cleaned_identifier:
            return cleaned_identifier

        candidate_usernames = list(
            User.objects.filter(email__iexact=cleaned_identifier)
            .values_list("username", flat=True)[:2]
        )
        if len(candidate_usernames) == 1:
            return candidate_usernames[0]
        return cleaned_identifier

    def clean(self):
        identifier = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if identifier and password:
            resolved_identifier = self._resolve_login_identifier(identifier)
            try:
                self.user_cache = authenticate(
                    self.request,
                    username=resolved_identifier,
                    password=password,
                )
            except (ProgrammingError, OperationalError):
                logger.exception(
                    "Authentication backend unavailable during login for '%s'. "
                    "Falling back to ModelBackend. Apply django-axes migrations in production.",
                    resolved_identifier,
                )
                self.user_cache = ModelBackend().authenticate(
                    self.request,
                    username=resolved_identifier,
                    password=password,
                )
                if self.user_cache is not None:
                    self.user_cache.backend = "django.contrib.auth.backends.ModelBackend"
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    """Édition du profil par l'utilisateur lui-même.

    SÉCURITÉ : le champ ``role`` est volontairement exclu. Un utilisateur ne
    doit jamais pouvoir modifier son propre rôle (escalade de privilèges).
    La gestion des rôles est réservée à l'administration.
    """

    class Meta:
        model = Profile
        fields = ("phone",)
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }
