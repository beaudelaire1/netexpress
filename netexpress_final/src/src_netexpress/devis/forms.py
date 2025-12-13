"""Formulaires pour la soumission de devis."""

from decimal import Decimal
from typing import Optional

from django import forms
from django.utils.translation import gettext_lazy as _

from services.models import Service
from .models import Client, Quote, QuoteRequest, QuoteRequestPhoto, QuoteItem

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class DevisForm(forms.Form):
    """Formulaire simple pour demander un devis."""

    full_name = forms.CharField(
        label="Nom complet",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Nom complet",
                "required": True,
                "aria-required": "true",
            }
        ),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "placeholder": "Email",
                "required": True,
                "aria-required": "true",
            }
        ),
    )
    phone = forms.CharField(
        label="Téléphone",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Téléphone",
                "required": True,
                "aria-required": "true",
            }
        ),
    )
    city = forms.CharField(
        label="Ville",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Ville",
                "required": True,
                "aria-required": "true",
            }
        ),
    )
    zip_code = forms.CharField(
        label="Code postal",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Code postal",
                "required": True,
                "aria-required": "true",
            }
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

    # Champs supplémentaires pour correspondre au cahier des charges 2025.
    SERVICE_TYPES = [
        ("nettoyage", "Nettoyage"),
        ("espaces_verts", "Espaces verts"),
        ("renovation", "Rénovation"),
    ]
    URGENCY_LEVELS = [
        ("standard", "Standard (sous 1 semaine)"),
        ("express", "Express (48 h)"),
        ("immediat", "Immédiat (24 h)"),
    ]

    service_type = forms.ChoiceField(
        label="Type de service",
        choices=SERVICE_TYPES,
        widget=forms.Select(
            attrs={"class": "select", "required": True, "aria-required": "true"}
        ),
    )

    surface = forms.IntegerField(
        label="Surface (m²)",
        min_value=1,
        widget=forms.HiddenInput(),
        required=False,
    )

    urgency = forms.ChoiceField(
        label="Urgence",
        choices=URGENCY_LEVELS,
        widget=forms.Select(
            attrs={"class": "select", "required": True, "aria-required": "true"}
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

        # Construit le message final en incluant les champs personnalisés si fournis
        message = cleaned.get("message", "")
        extra_lines = []
        # Ajout de la surface
        surface_val = cleaned.get("surface")
        if surface_val:
            extra_lines.append(f"Surface : {surface_val} m²")
        # Ajout de l'urgence
        urgency_val = cleaned.get("urgency")
        if urgency_val:
            # Convertit la clé en libellé pour l'enregistrement
            urgency_label = dict(self.URGENCY_LEVELS).get(urgency_val, urgency_val)
            extra_lines.append(f"Urgence : {urgency_label}")
        # Ajout du type de service
        service_type_val = cleaned.get("service_type")
        if service_type_val:
            service_label = dict(self.SERVICE_TYPES).get(service_type_val, service_type_val)
            extra_lines.append(f"Type de service : {service_label}")
        # Préfixe le message si des informations supplémentaires sont présentes
        if extra_lines:
            message = "\n".join(extra_lines) + "\n\n" + message
        


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
            message=message,
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


class QuoteRequestForm(forms.ModelForm):
    """Formulaire public pour déposer une demande de devis."""

    photos = forms.FileField(
        label=_("Photos (optionnel)"),
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
    )

    class Meta:
        model = QuoteRequest
        fields = ["client_name", "email", "phone", "address", "message", "preferred_date"]
        widgets = {
            "client_name": forms.TextInput(attrs={"class": "input", "placeholder": _("Nom complet")}),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": _("Email")}),
            "phone": forms.TextInput(attrs={"class": "input", "placeholder": _("Téléphone")}),
            "address": forms.TextInput(attrs={"class": "input", "placeholder": _("Adresse complète")}),
            "message": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "placeholder": _("Décrivez votre besoin (surface, fréquence, contraintes...)"),
                    "rows": 4,
                }
            ),
            "preferred_date": forms.DateInput(
                attrs={"class": "input", "type": "date"},
            ),
        }


class QuoteAdminForm(forms.ModelForm):
    """Formulaire d'édition des métadonnées d'un devis côté back‑office."""

    class Meta:
        model = Quote
        fields = ["client", "quote_request", "status", "issue_date", "valid_until", "message", "notes"]


class QuoteItemForm(forms.ModelForm):
    """Formulaire pour une ligne de devis dans l'éditeur dynamique."""

    class Meta:
        model = QuoteItem
        fields = ["service", "description", "quantity", "unit_price", "tax_rate"]
        widgets = {
            "service": forms.Select(attrs={"class": "select js-service"}),
            "description": forms.TextInput(attrs={"class": "input js-description"}),
            "quantity": forms.NumberInput(
                attrs={"class": "input js-quantity", "step": "0.1", "min": "0"}
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "input js-unit-price", "step": "0.01", "min": "0"}
            ),
            "tax_rate": forms.NumberInput(
                attrs={"class": "input js-tax-rate", "step": "0.01", "min": "0"}
            ),
        }
