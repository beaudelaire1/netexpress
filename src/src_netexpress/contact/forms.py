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
        fields = ["topic", "full_name", "email", "phone","street","city", "zip_code", "body"]

        # Messages d'erreur personnalisés pour une meilleure UX
        error_messages = {
            'topic': {
                'required': 'Merci de sélectionner un sujet pour votre demande',
            },
            'full_name': {
                'required': 'Merci de renseigner votre nom complet',
                'max_length': 'Le nom ne peut pas dépasser 200 caractères',
            },
            'email': {
                'required': 'Votre email est nécessaire pour vous recontacter',
                'invalid': 'Format email invalide (exemple: nom@exemple.fr)',
            },
            'phone': {
                'required': 'Votre numéro de téléphone est obligatoire pour vous joindre',
            },
            'street': {
                'required': 'Merci de renseigner votre adresse',
            },
            'city': {
                'required': 'Merci de renseigner votre commune',
            },
            'zip_code': {
                'required': 'Merci de renseigner votre code postal',
            },
            'body': {
                'required': 'Merci de décrire votre demande',
            },
        }

        widgets = {
            "topic": forms.Select(attrs={"class": "select"}),
            "full_name": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nom complet",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input",
                    "placeholder": "Email",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            # Le champ téléphone est obligatoire et comporte un attribut required pour la validation côté client.
            "phone": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Téléphone",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            "street": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Adresse",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Ville",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            "zip_code": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Code Postal",
                    "required": True,
                    "aria-required": "true",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "placeholder": "Votre message",
                    "rows": 4,
                }
            ),
        }