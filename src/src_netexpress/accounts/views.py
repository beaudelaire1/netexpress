from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from django.urls import reverse

from .forms import PortalAuthenticationForm, ProfileForm, SignUpForm
from core.portal_routing import redirect_after_login

User = get_user_model()

# Vérification d'e-mail : jeton signé indépendant de l'état de connexion
# (contrairement à default_token_generator qui dépend de last_login/password).
EMAIL_VERIFY_SALT = "accounts.email-verify"
EMAIL_VERIFY_MAX_AGE = 60 * 60 * 24 * 3  # 3 jours


def _send_email_verification(request, user) -> None:
    """Envoie un e-mail de confirmation d'adresse à un compte auto-inscrit."""
    if not user.email:
        return
    token = signing.dumps({"uid": user.pk}, salt=EMAIL_VERIFY_SALT)
    path = reverse("accounts:verify_email", kwargs={"token": token})
    verify_url = request.build_absolute_uri(path)
    subject = "Confirmez votre adresse e-mail — Nettoyage Express"
    body = (
        f"Bonjour {user.get_username()},\n\n"
        "Merci pour votre inscription. Pour accéder à vos devis et factures, "
        "confirmez votre adresse e-mail en cliquant sur le lien ci-dessous :\n\n"
        f"{verify_url}\n\n"
        "Si vous n'êtes pas à l'origine de cette inscription, ignorez cet e-mail.\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    try:
        send_mail(subject, body, from_email, [user.email], fail_silently=True)
    except Exception:
        # Ne jamais bloquer l'inscription si l'envoi échoue.
        pass


def signup(request):
    """Création de compte + connexion immédiate."""
    if request.method == "POST":
        # Vérification Cloudflare Turnstile
        from core.turnstile import verify_turnstile
        if not verify_turnstile(request):
            messages.error(request, "Vérification de sécurité échouée. Veuillez réessayer.")
            form = SignUpForm(request.POST)
            return render(request, "accounts/signup.html", {"form": form})

        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Envoi du lien de confirmation d'adresse e-mail (accès documents
            # bloqué tant que l'e-mail n'est pas vérifié — anti-usurpation).
            _send_email_verification(request, user)
            login(request, user)
            messages.success(
                request,
                "Votre compte a été créé. Un e-mail de confirmation vous a été "
                "envoyé : confirmez votre adresse pour accéder à vos devis et factures.",
            )
            # Use portal routing logic for redirect
            redirect_url = redirect_after_login(user)
            return redirect(redirect_url)
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET"])
def verify_email(request, token):
    """Confirme l'adresse e-mail d'un compte auto-inscrit via un jeton signé."""
    try:
        data = signing.loads(token, salt=EMAIL_VERIFY_SALT, max_age=EMAIL_VERIFY_MAX_AGE)
        user = get_object_or_404(User, pk=data.get("uid"))
    except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
        user = None

    if user is not None:
        profile = getattr(user, "profile", None)
        if profile is not None and not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
        messages.success(request, "Votre adresse e-mail a été confirmée. Merci !")
        if request.user.is_authenticated:
            return redirect(redirect_after_login(user))
        return redirect("accounts:login")

    messages.error(request, "Lien de confirmation invalide ou expiré.")
    return redirect("accounts:login")


def custom_login(request):
    """Custom login view that redirects users to their appropriate portal."""
    if request.user.is_authenticated:
        # User is already logged in, redirect to their portal
        redirect_url = redirect_after_login(request.user)
        return redirect(redirect_url)
    
    if request.method == "POST":
        # Vérification Cloudflare Turnstile
        from core.turnstile import verify_turnstile
        if not verify_turnstile(request):
            messages.error(request, "Vérification de sécurité échouée. Veuillez réessayer.")
            form = PortalAuthenticationForm()
            return render(request, "registration/login.html", {"form": form})

        form = PortalAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # AuthenticationForm valide deja les credentials avec le request.
            user = form.get_user()
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
                form = PortalAuthenticationForm(request)
    
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
                # Le clic sur le lien d'invitation prouve la possession de l'e-mail.
                profile = getattr(user, "profile", None)
                if profile is not None and not profile.email_verified:
                    profile.email_verified = True
                    profile.save(update_fields=["email_verified"])
                # Log the user in automatically after password setup
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
