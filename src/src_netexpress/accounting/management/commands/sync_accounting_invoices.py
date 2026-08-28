"""Recover legacy invoice originals without duplicating or reissuing invoices."""
import hashlib
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse

from accounting.models import AccountingActivity
from factures.models import Invoice


ISSUED_STATUSES = {
    Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.PAID,
    Invoice.InvoiceStatus.PARTIAL, Invoice.InvoiceStatus.OVERDUE,
    Invoice.InvoiceStatus.REFACTURATION, Invoice.InvoiceStatus.AVOIR,
}


def invoice_state(invoice):
    return {field.attname: getattr(invoice, field.attname)
            for field in invoice._meta.concrete_fields if field.name != "pdf"} | {"pdf": invoice.pdf.name}


def checked_path(storage, name):
    """Reject unsafe historical names, including symlinks outside local storage."""
    parts = PurePosixPath(name)
    if (not name or parts.is_absolute() or ".." in parts.parts or
            "\\" in name or ":" in name or parts.suffix.lower() != ".pdf"):
        raise ValueError("Chemin PDF historique invalide.")
    if isinstance(storage, FileSystemStorage):
        root = Path(storage.location).resolve()
        path = Path(storage.path(name)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Le chemin sort du stockage autorisé.")
        return path
    return None


def pdf_digest(storage, name):
    checked_path(storage, name)
    digest = hashlib.sha256()
    with storage.open(name, "rb") as file:
        if file.read(5) != b"%PDF-":
            raise ValueError("Le fichier enregistré n’est pas un PDF identifiable.")
        file.seek(0)
        for chunk in file.chunks():
            digest.update(chunk)
    return digest.hexdigest()


def copy_verified(source, target, name, expected_digest):
    """Publish a complete, verified file atomically, without replacing a destination."""
    destination = checked_path(target, name)
    if destination is None:
        raise ValueError("La destination privée doit être un stockage local.")
    if destination.exists():
        if pdf_digest(target, name) != expected_digest:
            raise ValueError("Un PDF privé différent existe déjà ; aucun écrasement autorisé.")
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix=".accounting-", delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            checked_path(source, name)
            with source.open(name, "rb") as original:
                for chunk in original.chunks():
                    output.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != expected_digest:
                raise ValueError("Le PDF source a changé depuis la vérification ; relancez la simulation.")
            output.flush()
            os.fsync(output.fileno())
        try:
            # Same-filesystem hard link: atomic publication; unlike replace(), never overwrites.
            os.link(temporary, destination)
        except FileExistsError:
            if pdf_digest(target, name) != expected_digest:
                raise ValueError("Un PDF privé différent a été créé pendant la reprise.")
            return False
        if pdf_digest(target, name) != expected_digest:
            raise ValueError("La vérification du PDF copié a échoué.")
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass
class Recovery:
    invoice: Invoice
    state: dict
    digest: str | None
    copy_pdf: bool


class Command(BaseCommand):
    help = "Reprend les anciennes factures clients et leurs PDF dans le portail comptable (simulation par défaut)."
    requires_migrations_checks = True

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--apply", action="store_true", help="Appliquer la reprise après sauvegarde.")
        mode.add_argument("--dry-run", action="store_true", help="Vérifier sans écrire (comportement par défaut).")
        parser.add_argument("--year", type=int, help="Limiter à l’année de la date de facture.")
        parser.add_argument("--source", choices=["local", "cloudinary"], default="local",
                            help="Ancien stockage des PDF (local par défaut).")
        parser.add_argument("--source-dir", help="Racine de l’ancien stockage local ; MEDIA_ROOT par défaut.")

    def handle(self, *args, **options):
        year = options["year"]
        if year is not None and not 1 <= year <= 9998:
            raise CommandError("--year doit être une année comprise entre 1 et 9998.")
        if options["source_dir"] and options["source"] != "local":
            raise CommandError("--source-dir est réservé à --source local.")
        target = Invoice._meta.get_field("pdf").storage
        if options["source"] == "local":
            source = FileSystemStorage(location=options["source_dir"] or settings.MEDIA_ROOT)
            source_root, target_root = Path(source.location).resolve(), Path(target.location).resolve()
            if source_root.is_relative_to(target_root) or target_root.is_relative_to(source_root):
                raise CommandError("Les stockages source et privé doivent être séparés, sans imbrication.")
        else:
            from cloudinary_storage.storage import MediaCloudinaryStorage
            source = MediaCloudinaryStorage()

        selection = Invoice.all_objects.all()
        if year is not None:
            selection = selection.filter(issue_date__range=(date(year, 1, 1), date(year, 12, 31)))
        eligible = Q(issued_at__isnull=False) | Q(status__in=ISSUED_STATUSES)
        excluded = selection.exclude(eligible).count()
        recoveries, errors = [], []
        self.stdout.write("APPLICATION" if options["apply"] else "SIMULATION — aucune écriture")
        self.stdout.write(f"{excluded} brouillon(s), devis ou statut(s) non émis exclus.")
        for invoice in selection.filter(eligible).order_by("pk").iterator(chunk_size=200):
            try:
                if not invoice.number or (not invoice.issued_at and not invoice.created_at):
                    raise ValueError("Numéro ou horodatage historique manquant.")
                name = invoice.pdf.name
                fingerprint, copy_pdf = None, False
                actions = []
                if name:
                    checked_path(source, name)
                    checked_path(target, name)
                    private_exists, source_exists = target.exists(name), source.exists(name)
                    if not private_exists and not source_exists:
                        raise ValueError(f"PDF original introuvable : {name}")
                    if private_exists:
                        fingerprint = pdf_digest(target, name)
                        if source_exists and pdf_digest(source, name) != fingerprint:
                            raise ValueError(f"Conflit entre le PDF privé et l’original : {name}")
                        actions.append("PDF privé vérifié")
                    else:
                        fingerprint = pdf_digest(source, name)
                        copy_pdf = True
                        actions.append("PDF original à copier")
                else:
                    actions.append("aucun PDF enregistré, génération à la demande conservée")
                if not invoice.issued_at:
                    actions.append("marqueur d’émission historique à reprendre depuis created_at")
                if invoice.status == Invoice.InvoiceStatus.AVOIR and not invoice.is_credit_note:
                    actions.append("nature avoir à rétablir")
                recoveries.append(Recovery(invoice, invoice_state(invoice), fingerprint, copy_pdf))
                self.stdout.write(f"{invoice.number} · {invoice.issue_date} : {', '.join(actions)}")
            except (OSError, ValueError) as exc:
                errors.append(f"{invoice.number or invoice.pk} : {exc}")

        for error in errors:
            self.stderr.write(error)
        if errors:
            raise CommandError(f"{len(errors)} anomalie(s). Aucune écriture effectuée ; corrigez les sources puis relancez.")

        copies = sum(item.copy_pdf for item in recoveries)
        markers = sum(not item.invoice.issued_at for item in recoveries)
        credits = sum(item.invoice.status == Invoice.InvoiceStatus.AVOIR and not item.invoice.is_credit_note
                      for item in recoveries)
        self.stdout.write(f"{len(recoveries)} facture(s) émise(s), {copies} PDF à récupérer, "
                          f"{markers} marqueur(s) d’émission à reprendre, {credits} avoir(s) à rétablir.")
        if options["apply"]:
            for item in recoveries:
                try:
                    self.apply_recovery(item, source, target)
                except (OSError, ValueError, Invoice.DoesNotExist) as exc:
                    raise CommandError(f"Reprise arrêtée sur {item.invoice.number} : {exc}. "
                                       "Les factures précédentes restent traitées ; une relance ne les duplique pas.") from exc
            self.stdout.write(self.style.SUCCESS("Reprise terminée. Aucun numéro, montant, statut ou date de facture modifié."))
        else:
            self.stdout.write("Après sauvegarde, relancez avec --apply pour effectuer la reprise.")
        if recoveries:
            dates = [item.invoice.issue_date for item in recoveries]
            period = urlencode({"date_from": min(dates).isoformat(), "date_to": max(dates).isoformat()})
            self.stdout.write(f"Factures dans le portail : {reverse('accounting:sales')}?{period}")
            self.stdout.write("Le portail affiche l’année courante par défaut : utilisez ce lien ou adaptez les dates.")
        self.stdout.write("Les originaux source sont conservés. Aucun email envoyé, aucune facture créée ni déclarée comptabilisée.")
        self.stdout.write("Si la source est publique, retirez-en les copies uniquement après sauvegarde et validation du stockage privé.")

    @transaction.atomic
    def apply_recovery(self, recovery, source, target):
        invoice = Invoice.all_objects.select_for_update().get(pk=recovery.invoice.pk)
        if invoice_state(invoice) != recovery.state:
            raise ValueError("La facture a changé depuis la simulation interne ; relancez la commande")
        copied = False
        if recovery.digest:
            # Recheck even an existing destination in case it disappeared after preflight.
            copied = copy_verified(source, target, invoice.pdf.name, recovery.digest)
        updates = {}
        if not invoice.issued_at:
            # Same historical convention as factures.0009; never invent a new issue date.
            updates["issued_at"] = invoice.created_at
        if invoice.status == Invoice.InvoiceStatus.AVOIR and not invoice.is_credit_note:
            updates["is_credit_note"] = True
        if updates:
            Invoice.all_objects.filter(pk=invoice.pk).update(**updates)
        if updates or copied:
            details = ["PDF original récupéré"] if copied else []
            if "issued_at" in updates:
                details.append("émission historique reprise depuis created_at")
            if "is_credit_note" in updates:
                details.append("nature avoir rétablie")
            AccountingActivity.objects.create(action="Reprise facture client",
                                              target=f"{invoice.number} · {', '.join(details)}"[:200])
