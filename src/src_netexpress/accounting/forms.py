import hashlib
from pathlib import Path
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.file_validation import validate_document
from .models import AccountingDocument, SupplierInvoice


class PeriodForm(forms.Form):
    date_from = forms.DateField(label="Du", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    date_to = forms.DateField(label="Au", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    q = forms.CharField(label="Rechercher", required=False, max_length=100)

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            today = timezone.localdate()
            data["date_from"] = data.get("date_from") or today.replace(month=1, day=1).isoformat()
            data["date_to"] = data.get("date_to") or today.replace(month=12, day=31).isoformat()
        super().__init__(data, *args, **kwargs)

    def clean(self):
        data = super().clean()
        today = timezone.localdate()
        data["date_from"] = data.get("date_from") or today.replace(month=1, day=1)
        data["date_to"] = data.get("date_to") or today.replace(month=12, day=31)
        if data["date_from"] > data["date_to"]:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")
        return data


class PrivateUploadForm(forms.ModelForm):
    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file and (not self.instance.pk or "file" in self.changed_data):
            validate_document(file)
            digest = hashlib.sha256()
            for chunk in file.chunks():
                digest.update(chunk)
            file.seek(0)
            self.instance.file_sha256 = digest.hexdigest()
            for model in (SupplierInvoice, AccountingDocument):
                existing = model.objects.filter(file_sha256=digest.hexdigest())
                if isinstance(self.instance, model):
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise forms.ValidationError("Cette pièce a déjà été déposée : doublon détecté.")
        return file


class SupplierInvoiceForm(PrivateUploadForm):
    class Meta:
        model = SupplierInvoice
        fields = ["supplier_name", "reference", "issue_date", "due_date", "total_ttc", "vat_amount", "category", "paid_on", "file", "notes"]
        widgets = {
            **{f: forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d") for f in ("issue_date", "due_date", "paid_on")},
            "notes": forms.Textarea(attrs={"rows": 3}),
            "file": forms.FileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["file"].help_text = "PDF, JPEG ou PNG · 10 Mo maximum. Seul le fichier est obligatoire au dépôt."
        self.fields["supplier_name"].widget.attrs["placeholder"] = "Ex. : votre fournisseur"
        self.fields["total_ttc"].widget.attrs["placeholder"] = "À compléter si vous le connaissez"
        self.fields["vat_amount"].help_text = "Laissez vide si inconnue ; indiquez 0 uniquement si la pièce ne comporte pas de TVA."

    @property
    def detail_fields(self):
        return [self[name] for name in ("reference", "issue_date", "vat_amount", "due_date", "paid_on", "category", "notes")]

    def clean_category(self):
        return self.cleaned_data.get("category") or SupplierInvoice.Category.OTHER

    def clean(self):
        data = super().clean()
        key = " ".join(data.get("supplier_name", "").casefold().split())
        reference = data.get("reference", "").strip()
        if key and reference and SupplierInvoice.objects.filter(supplier_key=key, reference=reference).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Une facture de ce fournisseur porte déjà ce numéro.")
        return data


class AccountingDocumentForm(PrivateUploadForm):
    class Meta:
        model = AccountingDocument
        fields = ["file", "kind", "title", "document_date", "notes"]
        widgets = {
            "file": forms.FileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg"}),
            "document_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "kind", "document_date"):
            self.fields[name].required = False
        self.fields["file"].help_text = "PDF, JPEG ou PNG · 10 Mo maximum."
        self.fields["title"].help_text = "Le nom du fichier sera utilisé si vous laissez ce champ vide."
        self.fields["document_date"].help_text = "Sert aux filtres et aux exports. Par défaut : aujourd’hui."

    def clean_kind(self):
        return self.cleaned_data.get("kind") or AccountingDocument.Kind.OTHER

    def clean_document_date(self):
        return self.cleaned_data.get("document_date") or timezone.localdate()

    def clean(self):
        data = super().clean()
        if not data.get("title") and data.get("file"):
            data["title"] = Path(data["file"].name).stem[:200] or "Document"
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
