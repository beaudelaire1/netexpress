from __future__ import annotations

from django import forms
from django.contrib.auth.models import User

from .models import Message, MessageThread


# Types de messages prédéfinis avec leurs templates
EMAIL_TEMPLATE_CHOICES = [
    ('notification_generic', 'Notification générique'),
    ('task_assignment', 'Assignation de tâche'),
    ('task_completion', 'Tâche terminée'),
    ('account_invitation', 'Invitation de compte'),
    ('message_notification', 'Notification de message'),
]


class MessageComposeForm(forms.Form):
    """Formulaire d'envoi d'email avec templates prédéfinis.
    
    Le contenu est généré automatiquement via les templates stylisés.
    Aucun texte libre n'est permis.
    """
    recipient = forms.EmailField(
        label="Destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'client@example.com'
        })
    )
    template_type = forms.ChoiceField(
        label="Type de message",
        choices=EMAIL_TEMPLATE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
        })
    )
    # Champs contextuels optionnels pour personnaliser le template
    recipient_name = forms.CharField(
        label="Nom du destinataire",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Nom du client ou employé'
        })
    )
    reference = forms.CharField(
        label="Référence (optionnel)",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Ex: Devis #123, Tâche #456'
        })
    )
    attachment = forms.FileField(
        label="Pièce jointe (optionnel)", 
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        })
    )


# Types de sujets prédéfinis pour les messages internes
INTERNAL_MESSAGE_SUBJECTS = [
    ('question', 'Question'),
    ('information', 'Information'),
    ('demande', 'Demande'),
    ('suivi_tache', 'Suivi de tâche'),
    ('suivi_devis', 'Suivi de devis'),
    ('suivi_facture', 'Suivi de facture'),
    ('autre', 'Autre'),
]


class InternalMessageForm(forms.ModelForm):
    """Form for creating internal messages with predefined subjects.
    
    Le contenu est limité à un texte simple sans HTML libre.
    """
    
    recipient = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label="Destinataire",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
        })
    )
    
    subject_type = forms.ChoiceField(
        label="Type de message",
        choices=INTERNAL_MESSAGE_SUBJECTS,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
        })
    )
    
    reference = forms.CharField(
        label="Référence (optionnel)",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Ex: Devis #123, Tâche #456'
        })
    )
    
    content = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'rows': 5,
            'placeholder': 'Votre message...',
            'maxlength': 2000
        }),
        max_length=2000,
        help_text="Maximum 2000 caractères"
    )
    
    class Meta:
        model = Message
        fields = ['recipient', 'content']
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)
        
        # Filter recipients to exclude the sender
        if self.sender:
            self.fields['recipient'].queryset = User.objects.filter(
                is_active=True
            ).exclude(id=self.sender.id)
    
    def save(self, commit=True):
        message = super().save(commit=False)
        if self.sender:
            message.sender = self.sender
        
        # Générer le sujet à partir du type et de la référence
        subject_type = self.cleaned_data.get('subject_type', 'autre')
        subject_label = dict(INTERNAL_MESSAGE_SUBJECTS).get(subject_type, 'Message')
        reference = self.cleaned_data.get('reference', '')
        
        if reference:
            message.subject = f"{subject_label} — {reference}"
        else:
            message.subject = subject_label
        
        if commit:
            message.save()
            
            # Create or update message thread
            thread, created = MessageThread.objects.get_or_create(
                subject=message.subject,
                defaults={'last_message_at': message.created_at}
            )
            
            # Add participants to thread
            thread.participants.add(message.sender, message.recipient)
            
            # Update thread's last message time
            if not created:
                thread.last_message_at = message.created_at
                thread.save(update_fields=['last_message_at'])
            
            # Associate message with thread
            message.thread = thread
            message.save(update_fields=['thread'])
        
        return message


class MessageReplyForm(forms.ModelForm):
    """Form for replying to messages within a thread.
    
    Utilise un textarea simple sans HTML libre.
    """
    
    content = forms.CharField(
        label="Réponse",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'rows': 4,
            'placeholder': 'Votre réponse...',
            'maxlength': 2000
        }),
        max_length=2000,
        help_text="Maximum 2000 caractères"
    )
    
    class Meta:
        model = Message
        fields = ['content']
    
    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop('sender', None)
        self.original_message = kwargs.pop('original_message', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        reply = super().save(commit=False)
        
        if self.sender and self.original_message:
            reply.sender = self.sender
            reply.recipient = self.original_message.sender
            reply.subject = f"Re: {self.original_message.subject}"
            reply.thread = self.original_message.thread
        
        if commit:
            reply.save()
            
            # Update thread's last message time
            if reply.thread:
                reply.thread.last_message_at = reply.created_at
                reply.thread.save(update_fields=['last_message_at'])
        
        return reply
