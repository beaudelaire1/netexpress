"""
Vues pour le formulaire de contact.
Compatibles avec contact/urls.py :
 - contact_view
 - contact_success
"""

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse

from .forms import ContactForm


def contact_view(request):
    """
    Formulaire de contact.
    - Sauvegarde du message via ContactForm()
    - Redirection vers la page de succès
    """

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            message_obj = form.save()

            # ---- Notifications admin (anti "black hole") ----
            # Destinataires: settings.ADMINS si défini, sinon DEFAULT_FROM_EMAIL.
            admin_emails = [email for _, email in getattr(settings, "ADMINS", []) or []]
            if not admin_emails:
                fallback = getattr(settings, "DEFAULT_FROM_EMAIL", "")
                if fallback:
                    admin_emails = [fallback]

            if admin_emails:
                subject = f"[Contact] Nouveau message — {getattr(message_obj, 'full_name', '')}".strip()
                logo_url = request.build_absolute_uri(static("img/logo.png"))
                ctx = {"contact": message_obj, "logo_url": logo_url}
                html = render_to_string("emails/new_contact_admin.html", ctx)
                text = (
                    f"Nom: {getattr(message_obj, 'full_name', '')}\n"
                    f"Email: {getattr(message_obj, 'email', '')}\n"
                    f"Ville: {getattr(message_obj, 'city', '')}\n\n"
                    f"Message:\n{getattr(message_obj, 'body', '')}\n"
                )
                try:
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=text,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        to=admin_emails,
                        reply_to=[getattr(message_obj, "email", "")] if getattr(message_obj, "email", "") else None,
                    )
                    email.attach_alternative(html, "text/html")
                    email.send(fail_silently=True)
                except Exception:
                    # Ne jamais bloquer l'utilisateur si l'email échoue.
                    pass

            messages.success(request, "Votre message a bien été envoyé.")
            return redirect(reverse("contact:success"))
    else:
        form = ContactForm()

    return render(request, "contact/contact.html", {"form": form})


def contact_success(request):
    """
    Page de confirmation après envoi du formulaire.
    Affiche les informations de contact du branding des factures (optionnel).
    """

    branding = getattr(settings, "INVOICE_BRANDING", {}) or {}

    # Si address_lines n'existe pas, on le reconstruit proprement
    if branding and not branding.get("address_lines") and branding.get("address"):
        lines = [
            line.strip()
            for line in str(branding.get("address")).splitlines()
            if line.strip()
        ]
        branding["address_lines"] = lines

    return render(request, "contact/contact_success.html", {"branding": branding})
