"""
Formulaires pour l'app ``contact``.

``ContactForm`` collecte les informations de l'expéditeur et crée un
``Message`` lors de l'enregistrement.  Les widgets sont décorés pour
s'aligner avec la charte graphique.  Une logique anti‑spam simple (honeypot)
peut être ajoutée via un champ caché si nécessaire.
"""

from django import forms

from .models import Message


class ContactForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["topic", "full_name", "email", "phone","city", "zip_code", "body"]
        widgets = {
            "topic": forms.Select(attrs={"class": "select"}),
            "full_name": forms.TextInput(attrs={"class": "input", "placeholder": "Nom complet", "required": True}),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "Email", "required": True}),
            # Le champ téléphone est obligatoire et comporte un attribut required pour la validation côté client.
            "phone": forms.TextInput(attrs={"class": "input", "placeholder": "Téléphone", "required": True}),
            "city": forms.TextInput(attrs={"class": "input", "placeholder": "Ville", "required": True}),
            "zip_code": forms.TextInput(attrs={"class": "input", "placeholder": "Code Postal", "required": True}),
            "body": forms.Textarea(attrs={"class": "textarea", "placeholder": "Votre message", "rows": 4}),
        }