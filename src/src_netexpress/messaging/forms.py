from __future__ import annotations

from django import forms


class MessageComposeForm(forms.Form):
    recipient = forms.EmailField(label="Destinataire")
    subject = forms.CharField(label="Objet", max_length=255)
    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "rows": 12,
            "class": "rich-editor",
            "placeholder": "Rédigez votre message…",
        }),
    )
    attachment = forms.FileField(label="Pièce jointe", required=False)
