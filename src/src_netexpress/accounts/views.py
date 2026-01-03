from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.decorators.http import require_http_methods

from .forms import ProfileForm, SignUpForm
from core.portal_routing import redirect_after_login

User = get_user_model()


def signup(request):
    """Création de compte + connexion immédiate."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Votre compte a été créé.")
            # Use portal routing logic for redirect
            redirect_url = redirect_after_login(user)
            return redirect(redirect_url)
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def custom_login(request):
    """Custom login view that redirects users to their appropriate portal."""
    if request.user.is_authenticated:
        # User is already logged in, redirect to their portal
        redirect_url = redirect_after_login(request.user)
        return redirect(redirect_url)
    
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Bienvenue, {user.get_full_name() or user.username}!")
                
                # Check if there's a 'next' parameter for redirect
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                # Use portal routing logic for redirect
                redirect_url = redirect_after_login(user)
                return redirect(redirect_url)
    else:
        form = AuthenticationForm()
    
    return render(request, "registration/login.html", {"form": form})


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


@require_http_methods(["GET", "POST"])
def password_setup(request, uidb64, token):
    """
    Password setup view for new client accounts created via invitation.
    
    This view allows new clients to set their password using a secure token
    sent via email invitation.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                # Log the user in automatically after password setup
                login(request, user)
                messages.success(request, 'Votre mot de passe a été configuré avec succès. Bienvenue !')
                
                # Redirect to client portal
                return redirect('core:client_portal_dashboard')
        else:
            form = SetPasswordForm(user)
        
        context = {
            'form': form,
            'user': user,
            'validlink': True,
        }
        return render(request, 'accounts/password_setup.html', context)
    else:
        context = {
            'validlink': False,
        }
        return render(request, 'accounts/password_setup.html', context)


def custom_logout(request):
    """Custom logout view with success message."""
    if request.user.is_authenticated:
        username = request.user.get_full_name() or request.user.username
        logout(request)
        messages.success(request, f"Au revoir {username}! Vous avez été déconnecté avec succès.")
    
    return redirect('core:home')



@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    """
    Vue de changement de mot de passe.
    
    Si l'utilisateur a force_password_change=True, il est redirigé ici
    et ne peut pas accéder aux autres pages tant qu'il n'a pas changé son mot de passe.
    """
    from django.contrib.auth.forms import PasswordChangeForm
    from .models import Profile
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Désactiver le flag force_password_change
            try:
                profile = user.profile
                if profile.force_password_change:
                    profile.force_password_change = False
                    profile.save(update_fields=['force_password_change'])
            except Profile.DoesNotExist:
                pass
            
            # Mettre à jour la session pour éviter la déconnexion
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Votre mot de passe a été changé avec succès!')
            
            # Rediriger vers le portail approprié
            redirect_url = redirect_after_login(user)
            return redirect(redirect_url)
    else:
        form = PasswordChangeForm(request.user)
    
    # Vérifier si c'est un changement forcé
    is_forced = False
    try:
        is_forced = request.user.profile.force_password_change
    except:
        pass
    
    return render(request, 'accounts/password_change.html', {
        'form': form,
        'is_forced': is_forced,
    })


@login_required
def password_change_done(request):
    """Vue de confirmation après changement de mot de passe."""
    return redirect(redirect_after_login(request.user))
