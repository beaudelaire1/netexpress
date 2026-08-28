from __future__ import annotations

from pathlib import Path

from django import forms

from accounts.models import Profile
from accounts.portal import get_user_role
from .exchange_file_validation import validate_exchange_document
from .models import AccountingExchange, AccountingExchangeDocument

ACCEPTED_EXCHANGE_FILES = ".pdf,.png,.jpg,.jpeg,.csv,.xlsx,.docx"


class _ExchangeUploadMixin:
    user = None

    def _configure_upload_fields(self):
        if "file" in self.fields:
            self.fields["file"].widget.attrs.update(
                {"accept": ACCEPTED_EXCHANGE_FILES, "data-exchange-file-input": "1"}
            )
            self.fields["file"].help_text = (
                "PDF, JPEG, PNG, CSV, XLSX ou DOCX · 10 Mo maximum."
            )
        if "visibility" in self.fields:
            is_admin = get_user_role(self.user) in {
                Profile.ROLE_ADMIN_BUSINESS,
                Profile.ROLE_ADMIN_TECHNICAL,
            }
            if not is_admin:
                self.fields.pop("visibility")

    def _clean_document_title(self, cleaned_data):
        title = (cleaned_data.get("document_title") or "").strip()
        file = cleaned_data.get("file")
        if file and not title:
            title = Path(file.name).stem[:200] or "Document"
        cleaned_data["document_title"] = title
        return cleaned_data

    def document_visibility(self):
        if "visibility" not in self.cleaned_data:
            return AccountingExchangeDocument.Visibility.SHARED
        return self.cleaned_data.get("visibility") or AccountingExchangeDocument.Visibility.SHARED


class ExchangeCreateForm(_ExchangeUploadMixin, forms.Form):
    subject = forms.CharField(
        label="Sujet",
        max_length=200,
        widget=forms.TextInput(
            attrs={"placeholder": "Ex. : TVA à vérifier sur la facture FAC-2026-014"}
        ),
    )
    kind = forms.ChoiceField(label="Type d’échange", choices=AccountingExchange.Kind.choices)
    priority = forms.ChoiceField(
        label="Priorité",
        choices=AccountingExchange.Priority.choices,
        initial=AccountingExchange.Priority.NORMAL,
    )
    message = forms.CharField(
        label="Message",
        required=False,
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": "Donnez le contexte utile au traitement de votre demande…",
                "data-character-counter": "4000",
            }
        ),
    )
    file = forms.FileField(
        label="Document à joindre",
        required=False,
        validators=[validate_exchange_document],
    )
    document_title = forms.CharField(
        label="Titre du document",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Le nom du fichier sera utilisé si vide"}),
    )
    document_type = forms.ChoiceField(
        label="Type de document",
        required=False,
        choices=AccountingExchangeDocument.Type.choices,
        initial=AccountingExchangeDocument.Type.OTHER,
    )
    visibility = forms.ChoiceField(
        label="Visibilité",
        required=False,
        choices=AccountingExchangeDocument.Visibility.choices,
        initial=AccountingExchangeDocument.Visibility.SHARED,
        help_text="Un document interne NetExpress n’est jamais révélé au cabinet.",
    )

    def __init__(self, *args, user=None, mode=None, **kwargs):
        self.user = user
        self.mode = mode if mode in {"message", "document"} else "message"
        super().__init__(*args, **kwargs)
        self._configure_upload_fields()
        if self.mode == "document":
            self.fields["kind"].initial = AccountingExchange.Kind.DOCUMENT_DELIVERY
            self.fields["message"].widget.attrs["placeholder"] = (
                "Ajoutez si nécessaire un message d’accompagnement au document…"
            )

    def clean(self):
        data = super().clean()
        self._clean_document_title(data)
        message = (data.get("message") or "").strip()
        data["message"] = message
        file = data.get("file")
        if self.mode == "document" and not file:
            self.add_error("file", "Sélectionnez le document à mettre à disposition.")
        elif not message and not file:
            raise forms.ValidationError(
                "Ajoutez un message ou un document avant de créer l’échange."
            )
        return data


class ExchangeReplyForm(_ExchangeUploadMixin, forms.Form):
    content = forms.CharField(
        label="Réponse",
        required=False,
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Rédigez votre réponse…",
                "data-character-counter": "4000",
            }
        ),
    )
    file = forms.FileField(
        label="Joindre un document",
        required=False,
        validators=[validate_exchange_document],
    )
    document_title = forms.CharField(
        label="Titre du document",
        required=False,
        max_length=200,
    )
    document_type = forms.ChoiceField(
        label="Type de document",
        required=False,
        choices=AccountingExchangeDocument.Type.choices,
        initial=AccountingExchangeDocument.Type.OTHER,
    )
    visibility = forms.ChoiceField(
        label="Visibilité",
        required=False,
        choices=AccountingExchangeDocument.Visibility.choices,
        initial=AccountingExchangeDocument.Visibility.SHARED,
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._configure_upload_fields()

    def clean(self):
        data = super().clean()
        self._clean_document_title(data)
        content = (data.get("content") or "").strip()
        data["content"] = content
        if not content and not data.get("file"):
            raise forms.ValidationError("Rédigez une réponse ou joignez un document.")
        return data


class ExchangeDocumentForm(_ExchangeUploadMixin, forms.Form):
    file = forms.FileField(
        label="Document",
        validators=[validate_exchange_document],
    )
    document_title = forms.CharField(
        label="Titre du document",
        required=False,
        max_length=200,
    )
    document_type = forms.ChoiceField(
        label="Type de document",
        choices=AccountingExchangeDocument.Type.choices,
        initial=AccountingExchangeDocument.Type.OTHER,
    )
    visibility = forms.ChoiceField(
        label="Visibilité",
        required=False,
        choices=AccountingExchangeDocument.Visibility.choices,
        initial=AccountingExchangeDocument.Visibility.SHARED,
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._configure_upload_fields()

    def clean(self):
        data = super().clean()
        return self._clean_document_title(data)
