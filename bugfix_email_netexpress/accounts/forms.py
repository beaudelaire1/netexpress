from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class SignUpForm(UserCreationForm):
    """Création de compte avec choix du rôle."""

    email = forms.EmailField(required=True)
    # The team role should not be selectable during self‑sign‑up.  Only
    # administrators can assign the "team" role to a user via the admin.
    role = forms.ChoiceField(
        choices=[
            (Profile.ROLE_CLIENT, "Client"),
            (Profile.ROLE_WORKER, "Ouvrier"),
        ],
        initial=Profile.ROLE_CLIENT,
    )
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("role", "phone")
        widgets = {
            "role": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }
