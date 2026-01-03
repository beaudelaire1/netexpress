"""Vues pour l'historique des messages envoyés (class-based views)."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.conf import settings

from .models import EmailMessage, Message, MessageThread
from .forms import MessageComposeForm, InternalMessageForm, MessageReplyForm, EMAIL_TEMPLATE_CHOICES


# Mapping des types de templates vers les sujets et templates
TEMPLATE_CONFIG = {
    'notification_generic': {
        'subject': 'Notification — Nettoyage Express',
        'template': 'emails/notification_generic.html',
    },
    'task_assignment': {
        'subject': 'Nouvelle tâche assignée — Nettoyage Express',
        'template': 'emails/task_assignment.html',
    },
    'task_completion': {
        'subject': 'Tâche terminée — Nettoyage Express',
        'template': 'emails/task_completion.html',
    },
    'account_invitation': {
        'subject': 'Invitation à rejoindre Nettoyage Express',
        'template': 'emails/account_invitation.html',
    },
    'message_notification': {
        'subject': 'Nouveau message — Nettoyage Express',
        'template': 'emails/message_notification.html',
    },
}


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
    """Compose & send a custom HTML email with rich text formatting.

    Permet d'écrire un message personnalisé avec TinyMCE (texte libre).
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("admin:login")

    if request.method == "POST":
        form = MessageComposeForm(request.POST, request.FILES)
        if form.is_valid():
            # Récupérer les données du formulaire
            recipient_email = form.cleaned_data["recipient"]
            recipient_name = form.cleaned_data.get("recipient_name") or "Client"
            subject = form.cleaned_data["subject"]
            content = form.cleaned_data["content"]
            
            # Préparer le contexte pour le template d'email
            branding = getattr(settings, 'INVOICE_BRANDING', {}) or {}
            context = {
                'branding': branding,
                'brand': branding.get('name', 'Nettoyage Express'),
                'recipient_name': recipient_name,
                'content': content,  # Contenu HTML de TinyMCE
            }
            
            # Générer le HTML avec le template de base
            html_body = render_to_string('emails/custom_message.html', context)
            
            msg = EmailMessage.objects.create(
                recipient=recipient_email,
                subject=subject,
                body=html_body,
                attachment=form.cleaned_data.get("attachment"),
            )
            try:
                msg.send()
                messages.success(request, f"Message envoyé avec succès à {recipient_email}.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi du message: {str(e)}")
            return redirect("messaging:list")
    else:
        form = MessageComposeForm()

    return render(request, "messaging/compose.html", {"form": form})


# Internal Messaging System Views

class InternalMessageListView(LoginRequiredMixin, ListView):
    """Display list of internal messages for the current user."""
    model = Message
    template_name = "messaging/internal_message_list.html"
    context_object_name = "messages"
    paginate_by = 20
    
    def get_queryset(self):
        """Return messages where user is sender or recipient."""
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).select_related('sender', 'recipient', 'thread').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count unread messages
        context['unread_count'] = Message.objects.filter(
            recipient=self.request.user,
            read_at__isnull=True
        ).count()
        return context


class InternalMessageDetailView(LoginRequiredMixin, DetailView):
    """Display detail of an internal message."""
    model = Message
    template_name = "messaging/internal_message_detail.html"
    context_object_name = "message"
    
    def get_queryset(self):
        """Only allow access to messages where user is sender or recipient."""
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).select_related('sender', 'recipient', 'thread')
    
    def get_object(self, queryset=None):
        """Mark message as read when recipient views it."""
        message = super().get_object(queryset)
        if message.recipient == self.request.user:
            message.mark_as_read()
        return message
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add reply form
        context['reply_form'] = MessageReplyForm()
        
        # Get thread messages if this message is part of a thread
        if self.object.thread:
            context['thread_messages'] = self.object.thread.messages.select_related(
                'sender', 'recipient'
            ).order_by('created_at')
        
        return context


class InternalMessageComposeView(LoginRequiredMixin, CreateView):
    """Compose a new internal message."""
    model = Message
    form_class = InternalMessageForm
    template_name = "messaging/internal_message_compose.html"
    success_url = reverse_lazy('messaging:internal_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['sender'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Message envoyé avec succès.")
        return super().form_valid(form)


class MessageThreadListView(LoginRequiredMixin, ListView):
    """Display list of message threads for the current user."""
    model = MessageThread
    template_name = "messaging/thread_list.html"
    context_object_name = "threads"
    paginate_by = 20
    
    def get_queryset(self):
        """Return threads where user is a participant."""
        return MessageThread.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages').order_by('-last_message_at')


def message_reply(request, message_id):
    """Handle AJAX reply to a message."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    original_message = get_object_or_404(
        Message,
        id=message_id,
        recipient=request.user  # Only recipient can reply
    )
    
    if request.method == 'POST':
        form = MessageReplyForm(
            request.POST,
            sender=request.user,
            original_message=original_message
        )
        
        if form.is_valid():
            reply = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Réponse envoyée avec succès',
                'reply_id': reply.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def mark_message_read(request, message_id):
    """Mark a message as read via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    message = get_object_or_404(
        Message,
        id=message_id,
        recipient=request.user
    )
    
    message.mark_as_read()
    
    return JsonResponse({
        'success': True,
        'read_at': message.read_at.isoformat() if message.read_at else None
    })
