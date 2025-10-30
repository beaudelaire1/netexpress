"""
Formulaires pour les demandes de devis (app ``quotes``).

Ces formulaires encapsulent les règles de validation pour les demandes de
devis.  La refonte de 2025 a rendu le champ téléphone obligatoire pour
améliorer le suivi commercial et a harmonisé les widgets avec le design
du reste du site.  Les pages qui utilisent ces formulaires affichent
désormais des illustrations libres de droits issues d'Unsplash pour
illustrer les services proposés【668280112401708†L16-L63】.
"""

from django import forms
from .models import Quote


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["name", "phone", "email", "service", "message"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "input", "placeholder": "Nom complet", "required": True
            }),
            "phone": forms.TextInput(attrs={
                "class": "input", "placeholder": "Téléphone", "required": True
            }),
            "email": forms.EmailInput(attrs={
                "class": "input", "placeholder": "Email", "required": True
            }),
            "service": forms.TextInput(attrs={
                "class": "input", "placeholder": "Service souhaité"
            }),
            "message": forms.Textarea(attrs={
                "class": "textarea", "placeholder": "Décrivez votre besoin…", "rows": 4
            }),
        }