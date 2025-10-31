"""
Forms for quote submissions.

These forms encapsulate the validation rules for incoming quote requests.  A
model form is used to easily persist the data into the database.  Additional
helpers could be added here to customise error messages or widget styling.
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