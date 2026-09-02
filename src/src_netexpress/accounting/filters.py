from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django import forms
from django.db.models import Q
from django.utils import timezone

from factures.models import Invoice

from .models import (
    AccountingDocument,
    AccountingExchange,
    AccountingExchangeDocument,
    SupplierInvoice,
)
from .services import (
    ACCOUNTING_VISIBLE_INVOICE_STATUSES,
    complete_purchases,
    incomplete_purchases,
    is_reviewed,
    issued_invoices,
)


REVIEW_CHOICES = (
    ("", "Tous les contrôles"),
    ("pending", "À contrôler"),
    ("reviewed", "Contrôlé"),
)

OPEN_EXCHANGE_STATUSES = (
    AccountingExchange.Status.OPEN,
    AccountingExchange.Status.WAITING_NETEXPRESS,
    AccountingExchange.Status.WAITING_ACCOUNTANT,
)

EXCHANGE_LINK_CHOICES = (
    ("", "Avec ou sans échange"),
    ("open", "Avec échange ouvert"),
    ("no_open", "Sans échange ouvert"),
)

VISIBLE_INVOICE_STATUS_CHOICES = tuple(
    (value, label)
    for value, label in Invoice.InvoiceStatus.choices
    if value in ACCOUNTING_VISIBLE_INVOICE_STATUSES
)


class BaseAccountingFilterForm(forms.Form):
    """Base des filtres de file.

    Les pièces comptables sont affichées sur l'exercice courant par défaut.
    Les échanges dérogent à cette règle : un fil non résolu doit rester
    retrouvable même s'il a été ouvert sur un exercice antérieur.
    """

    default_period = True
    advanced_fields: tuple[str, ...] = ()

    q = forms.CharField(
        label="Recherche",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"autocomplete": "off"}),
    )
    date_from = forms.DateField(
        label="Du",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    date_to = forms.DateField(
        label="Au",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, data=None, *args, **kwargs):
        if data is not None and self.default_period:
            data = data.copy()
            today = timezone.localdate()
            data["date_from"] = data.get("date_from") or today.replace(month=1, day=1).isoformat()
            data["date_to"] = data.get("date_to") or today.replace(month=12, day=31).isoformat()
        super().__init__(data, *args, **kwargs)

    def clean(self):
        data = super().clean()
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        if self.default_period:
            today = timezone.localdate()
            date_from = date_from or today.replace(month=1, day=1)
            date_to = date_to or today.replace(month=12, day=31)
            data["date_from"] = date_from
            data["date_to"] = date_to

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")

        amount_min = data.get("amount_min")
        amount_max = data.get("amount_max")
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            raise forms.ValidationError("Le montant minimum ne peut pas dépasser le montant maximum.")
        return data

    def active_advanced_count(self, request) -> int:
        return sum(bool(request.GET.get(name)) for name in self.advanced_fields)

    def active_filter_chips(self, request):
        chips = []
        for name, field in self.fields.items():
            raw = (request.GET.get(name) or "").strip()
            if not raw:
                continue

            display = raw
            if isinstance(field, forms.BooleanField):
                display = "Oui"
            elif getattr(field, "choices", None):
                display = dict(field.choices).get(raw, raw)
            elif name in {"date_from", "date_to"}:
                try:
                    display = datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError:
                    pass
            elif name in {"amount_min", "amount_max"}:
                display = f"{raw} €"

            params = request.GET.copy()
            params.pop(name, None)
            params.pop("page", None)
            query = params.urlencode()
            remove_url = f"{request.path}?{query}" if query else request.path
            prefix = {
                "q": "Recherche",
                "date_from": "Depuis",
                "date_to": "Jusqu’au",
                "amount_min": "Min.",
                "amount_max": "Max.",
            }.get(name, field.label)
            chips.append(
                {
                    "name": name,
                    "label": f"{prefix} : {display}",
                    "remove_url": remove_url,
                }
            )
        return chips


class SalesFilterForm(BaseAccountingFilterForm):
    status = forms.ChoiceField(
        label="Statut facture",
        required=False,
        choices=(("", "Tous les statuts"),) + VISIBLE_INVOICE_STATUS_CHOICES,
    )
    review = forms.ChoiceField(label="Contrôle", required=False, choices=REVIEW_CHOICES)
    document_type = forms.ChoiceField(
        label="Nature",
        required=False,
        choices=(
            ("", "Factures et avoirs"),
            ("invoice", "Factures uniquement"),
            ("credit_note", "Avoirs uniquement"),
        ),
    )
    amount_min = forms.DecimalField(
        label="TTC minimum", required=False, min_value=Decimal("0"), decimal_places=2
    )
    amount_max = forms.DecimalField(
        label="TTC maximum", required=False, min_value=Decimal("0"), decimal_places=2
    )
    exchange = forms.ChoiceField(
        label="Échanges", required=False, choices=EXCHANGE_LINK_CHOICES
    )

    advanced_fields = (
        "status",
        "review",
        "document_type",
        "amount_min",
        "amount_max",
        "exchange",
    )


class SupplierFilterForm(BaseAccountingFilterForm):
    category = forms.ChoiceField(
        label="Catégorie",
        required=False,
        choices=(("", "Toutes les catégories"),) + tuple(SupplierInvoice.Category.choices),
    )
    review = forms.ChoiceField(label="Contrôle", required=False, choices=REVIEW_CHOICES)
    payment = forms.ChoiceField(
        label="Paiement",
        required=False,
        choices=(
            ("", "Tous les paiements"),
            ("paid", "Payée"),
            ("unpaid", "Non payée"),
            ("overdue", "Échéance dépassée"),
        ),
    )
    completeness = forms.ChoiceField(
        label="Préparation",
        required=False,
        choices=(
            ("", "Toutes les pièces"),
            ("complete", "Complètes"),
            ("incomplete", "Brouillons à compléter"),
        ),
    )
    amount_min = forms.DecimalField(
        label="TTC minimum", required=False, min_value=Decimal("0"), decimal_places=2
    )
    amount_max = forms.DecimalField(
        label="TTC maximum", required=False, min_value=Decimal("0"), decimal_places=2
    )
    exchange = forms.ChoiceField(
        label="Échanges", required=False, choices=EXCHANGE_LINK_CHOICES
    )

    advanced_fields = (
        "category",
        "review",
        "payment",
        "completeness",
        "amount_min",
        "amount_max",
        "exchange",
    )

    def __init__(self, data=None, *args, accounting_admin=False, **kwargs):
        super().__init__(data, *args, **kwargs)
        if not accounting_admin:
            self.fields.pop("completeness", None)
            self.advanced_fields = tuple(
                name for name in self.advanced_fields if name != "completeness"
            )


class DocumentFilterForm(BaseAccountingFilterForm):
    kind = forms.ChoiceField(
        label="Type de document",
        required=False,
        choices=(("", "Tous les types"),) + tuple(AccountingDocument.Kind.choices),
    )
    review = forms.ChoiceField(
        label="Contrôle",
        required=False,
        choices=(
            ("", "Tous les contrôles"),
            ("pending", "À vérifier"),
            ("reviewed", "Vérifié"),
        ),
    )
    source = forms.ChoiceField(
        label="Origine",
        required=False,
        choices=(
            ("", "Toutes les origines"),
            ("direct", "Déposé dans le dossier"),
            ("exchange", "Classé depuis un échange"),
        ),
    )
    exchange = forms.ChoiceField(
        label="Échanges", required=False, choices=EXCHANGE_LINK_CHOICES
    )

    advanced_fields = ("kind", "review", "source", "exchange")


class ExchangeFilterForm(BaseAccountingFilterForm):
    # Une conversation ouverte en décembre doit encore être visible en janvier.
    default_period = False

    status = forms.ChoiceField(
        label="Statut",
        required=False,
        choices=(("", "Tous les statuts"),) + tuple(AccountingExchange.Status.choices),
    )
    kind = forms.ChoiceField(
        label="Type de demande",
        required=False,
        choices=(("", "Tous les types"),) + tuple(AccountingExchange.Kind.choices),
    )
    priority = forms.ChoiceField(
        label="Priorité",
        required=False,
        choices=(("", "Toutes les priorités"),) + tuple(AccountingExchange.Priority.choices),
    )
    documents = forms.ChoiceField(
        label="Pièces jointes",
        required=False,
        choices=(
            ("", "Avec ou sans document"),
            ("with", "Avec document"),
            ("without", "Sans document"),
        ),
    )
    unread = forms.BooleanField(label="Non lus uniquement", required=False)
    context = forms.ChoiceField(
        label="Contexte",
        required=False,
        choices=(
            ("", "Tous les contextes"),
            ("general", "Échange général"),
            ("invoice", "Facture client"),
            ("quote", "Devis lié"),
            ("supplier", "Facture fournisseur"),
            ("document", "Autre document"),
        ),
    )

    advanced_fields = (
        "status",
        "kind",
        "priority",
        "documents",
        "unread",
        "context",
    )


def _apply_period(queryset, field_name, data):
    return queryset.filter(
        **{
            f"{field_name}__gte": data["date_from"],
            f"{field_name}__lte": data["date_to"],
        }
    )


def _apply_exchange_link_filter(queryset, value: str):
    if value == "open":
        return queryset.filter(
            accounting_exchanges__status__in=OPEN_EXCHANGE_STATUSES
        ).distinct()
    if value == "no_open":
        return queryset.exclude(
            accounting_exchanges__status__in=OPEN_EXCHANGE_STATUSES
        ).distinct()
    return queryset


def filtered_sales(request):
    form = SalesFilterForm(request.GET)
    if not form.is_valid():
        return form, []

    data = form.cleaned_data
    queryset = _apply_period(issued_invoices(), "issue_date", data)
    if data.get("q"):
        queryset = queryset.filter(
            Q(number__icontains=data["q"])
            | Q(client__full_name__icontains=data["q"])
            | Q(client__email__icontains=data["q"])
            | Q(invoice_items__description__icontains=data["q"])
        ).distinct()
    if data.get("status"):
        queryset = queryset.filter(status=data["status"])
    if data.get("document_type") == "invoice":
        queryset = queryset.filter(is_credit_note=False)
    elif data.get("document_type") == "credit_note":
        queryset = queryset.filter(is_credit_note=True)
    if data.get("amount_min") is not None:
        queryset = queryset.filter(total_ttc__gte=data["amount_min"])
    if data.get("amount_max") is not None:
        queryset = queryset.filter(total_ttc__lte=data["amount_max"])
    queryset = _apply_exchange_link_filter(queryset, data.get("exchange") or "")

    # Le contrôle valide dépend d'une empreinte du contenu complet de la facture.
    # On ne matérialise donc la collection que lorsqu'un filtre de contrôle
    # l'exige ; les autres recherches restent paginables en SQL.
    review = data.get("review")
    if not review:
        return form, queryset

    invoices = list(queryset)
    if review == "pending":
        invoices = [invoice for invoice in invoices if not is_reviewed(invoice)]
    elif review == "reviewed":
        invoices = [invoice for invoice in invoices if is_reviewed(invoice)]
    return form, invoices


def filtered_suppliers(request):
    form = SupplierFilterForm(request.GET, accounting_admin=request.accounting_admin)
    if not form.is_valid():
        return form, SupplierInvoice.objects.none()

    data = form.cleaned_data
    queryset = SupplierInvoice.objects.filter(
        Q(issue_date__range=(data["date_from"], data["date_to"]))
        | Q(
            issue_date__isnull=True,
            created_at__date__range=(data["date_from"], data["date_to"]),
        )
    )

    if not request.accounting_admin:
        queryset = complete_purchases(queryset)
    elif data.get("completeness") == "complete":
        queryset = complete_purchases(queryset)
    elif data.get("completeness") == "incomplete":
        queryset = incomplete_purchases(queryset)

    if data.get("q"):
        queryset = queryset.filter(
            Q(supplier_name__icontains=data["q"])
            | Q(reference__icontains=data["q"])
            | Q(notes__icontains=data["q"])
        )
    if data.get("category"):
        queryset = queryset.filter(category=data["category"])
    if data.get("review") == "pending":
        queryset = complete_purchases(queryset).filter(reviewed_at__isnull=True)
    elif data.get("review") == "reviewed":
        queryset = queryset.filter(reviewed_at__isnull=False)

    if data.get("payment") == "paid":
        queryset = queryset.filter(paid_on__isnull=False)
    elif data.get("payment") == "unpaid":
        queryset = queryset.filter(paid_on__isnull=True)
    elif data.get("payment") == "overdue":
        queryset = queryset.filter(
            paid_on__isnull=True,
            due_date__lt=timezone.localdate(),
        )

    if data.get("amount_min") is not None:
        queryset = queryset.filter(total_ttc__gte=data["amount_min"])
    if data.get("amount_max") is not None:
        queryset = queryset.filter(total_ttc__lte=data["amount_max"])
    queryset = _apply_exchange_link_filter(queryset, data.get("exchange") or "")
    return form, queryset.distinct()


def filtered_documents(request):
    form = DocumentFilterForm(request.GET)
    if not form.is_valid():
        return form, AccountingDocument.objects.none()

    data = form.cleaned_data
    queryset = _apply_period(AccountingDocument.objects.all(), "document_date", data)
    if data.get("q"):
        queryset = queryset.filter(
            Q(title__icontains=data["q"]) | Q(notes__icontains=data["q"])
        )
    if data.get("kind"):
        queryset = queryset.filter(kind=data["kind"])
    if data.get("review") == "pending":
        queryset = queryset.filter(reviewed_at__isnull=True)
    elif data.get("review") == "reviewed":
        queryset = queryset.filter(reviewed_at__isnull=False)
    if data.get("source") == "exchange":
        queryset = queryset.filter(source_exchange_document__isnull=False)
    elif data.get("source") == "direct":
        queryset = queryset.filter(source_exchange_document__isnull=True)
    queryset = _apply_exchange_link_filter(queryset, data.get("exchange") or "")
    return form, queryset.distinct()


def filtered_exchanges(request, queryset):
    form = ExchangeFilterForm(request.GET)
    if not form.is_valid():
        return form, queryset.none()

    data = form.cleaned_data
    if data.get("date_from"):
        queryset = queryset.filter(last_activity_at__date__gte=data["date_from"])
    if data.get("date_to"):
        queryset = queryset.filter(last_activity_at__date__lte=data["date_to"])

    if data.get("q"):
        queryset = queryset.filter(
            Q(subject__icontains=data["q"])
            | Q(messages__content__icontains=data["q"])
            | Q(invoice__number__icontains=data["q"])
            | Q(invoice__client__full_name__icontains=data["q"])
            | Q(quote__number__icontains=data["q"])
            | Q(quote__client__full_name__icontains=data["q"])
            | Q(supplier_invoice__supplier_name__icontains=data["q"])
            | Q(supplier_invoice__reference__icontains=data["q"])
            | Q(accounting_document__title__icontains=data["q"])
        ).distinct()
    if data.get("status"):
        queryset = queryset.filter(status=data["status"])
    if data.get("kind"):
        queryset = queryset.filter(kind=data["kind"])
    if data.get("priority"):
        queryset = queryset.filter(priority=data["priority"])

    if data.get("documents") == "with":
        if request.accounting_admin:
            queryset = queryset.filter(documents__isnull=False)
        else:
            queryset = queryset.filter(
                documents__visibility=AccountingExchangeDocument.Visibility.SHARED
            )
        queryset = queryset.distinct()
    elif data.get("documents") == "without":
        if request.accounting_admin:
            queryset = queryset.filter(documents__isnull=True)
        else:
            queryset = queryset.exclude(
                documents__visibility=AccountingExchangeDocument.Visibility.SHARED
            )

    context = data.get("context")
    if context == "general":
        queryset = queryset.filter(
            invoice__isnull=True,
            quote__isnull=True,
            supplier_invoice__isnull=True,
            accounting_document__isnull=True,
        )
    elif context == "invoice":
        queryset = queryset.filter(invoice__isnull=False)
    elif context == "quote":
        queryset = queryset.filter(quote__isnull=False)
    elif context == "supplier":
        queryset = queryset.filter(supplier_invoice__isnull=False)
    elif context == "document":
        queryset = queryset.filter(accounting_document__isnull=False)

    return form, queryset.distinct()
