import hashlib
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.file_validation import validate_document
from .models import SupplierInvoice


class PeriodForm(forms.Form):
    date_from = forms.DateField(label="Du", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    date_to = forms.DateField(label="Au", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    q = forms.CharField(label="Rechercher", required=False, max_length=100)

    def clean(self):
        data = super().clean()
        today = timezone.localdate()
        data["date_from"] = data.get("date_from") or today.replace(month=1, day=1)
        data["date_to"] = data.get("date_to") or today.replace(month=12, day=31)
        if data["date_from"] > data["date_to"]:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")
        return data


class SupplierInvoiceForm(forms.ModelForm):
    class Meta:
        model = SupplierInvoice
        fields = ["supplier_name", "reference", "issue_date", "due_date", "total_ttc", "vat_amount", "category", "paid_on", "file", "notes"]
        widgets = {
            **{f: forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d") for f in ("issue_date", "due_date", "paid_on")},
            "notes": forms.Textarea(attrs={"rows": 3}),
            "file": forms.FileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg"}),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file and (not self.instance.pk or "file" in self.changed_data):
            validate_document(file)
            digest = hashlib.sha256()
            for chunk in file.chunks():
                digest.update(chunk)
            file.seek(0)
            self.instance.file_sha256 = digest.hexdigest()
            if SupplierInvoice.objects.filter(file_sha256=digest.hexdigest()).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Cette pièce a déjà été déposée : doublon détecté.")
        return file

    def clean(self):
        data = super().clean()
        key = " ".join(data.get("supplier_name", "").casefold().split())
        reference = data.get("reference", "").strip()
        if SupplierInvoice.objects.filter(supplier_key=key, reference=reference).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Une facture de ce fournisseur porte déjà ce numéro.")
        return data


class AccountantInvitationForm(forms.Form):
    email = forms.EmailField(label="Email professionnel")
    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    accounting_firm = forms.CharField(label="Cabinet comptable", max_length=200)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse est déjà utilisée. Utilisez un compte dédié au cabinet.")
        return email


class ReviewForm(forms.Form):
    note = forms.CharField(label="Note de contrôle", required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))
    fingerprint = forms.CharField(required=False, widget=forms.HiddenInput)
