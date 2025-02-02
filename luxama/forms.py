from django import forms
from .models import Devis, Service, Tache, Client


class ContactForm(forms.Form):
    nom = forms.CharField(max_length=100, label="Nom")
    prenom = forms.CharField(max_length=100, label="Prenom")
    email = forms.EmailField(label="Email")
    telephone = forms.CharField(max_length=15, label="Telephone")
    motif = forms.ChoiceField(
        choices=[
            ('nettoyage', 'Devis Nettoyage'),
            ('peinture', 'Projet de Peinture'),
            ('espacevert', 'Espace Vert'),
            ('renovation', 'Rénovation'),
            ('bricolage', 'Petits Travaux'),
            ('autre', 'Autre')
        ],
        label="Motif de contact"
    )
    message = forms.CharField(label="Message", widget=forms.Textarea)


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



"""class ajouterServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['nom', 'prix', 'service']
        labels = {
            'nom': 'Nom du service',
            'prix': 'Prix du service',
            'service': 'Catégorie du service'
        }

        error_messages = {
            'nom': {
                'max_length': 'Le nom du service est trop long.'
            }
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'})
        }
"""