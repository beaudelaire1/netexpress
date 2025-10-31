"""
Formulaires pour la soumission de devis.

Cette app définit un formulaire personnalisé (non basé sur un ``ModelForm``)
qui capture les informations du client et du service souhaité.  Lors de
l'appel à ``save()``, un ``Client`` est créé puis un ``Quote`` est
enregistré avec le service facultatif et le message.

En 2025, l'interface utilisateur a été repensée pour être plus conviviale :
les widgets portent désormais l'attribut ``required`` et les pages
associent des visuels libres de droits issus d'Unsplash afin d'illustrer
chaque catégorie de service【668280112401708†L16-L63】.

Les widgets sont décorés de classes CSS pour s'intégrer au thème du site.
"""

from django import forms
from services.models import Service
from .models import Client, Quote
from decimal import Decimal


class DevisForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        label="Nom complet",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Nom complet",
            "required": True,
        }),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "Email",
            "required": True,
        }),
    )
    phone = forms.CharField(
        max_length=50,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Téléphone",
            "required": True,
        }),
    )
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
        label="Service souhaité",
        empty_label="Choisissez un service",
        widget=forms.Select(attrs={
            "class": "select",
        }),
    )
    message = forms.CharField(
        required=False,
        label="Message",
        widget=forms.Textarea(attrs={
            "class": "textarea",
            "placeholder": "Décrivez votre besoin…",
            "rows": 4,
        }),
    )

    def save(self):
        """Créer un client et un devis avec une ligne de service si sélectionné."""
        client = Client.objects.create(
            full_name=self.cleaned_data["full_name"],
            email=self.cleaned_data["email"],
            phone=self.cleaned_data["phone"],
        )
        quote = Quote(
            client=client,
            service=self.cleaned_data.get("service"),
            message=self.cleaned_data.get("message", ""),
            status="sent",
        )
        quote.save()
        selected_service = self.cleaned_data.get("service")
        if selected_service:
            from .models import QuoteItem
            QuoteItem.objects.create(
                quote=quote,
                service=selected_service,
                description=selected_service.title,
                quantity=1,
                unit_price=selected_service.base_price,
                tax_rate=Decimal("20.00"),
            )
            quote.compute_totals()
        return quote