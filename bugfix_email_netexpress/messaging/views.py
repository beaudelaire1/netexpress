"""Vues pour l'historique des messages envoyés (class-based views)."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.generic import ListView, DetailView

from .models import EmailMessage
from .forms import MessageComposeForm


class MessageListView(LoginRequiredMixin, ListView):
    """Afficher la liste des messages envoyés."""
    model = EmailMessage
    template_name = "messaging/message_list.html"
    context_object_name = "email_messages"
    ordering = ["-created_at"]


class MessageDetailView(LoginRequiredMixin, DetailView):
    """Afficher le détail d'un message spécifique."""
    model = EmailMessage
    template_name = "messaging/message_detail.html"
    context_object_name = "message"


def compose(request):
    """Compose & send a premium HTML email (no plaintext).

    L'éditeur WYSIWYG est géré via TinyMCE côté template.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("admin:login")

    if request.method == "POST":
        form = MessageComposeForm(request.POST, request.FILES)
        if form.is_valid():
            msg = EmailMessage.objects.create(
                recipient=form.cleaned_data["recipient"],
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
                attachment=form.cleaned_data.get("attachment"),
            )
            try:
                msg.send()
                messages.success(request, "Message envoyé.")
            except Exception:
                messages.error(request, "Erreur lors de l'envoi du message.")
            return redirect("messaging:list")
    else:
        form = MessageComposeForm()

    return render(request, "messaging/compose.html", {"form": form})
