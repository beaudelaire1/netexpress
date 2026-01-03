from __future__ import annotations

from django import forms
from django.contrib.auth.models import User
from django.conf import settings
from tinymce.widgets import TinyMCE

from .models import Message, MessageThread
from devis.models import Client


# Types de messages prédéfinis avec leurs templates
EMAIL_TEMPLATE_CHOICES = [
    ('notification_generic', 'Notification générique'),
    ('task_assignment', 'Assignation de tâche'),
    ('task_completion', 'Tâche terminée'),
    ('account_invitation', 'Invitation de compte'),
    ('message_notification', 'Notification de message'),
]


class MessageComposeForm(forms.Form):
    """Formulaire d'envoi d'email avec contenu libre et mise en forme.
    
    Permet d'écrire un message personnalisé avec TinyMCE.
    """
    client = forms.ModelChoiceField(
        queryset=Client.objects.all().order_by('full_name'),
        label="Destinataire",
        required=False,
        empty_label="-- Sélectionner un client --",
        widget=forms.Select(attrs={
            'class': 'bo-input',
            'id': 'id_client'
        })
    )
    recipient = forms.EmailField(
        label="Ou saisir un email",
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'bo-input',
            'placeholder': 'client@example.com',
            'id': 'id_recipient'
        })
    )
    subject = forms.CharField(
        label="Objet",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'bo-input',
            'placeholder': 'Objet du message'
        })
    )
    content = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'id': 'id_content',
            'rows': 10
        }),
        help_text="Rédigez votre message avec mise en forme"
    )
    attachment = forms.FileField(
        label="Pièce jointe (optionnel)", 
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'bo-input'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        recipient = cleaned_data.get('recipient')
        
        # Au moins un des deux doit être renseigné
        if not client and not recipient:
            raise forms.ValidationError("Veuillez sélectionner un client ou saisir un email.")
        
        # Si client sélectionné, utiliser son email
        if client:
            cleaned_data['recipient'] = client.email
            cleaned_data['recipient_name'] = client.full_name
        else:
            cleaned_data['recipient_name'] = ''
        
        return cleaned_data


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


# Configuration TinyMCE simplifiée pour les messages
TINYMCE_MESSAGING_ATTRS = {
    'cols': 80,
    'rows': 10,
}


class InternalMessageForm(forms.ModelForm):
    """Form for creating internal messages with rich text editor."""
    
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
        widget=TinyMCE(
            attrs=TINYMCE_MESSAGING_ATTRS,
            mce_attrs={
                'theme': 'silver',
                'height': 250,
                'menubar': False,
                'plugins': 'advlist autolink lists link',
                'toolbar': 'bold italic underline | forecolor | bullist numlist | link | removeformat',
                'branding': False,
                'promotion': False,
                'license_key': 'gpl',
            }
        ),
        help_text="Utilisez la barre d'outils pour formater votre message"
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
    """Form for replying to messages within a thread with rich text editor."""
    
    content = forms.CharField(
        label="Réponse",
        widget=TinyMCE(
            attrs=TINYMCE_MESSAGING_ATTRS,
            mce_attrs={
                'theme': 'silver',
                'height': 200,
                'menubar': False,
                'plugins': 'advlist autolink lists link',
                'toolbar': 'bold italic underline | forecolor | bullist numlist | link | removeformat',
                'branding': False,
                'promotion': False,
                'license_key': 'gpl',
            }
        ),
        help_text="Utilisez la barre d'outils pour formater votre réponse"
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
            # Reply to the other person in the conversation
            if self.original_message.sender == self.sender:
                reply.recipient = self.original_message.recipient
            else:
                reply.recipient = self.original_message.sender
            reply.subject = f"Re: {self.original_message.subject.replace('Re: ', '')}"
            reply.thread = self.original_message.thread
        
        if commit:
            reply.save()
            
            # Update thread's last message time
            if reply.thread:
                reply.thread.last_message_at = reply.created_at
                reply.thread.save(update_fields=['last_message_at'])
        
        return reply
