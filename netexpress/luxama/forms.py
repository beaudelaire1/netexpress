from django import forms
from .models import Devis, Service, Tache, Client

class ContactForm(forms.Form):
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=15, label="Téléphone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    motif = forms.ChoiceField(
        choices=[
            ('nettoyage', 'Devis Nettoyage'),
            ('peinture', 'Projet de Peinture'),
            ('espacevert', 'Espace Vert'),
            ('renovation', 'Rénovation'),
            ('bricolage', 'Petits Travaux'),
            ('autre', 'Autre')
        ],
        label="Motif de contact",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    message = forms.CharField(label="Message", widget=forms.Textarea(attrs={'class': 'form-control'}))


class DevisForm(forms.ModelForm):
    class Meta:
        model = Devis
        fields = ['client', 'prix_initial', 'reduction']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        prix_initial = cleaned_data.get("prix_initial", 0)
        reduction = cleaned_data.get("reduction", 0)

        if prix_initial < 0 or reduction < 0:
            raise forms.ValidationError("Prix et réduction doivent être positifs.")

        return cleaned_data


class TacheForm(forms.ModelForm):
    class Meta:
        model = Tache
        fields = ['titre', 'description', 'localisation', 'statut', 'date_debut', 'date_fin']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'localisation': forms.TextInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
