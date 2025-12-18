from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm


def signup(request):
    """Création de compte + connexion immédiate."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Votre compte a été créé.")
            # Redirection selon rôle
            role = getattr(getattr(user, "profile", None), "role", "client")
            if role == "worker":
                return redirect("core:worker_dashboard")
            return redirect("core:client_dashboard")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    prof = getattr(request.user, "profile", None)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=prof)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=prof)
    return render(request, "accounts/profile.html", {"form": form})
