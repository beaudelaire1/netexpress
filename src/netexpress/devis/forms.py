"""
Formulaires pour la soumission de devis.

Cette app définit un formulaire personnalisé (non basé sur un ``ModelForm``)
qui capture les informations du client et du service souhaité.  Lors de
l'appel à ``save()``, un ``Client`` est créé puis un ``Quote`` est
enregistré avec le service facultatif et le message.

En 2025, l'interface utilisateur a été repensée pour être plus conviviale :
les widgets portent désormais l'attribut ``required`` et les pages
associent des visuels locaux (``static/img``) afin d'illustrer
chaque catégorie de service.  Toute dépendance à des images externes
comme Unsplash a été retirée【668280112401708†L16-L63】.

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

    # Champ optionnel pour téléverser une ou plusieurs photos.  L'upload est
    # géré dans la vue car un ``Form`` classique ne peut pas facilement
    # manipuler plusieurs fichiers sur un ``ModelForm`` inexistant.  Le
    # widget `multiple` permet de sélectionner plusieurs images.
    images = forms.FileField(
        required=False,
        label="Photos (facultatif)",
        widget=forms.ClearableFileInput(attrs={
            #"multiple": True,
            "class": "file-input",
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
            # Mettre à jour les totaux du devis.  Cela calcule le HT, la
            # TVA et le TTC avant de générer le PDF et d'envoyer une
            # notification.  Sans cet appel, le total resterait à zéro.
            quote.compute_totals()
        # Générer automatiquement un PDF professionnel pour le devis.
        # Cette étape est exécutée même lorsqu'aucun service n'est
        # sélectionné afin de garder une trace formalisée de la demande.
        try:
            quote.generate_pdf(attach=True)
        except ImportError:
            # ReportLab n'est pas installé : poursuivre sans générer le PDF.
            pass
        return quote