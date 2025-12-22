"""Forms for admin portal functionality."""

from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from devis.models import Quote, Client
from factures.models import Invoice
from tasks.models import Task
from services.models import Service


class WorkerCreationForm(UserCreationForm):
    """Form for creating worker accounts in admin portal."""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Nom de famille'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'email@example.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': '0594123456'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the inherited fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Nom d\'utilisateur'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
        })
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Add to Workers group
            workers_group, created = Group.objects.get_or_create(name='Workers')
            user.groups.add(workers_group)
            
            # Create or update profile with phone number and worker role
            from accounts.models import Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.role = Profile.ROLE_WORKER  # Set role to worker
            profile.save()
        
        return user


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
    """Form for creating quotes in admin portal."""
    
    class Meta:
        model = Quote
        fields = ['client', 'service', 'message', 'notes', 'valid_until']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
            }),
            'service': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 4,
                'placeholder': 'Message pour le client...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'rows': 3,
                'placeholder': 'Notes internes (optionnel)...'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
                'type': 'date'
            }),
        }


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
            'assigned_to': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500'
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
        # Limit assigned_to to workers only
        self.fields['assigned_to'].queryset = User.objects.filter(groups__name='Workers').order_by('first_name', 'last_name')
        self.fields['assigned_to'].empty_label = "Sélectionner un ouvrier..."


class QuoteEmailForm(forms.Form):
    """Form for sending quotes by email."""
    
    recipient_email = forms.EmailField(
        label="Email du destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'client@example.com'
        })
    )
    subject = forms.CharField(
        label="Sujet",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Votre devis Nettoyage Express'
        })
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'rows': 6,
            'placeholder': 'Message personnalisé pour accompagner le devis...'
        })
    )
    
    def __init__(self, quote=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if quote:
            # Pre-fill with quote data
            self.fields['recipient_email'].initial = quote.client.email
            self.fields['subject'].initial = f"Votre devis {quote.number} - Nettoyage Express"
            self.fields['message'].initial = f"""Bonjour {quote.client.full_name},

Veuillez trouver ci-joint votre devis {quote.number}.

Nous restons à votre disposition pour toute question.

Cordialement,
L'équipe Nettoyage Express"""


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
    """Form for sending quote by email."""
    
    recipient_email = forms.EmailField(
        label="Email du destinataire",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'client@example.com'
        })
    )
    subject = forms.CharField(
        label="Sujet",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'placeholder': 'Votre devis Nettoyage Express'
        })
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-ne-primary-500',
            'rows': 6,
            'placeholder': 'Bonjour,\n\nVeuillez trouver ci-joint votre devis.\n\nCordialement,\nL\'équipe Nettoyage Express'
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