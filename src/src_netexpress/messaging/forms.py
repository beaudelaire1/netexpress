from __future__ import annotations

from django import forms
from django.contrib.auth.models import User
from ckeditor.widgets import CKEditorWidget

from .models import Message, MessageThread


class MessageComposeForm(forms.Form):
    recipient = forms.EmailField(label="Destinataire")
    subject = forms.CharField(label="Objet", max_length=255)
    body = forms.CharField(
        label="Message",
        widget=CKEditorWidget(config_name='messaging'),
        help_text="Utilisez les outils de formatage pour créer un message professionnel"
    )
    attachment = forms.FileField(label="Pièce jointe", required=False)


class InternalMessageForm(forms.ModelForm):
    """Form for creating internal messages with CKEditor."""
    
    recipient = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label="Destinataire",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    content = forms.CharField(
        label="Message",
        widget=CKEditorWidget(config_name='messaging'),
        help_text="Utilisez les outils de formatage pour créer un message professionnel"
    )
    
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Objet du message'
            })
        }
        labels = {
            'subject': 'Objet',
            'content': 'Message'
        }
    
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
    """Form for replying to messages within a thread."""
    
    content = forms.CharField(
        label="Réponse",
        widget=CKEditorWidget(config_name='messaging'),
        help_text="Rédigez votre réponse"
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
