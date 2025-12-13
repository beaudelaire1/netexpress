"""Vues pour l'historique des messages envoyés (class-based views)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from .models import EmailMessage


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
