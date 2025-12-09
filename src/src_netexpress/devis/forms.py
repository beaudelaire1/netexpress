"""Formulaires pour la soumission de devis."""

from decimal import Decimal
from typing import Optional

from django import forms

from services.models import Service
from .models import Client, Quote


class DevisForm(forms.Form):
    """Formulaire simple pour demander un devis."""

    full_name = forms.CharField(
        label="Nom complet",
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Nom complet", "required": True}
        ),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "input", "placeholder": "Email", "required": True}
        ),
    )
    phone = forms.CharField(
        label="Téléphone",
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Téléphone", "required": True}
        ),
    )
    city = forms.CharField(
        label="Ville",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Ville", "required": True}
        ),
    )
    zip_code = forms.CharField(
        label="Code postal",
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Code postal", "required": True}
        ),
    )
    service = forms.ModelChoiceField(
        label="Service souhaité",
        queryset=Service.objects.filter(is_active=True).order_by("title"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
    )
    message = forms.CharField(
        label="Votre demande",
        widget=forms.Textarea(
            attrs={
                "class": "textarea",
                "placeholder": "Décrivez votre besoin (surface, fréquence, contraintes...) ",
                "rows": 4,
            }
        ),
    )
    images = forms.FileField(
        label="Photos (optionnel)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"multiple": False}),
    )

    def save(self) -> Quote:
        """Crée un ``Client`` et un ``Quote`` à partir des données du formulaire."""
        cleaned = self.cleaned_data
        service: Optional[Service] = cleaned.get("service")  # type: ignore[assignment]


        client = Client.objects.create(
            full_name=cleaned["full_name"],
            email=cleaned["email"],
            phone=cleaned["phone"],
            city=cleaned["city"],
            zip_code=cleaned["zip_code"],
        )

        quote = Quote.objects.create(
            client=client,
            service=service,
            message=cleaned.get("message", ""),
            total_ht=Decimal("0.00"),
            tva=Decimal("0.00"),
            total_ttc=Decimal("0.00"),
        )

        if hasattr(quote, "compute_totals") and callable(getattr(quote, "compute_totals")):
            quote.compute_totals()  # type: ignore[call-arg]

        if hasattr(quote, "generate_pdf") and callable(getattr(quote, "generate_pdf")):
            try:
                quote.generate_pdf(attach=True)  # type: ignore[call-arg]
            except ImportError:
                pass

        return quote
