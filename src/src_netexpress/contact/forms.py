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
        # Minimisation des données (RGPD art. 5.1.c) : on ne collecte que les
        # informations réellement exploitées pour traiter la demande. Le champ
        # « rue » (street) a été retiré car il était demandé — et même requis —
        # sans jamais être utilisé (absent de l'email de notification comme du
        # back-office).
        fields = ["topic", "full_name", "email", "phone", "city", "zip_code", "body"]
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