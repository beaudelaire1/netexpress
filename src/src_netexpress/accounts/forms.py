from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile

User = get_user_model()


class SignUpForm(UserCreationForm):
    """Création de compte avec choix du rôle."""

    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, initial=Profile.ROLE_CLIENT)
    phone = forms.CharField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            # profil
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data.get("role", Profile.ROLE_CLIENT)
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
            self.user_cache = authenticate(
                self.request,
                username=resolved_identifier,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("role", "phone")
        widgets = {
            "role": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }
