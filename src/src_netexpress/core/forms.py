"""Forms for admin portal functionality."""

from decimal import Decimal
from django import forms
from django.contrib.auth.models import User, Group
from django.forms import inlineformset_factory
from devis.models import Quote, QuoteItem, Client
from factures.models import Invoice
from tasks.models import Task
from services.models import Service


class WorkerCreationForm(forms.Form):
    """Form for creating worker accounts in admin portal.
    
    Le mot de passe est généré automatiquement par le service.
    L'ouvrier devra le changer à sa première connexion.
    """
    
    first_name = forms.CharField(
        label="Prénom",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        label="Nom",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Nom de famille'
        })
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'email@example.com'
        })
    )
    phone = forms.CharField(
        label="Téléphone",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': '0594123456'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un utilisateur avec cet email existe déjà.")
        return email


class ClientCreationForm(forms.ModelForm):
    """Form for creating client accounts in admin portal."""
    
    class Meta:
        model = Client
        fields = ['full_name', 'email', 'phone', 'company', 'address_line', 'city', 'zip_code']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Nom complet du client'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': '0594123456'
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Nom de l\'entreprise (optionnel)'
            }),
            'address_line': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Adresse'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Ville'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': '97300'
            }),
        }


class QuoteCreationForm(forms.ModelForm):
    """Form for creating quotes in admin portal - like Django Admin."""
    
    class Meta:
        model = Quote
        fields = ['client', 'status', 'issue_date', 'valid_until', 'message', 'notes']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
            }),
            'issue_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 3,
                'placeholder': 'Message pour le client...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 2,
                'placeholder': 'Notes internes (optionnel)...'
            }),
        }


class QuoteItemForm(forms.ModelForm):
    """Form for a single quote line item."""
    
    class Meta:
        model = QuoteItem
        fields = ['service', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'service': forms.Select(attrs={
                'class': 'w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-ne-primary-500 service-select',
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-ne-primary-500',
                'placeholder': 'Description de la ligne...'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-20 px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-ne-primary-500 text-right qty-input',
                'step': '1',
                'min': '1',
                'value': '1'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'w-24 px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-ne-primary-500 text-right price-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'w-20 px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-ne-primary-500 text-right tva-input',
                'step': '0.01',
                'value': '0.00'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(is_active=True).order_by('title')
        self.fields['service'].required = False
        self.fields['service'].empty_label = "-- Libre --"
        self.fields['description'].required = True
        # Set default values
        if not self.initial.get('quantity'):
            self.initial['quantity'] = Decimal('1.00')
        if not self.initial.get('tax_rate'):
            self.initial['tax_rate'] = Decimal('20.00')


# Formset for quote items - like Django Admin TabularInline
QuoteItemFormset = inlineformset_factory(
    Quote,
    QuoteItem,
    form=QuoteItemForm,
    extra=3,  # Show 3 empty lines by default
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class TaskCreationForm(forms.ModelForm):
    """Form for creating tasks in admin portal."""
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'location', 'team', 'assigned_to', 'start_date', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Titre de la tâche'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 4,
                'placeholder': 'Description détaillée de la tâche...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Lieu d\'intervention'
            }),
            'team': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Équipe responsable'
            }),
            'assigned_to': forms.SelectMultiple(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'size': '5'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit assigned_to to workers only (multiple selection)
        self.fields['assigned_to'].queryset = User.objects.filter(groups__name='Workers').order_by('first_name', 'last_name')
        self.fields['assigned_to'].label = "Ouvriers assignés"
        self.fields['assigned_to'].help_text = "Maintenez Ctrl pour sélectionner plusieurs ouvriers"
        self.fields['assigned_to'].required = False


class QuoteEmailForm(forms.Form):
    """Form for sending quotes by email.
    
    Le message est généré automatiquement via le template stylisé modele_quote.html.
    Seul l'email du destinataire est modifiable.
    """
    
    recipient_email = forms.EmailField(
        label="Email du destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'client@example.com'
        })
    )
    
    def __init__(self, quote=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if quote:
            # Pre-fill with client email
            self.fields['recipient_email'].initial = quote.client.email


class InvoiceCreationForm(forms.ModelForm):
    """Form for creating invoices in admin portal."""
    
    class Meta:
        model = Invoice
        fields = ['quote', 'command_ref', 'due_date', 'notes', 'payment_terms']
        widgets = {
            'quote': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
            }),
            'command_ref': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'placeholder': 'Référence bon de commande (optionnel)'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 3,
                'placeholder': 'Notes internes (optionnel)...'
            }),
            'payment_terms': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 2,
                'placeholder': 'Conditions de paiement...'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit quotes to accepted ones only
        self.fields['quote'].queryset = Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).order_by('-issue_date')
        self.fields['quote'].empty_label = "Sélectionner un devis accepté..."


class SendQuoteEmailForm(forms.Form):
    """Form for sending quote by email.
    
    Le message est généré automatiquement via le template stylisé.
    Seul l'email du destinataire est modifiable.
    """
    
    recipient_email = forms.EmailField(
        label="Email du destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'client@example.com'
        })
    )
    include_pdf = forms.BooleanField(
        label="Inclure le PDF en pièce jointe",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-ne-primary-600 focus:ring-ne-primary-500'
        })
    )