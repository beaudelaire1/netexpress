from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from html import escape

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from weasyprint import HTML

from accounts.models import Profile
from accounting.models import (
    AccountingActivity,
    AccountingDocument,
    InvoiceReview,
    SupplierInvoice,
)
from accounting.services import invoice_fingerprint
from devis.models import Client, Quote, QuoteItem
from factures.models import Invoice, InvoiceItem


TAG = "NETEXPRESS-DEMO-2026"
today = timezone.localdate()
User = get_user_model()

admin = User.objects.filter(username="admin").first()
compta = User.objects.filter(username="compta").first()
client_user = User.objects.filter(username="client").first()


def pdf_bytes(title, body):
    html = f"""
    <!doctype html>
    <html lang="fr">
    <meta charset="utf-8">
    <style>
        body {{ font-family: sans-serif; padding: 35px; }}
        h1 {{ font-size: 22px; }}
        p {{ font-size: 13px; line-height: 1.6; }}
    </style>
    <body>
        <h1>{escape(title)}</h1>
        <p>{escape(body)}</p>
        <p>Document généré uniquement pour les tests locaux NetExpress.</p>
    </body>
    </html>
    """
    return HTML(string=html).write_pdf()


CLIENTS = [
    ("Sophie Bernard", "sophie.bernard@demo.local", "0694 10 20 01", "Cayenne", ""),
    ("Marc Louis", "marc.louis@demo.local", "0694 10 20 02", "Matoury", ""),
    ("Claire Joseph", "claire.joseph@demo.local", "0694 10 20 03", "Rémire-Montjoly", ""),
    ("Daniel Pierre", "daniel.pierre@demo.local", "0694 10 20 04", "Cayenne", ""),
    ("Nathalie André", "nathalie.andre@demo.local", "0694 10 20 05", "Matoury", ""),
    ("Patrick Laurent", "patrick.laurent@demo.local", "0694 10 20 06", "Macouria", ""),
    ("Démo Rémire Habitat", "contact@remire-habitat.demo", "0594 30 40 01", "Rémire-Montjoly", "Rémire Habitat Démo"),
    ("Démo Cayenne Services", "contact@cayenne-services.demo", "0594 30 40 02", "Cayenne", "Cayenne Services Démo"),
    ("Démo Matoury Pro", "contact@matoury-pro.demo", "0594 30 40 03", "Matoury", "Matoury Pro Démo"),
    ("Démo Amazonie Bâtiment", "contact@amazonie-bat.demo", "0594 30 40 04", "Cayenne", "Amazonie Bâtiment Démo"),
    ("Élodie François", "elodie.francois@demo.local", "0694 10 20 11", "Kourou", ""),
    ("Michel Alexandre", "michel.alexandre@demo.local", "0694 10 20 12", "Matoury", ""),
]

SERVICES = [
    ("Entretien mensuel des locaux", Decimal("280.00")),
    ("Nettoyage approfondi", Decimal("450.00")),
    ("Entretien espaces verts", Decimal("320.00")),
    ("Remise en état après travaux", Decimal("780.00")),
    ("Nettoyage de bureaux", Decimal("240.00")),
    ("Intervention ponctuelle", Decimal("195.00")),
]


@transaction.atomic
def seed():

    # ---------------------------------------------------------
    # CLIENTS
    # ---------------------------------------------------------
    clients = []

    for full_name, email, phone, city, company in CLIENTS:
        client = Client.all_objects.filter(email=email).first()

        if client is None:
            client = Client(
                full_name=full_name,
                email=email,
            )

        client.full_name = full_name
        client.phone = phone
        client.city = city
        client.zip_code = "97300"
        client.address_line = f"{10 + len(clients)} rue de Démonstration"
        client.company = company
        client.save()

        clients.append(client)

    # Le compte client voit réellement un client du jeu de données
    if client_user:
        profile, _ = Profile.objects.get_or_create(user=client_user)
        profile.client = clients[0]
        profile.role = Profile.ROLE_CLIENT
        profile.save()

    # ---------------------------------------------------------
    # DEVIS
    # ---------------------------------------------------------
    quotes = []

    quote_statuses = [
        Quote.QuoteStatus.SENT,
        Quote.QuoteStatus.ACCEPTED,
        Quote.QuoteStatus.REJECTED,
        Quote.QuoteStatus.SENT,
    ]

    for i in range(16):
        marker = f"{TAG}-Q{i + 1:02d}"
        issue_date = today - timedelta(days=(15 - i) * 14 + 7)

        quote = Quote.all_objects.filter(notes__contains=marker).first()

        if quote is None:
            quote = Quote(
                client=clients[i % len(clients)],
                issue_date=issue_date,
            )

        quote.client = clients[i % len(clients)]
        quote.issue_date = issue_date
        quote.valid_until = issue_date + timedelta(days=30)
        quote.status = quote_statuses[i % len(quote_statuses)]
        quote.message = "Demande de prestation issue du jeu de démonstration."
        quote.notes = f"Données de démonstration — {marker}"
        quote.save()

        QuoteItem.objects.filter(quote=quote).delete()

        label1, price1 = SERVICES[i % len(SERVICES)]
        label2, price2 = SERVICES[(i + 2) % len(SERVICES)]

        QuoteItem.objects.create(
            quote=quote,
            description=label1,
            quantity=Decimal("1.00"),
            unit_price=price1,
            tax_rate=Decimal("0.00"),
        )

        if i % 3 == 0:
            QuoteItem.objects.create(
                quote=quote,
                description=label2,
                quantity=Decimal("1.00"),
                unit_price=price2,
                tax_rate=Decimal("0.00"),
            )

        quote.compute_totals()
        quotes.append(quote)

    # ---------------------------------------------------------
    # FACTURES CLIENTS
    # ---------------------------------------------------------
    invoice_statuses = [
        Invoice.InvoiceStatus.PAID,
        Invoice.InvoiceStatus.PAID,
        Invoice.InvoiceStatus.SENT,
        Invoice.InvoiceStatus.OVERDUE,
        Invoice.InvoiceStatus.PARTIAL,
        Invoice.InvoiceStatus.SENT,
        Invoice.InvoiceStatus.PAID,
        Invoice.InvoiceStatus.SENT,
        Invoice.InvoiceStatus.OVERDUE,
        Invoice.InvoiceStatus.PAID,
        Invoice.InvoiceStatus.PARTIAL,
    ]

    invoices = []

    for i in range(11):
        marker = f"{TAG}-F{i + 1:02d}"
        quote = quotes[i]
        issue_date = quote.issue_date + timedelta(days=5)

        invoice = Invoice.all_objects.filter(
            notes__contains=marker
        ).first()

        if invoice is None:
            invoice = Invoice(
                quote=quote,
                issue_date=issue_date,
            )

        invoice.quote = quote
        invoice.issue_date = issue_date
        invoice.due_date = issue_date + timedelta(days=30)
        invoice.status = invoice_statuses[i]
        invoice.notes = f"Facture de démonstration — {marker}"
        invoice.payment_terms = "Paiement à 30 jours."
        invoice.save()

        InvoiceItem.objects.filter(invoice=invoice).delete()

        for item in quote.quote_items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
            )

        invoice.compute_totals()

        quote.status = Quote.QuoteStatus.INVOICED
        quote.save(update_fields=["status"])

        invoices.append(invoice)

    # ---------------------------------------------------------
    # UN AVOIR
    # ---------------------------------------------------------
    marker = f"{TAG}-AVOIR-01"

    credit = Invoice.all_objects.filter(
        notes__contains=marker
    ).first()

    if credit is None:
        credit = Invoice(
            quote=quotes[0],
            issue_date=today - timedelta(days=15),
        )

    credit.status = Invoice.InvoiceStatus.AVOIR
    credit.due_date = None
    credit.notes = f"Avoir commercial de démonstration — {marker}"
    credit.save()

    InvoiceItem.objects.filter(invoice=credit).delete()

    InvoiceItem.objects.create(
        invoice=credit,
        description="Avoir sur prestation",
        quantity=Decimal("1.00"),
        unit_price=Decimal("95.00"),
        tax_rate=Decimal("0.00"),
    )

    credit.compute_totals()
    invoices.append(credit)

    # ---------------------------------------------------------
    # CONTRÔLES CABINET
    # environ 1 facture sur 3 déjà contrôlée
    # ---------------------------------------------------------
    for i, invoice in enumerate(invoices):
        if i % 3 == 0:
            InvoiceReview.objects.update_or_create(
                invoice=invoice,
                defaults={
                    "fingerprint": invoice_fingerprint(invoice),
                    "reviewed_by": compta,
                    "reviewed_at": timezone.now(),
                    "note": "Pièce vérifiée dans le jeu de démonstration.",
                },
            )
        else:
            InvoiceReview.objects.filter(invoice=invoice).delete()

    # ---------------------------------------------------------
    # FACTURES FOURNISSEURS
    # ---------------------------------------------------------
    suppliers = [
        ("Fournitures Démo Guyane", "FD-26001", Decimal("189.00"), SupplierInvoice.Category.SUPPLIES),
        ("Matériel Démo Pro", "MD-26018", Decimal("860.00"), SupplierInvoice.Category.EQUIPMENT),
        ("Transport Démo", "TD-26044", Decimal("245.00"), SupplierInvoice.Category.TRANSPORT),
        ("Services Démo", "SD-26071", Decimal("119.90"), SupplierInvoice.Category.SERVICES),
        ("Locaux Démo", "LD-26008", Decimal("640.00"), SupplierInvoice.Category.PREMISES),
        ("Sous-traitant Démo", "ST-26012", Decimal("1250.00"), SupplierInvoice.Category.SUBCONTRACTING),
    ]

    for i, (supplier, reference, amount, category) in enumerate(suppliers):

        marker = f"{TAG}-ACHAT-{i + 1:02d}"

        purchase = SupplierInvoice.objects.filter(
            notes__contains=marker
        ).first()

        issue_date = today - timedelta(days=(i + 1) * 18)

        if purchase is None:
            purchase = SupplierInvoice()

        purchase.supplier_name = supplier
        purchase.reference = reference
        purchase.issue_date = issue_date
        purchase.due_date = issue_date + timedelta(days=30)
        purchase.total_ttc = amount

        # Guyane : données de démonstration sans TVA
        purchase.vat_amount = Decimal("0.00")

        purchase.category = category
        purchase.created_by = admin
        purchase.notes = f"Facture fournisseur de démonstration — {marker}"

        if i in (0, 1, 3):
            purchase.paid_on = issue_date + timedelta(days=12)
        else:
            purchase.paid_on = None

        if not purchase.file:
            content = pdf_bytes(
                f"Facture fournisseur {reference}",
                f"Fournisseur : {supplier} — Montant : {amount} €",
            )
            purchase.file.save(
                f"demo-{reference}.pdf",
                ContentFile(content),
                save=False,
            )
            purchase.file_sha256 = sha256(content).hexdigest()

        if i % 2 == 0:
            purchase.reviewed_at = timezone.now()
            purchase.reviewed_by = compta
            purchase.review_note = "Contrôle cabinet effectué."
        else:
            purchase.reviewed_at = None
            purchase.reviewed_by = None
            purchase.review_note = ""

        purchase.save()

    # ---------------------------------------------------------
    # 2 FACTURES FOURNISSEURS INCOMPLÈTES
    # ---------------------------------------------------------
    for i in range(2):

        marker = f"{TAG}-INCOMPLET-{i + 1}"

        purchase = SupplierInvoice.objects.filter(
            notes__contains=marker
        ).first()

        if purchase is None:
            purchase = SupplierInvoice()

        purchase.supplier_name = ""
        purchase.reference = ""
        purchase.issue_date = None
        purchase.due_date = None
        purchase.total_ttc = None
        purchase.vat_amount = None
        purchase.category = SupplierInvoice.Category.OTHER
        purchase.created_by = admin
        purchase.notes = f"Pièce volontairement incomplète — {marker}"

        if not purchase.file:
            content = pdf_bytes(
                "Facture fournisseur à compléter",
                "Cette pièce sert à tester le parcours des factures incomplètes.",
            )
            purchase.file.save(
                f"demo-incomplete-{i + 1}.pdf",
                ContentFile(content),
                save=False,
            )
            purchase.file_sha256 = sha256(content).hexdigest()

        purchase.reviewed_at = None
        purchase.reviewed_by = None
        purchase.save()

    # ---------------------------------------------------------
    # AUTRES DOCUMENTS COMPTABLES
    # ---------------------------------------------------------
    documents = [
        ("Relevé bancaire — janvier", AccountingDocument.Kind.BANK),
        ("Relevé bancaire — février", AccountingDocument.Kind.BANK),
        ("Attestation d'assurance", AccountingDocument.Kind.INSURANCE),
        ("Contrat fournisseur annuel", AccountingDocument.Kind.CONTRACT),
        ("Document fiscal", AccountingDocument.Kind.TAX),
        ("Document social", AccountingDocument.Kind.SOCIAL),
    ]

    for i, (title, kind) in enumerate(documents):

        marker = f"{TAG}-DOC-{i + 1:02d}"

        document = AccountingDocument.objects.filter(
            notes__contains=marker
        ).first()

        if document is None:
            document = AccountingDocument()

        document.title = title
        document.kind = kind
        document.document_date = today - timedelta(days=i * 28 + 5)
        document.created_by = admin
        document.notes = f"Document comptable de démonstration — {marker}"

        if not document.file:
            content = pdf_bytes(
                title,
                "Document destiné à alimenter le portail comptable de démonstration.",
            )
            document.file.save(
                f"demo-document-{i + 1}.pdf",
                ContentFile(content),
                save=False,
            )
            document.file_sha256 = sha256(content).hexdigest()

        if i in (0, 2, 4):
            document.reviewed_at = timezone.now()
            document.reviewed_by = compta
            document.review_note = "Document vérifié par le cabinet."
        else:
            document.reviewed_at = None
            document.reviewed_by = None
            document.review_note = ""

        document.save()

    # ---------------------------------------------------------
    # JOURNAL D'ACTIVITÉ
    # ---------------------------------------------------------
    AccountingActivity.objects.filter(
        target__startswith=TAG
    ).delete()

    AccountingActivity.objects.create(
        actor=admin,
        action="Jeu de démonstration créé",
        target=f"{TAG} · clients et devis",
    )

    AccountingActivity.objects.create(
        actor=admin,
        action="Pièces fournisseurs déposées",
        target=f"{TAG} · achats",
    )

    AccountingActivity.objects.create(
        actor=compta,
        action="Contrôles comptables effectués",
        target=f"{TAG} · contrôle cabinet",
    )

    print()
    print("======================================")
    print(" NETEXPRESS — BASE DEMO ALIMENTÉE")
    print("======================================")
    print("Clients             :", Client.all_objects.filter(email__contains="demo").count())
    print("Devis DEMO          :", Quote.all_objects.filter(notes__contains=TAG).count())
    print("Factures clients    :", Invoice.all_objects.filter(notes__contains=TAG).count())
    print("Factures fournisseurs:", SupplierInvoice.objects.filter(notes__contains=TAG).count())
    print("Autres documents    :", AccountingDocument.objects.filter(notes__contains=TAG).count())
    print("======================================")


seed()