"""Service d'import de clients depuis un fichier Excel (.xlsx / .xlsm).

Colonnes attendues (en-tête ligne 1, insensible à la casse) :
    nom | email | telephone | adresse | ville | code_postal | societe

Le service valide chaque ligne et retourne un rapport détaillé.
"""

import re
from dataclasses import dataclass, field
from typing import IO, List

from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from devis.models import Client


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    total: int = 0


ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}

IMPORT_COLUMN_GUIDE = [
    {"label": "Nom", "required": True, "aliases": ["nom", "name", "full_name", "client"]},
    {"label": "Email", "required": True, "aliases": ["email", "e-mail", "mail", "courriel"]},
    {"label": "Téléphone", "required": False, "aliases": ["telephone", "téléphone", "phone", "tel", "mobile", "portable"]},
    {"label": "Adresse", "required": False, "aliases": ["adresse", "address", "address_line", "adresse_1"]},
    {"label": "Ville", "required": False, "aliases": ["ville", "city", "commune"]},
    {"label": "Code postal", "required": False, "aliases": ["code_postal", "code postal", "cp", "zip_code", "zip", "postal_code"]},
    {"label": "Société", "required": False, "aliases": ["societe", "société", "company", "entreprise", "raison_sociale", "company_name"]},
]

TEMPLATE_HEADERS = [entry["label"] for entry in IMPORT_COLUMN_GUIDE]
TEMPLATE_SAMPLE_ROW = [
    "Maison Durand",
    "contact@maison-durand.fr",
    "0594 12 34 56",
    "12 rue des Flamboyants",
    "Matoury",
    "97351",
    "Maison Durand",
]


# Mapping colonnes Excel → champ modèle
COLUMN_MAP = {
    "nom": "full_name",
    "name": "full_name",
    "full_name": "full_name",
    "client": "full_name",
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "courriel": "email",
    "telephone": "phone",
    "téléphone": "phone",
    "phone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "portable": "phone",
    "adresse": "address_line",
    "address": "address_line",
    "address_line": "address_line",
    "adresse_1": "address_line",
    "ville": "city",
    "city": "city",
    "commune": "city",
    "code_postal": "zip_code",
    "cp": "zip_code",
    "zip_code": "zip_code",
    "zip": "zip_code",
    "postal_code": "zip_code",
    "societe": "company",
    "société": "company",
    "company": "company",
    "entreprise": "company",
    "raison_sociale": "company",
    "company_name": "company",
}

REQUIRED_FIELDS = {"full_name", "email"}

PHONE_RE = re.compile(r'^[\d\s\+\-\.\(\)]{6,20}$')


def _normalize_header(header: str) -> str:
    """Normalise un en-tête de colonne."""
    return header.strip().lower().replace("\xa0", " ").replace(" ", "_").replace("-", "_")


def _cell_to_string(value) -> str:
    """Convertit proprement une cellule Excel en texte exploitable."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _validate_row(row_data: dict, row_num: int) -> List[str]:
    """Valide une ligne et retourne les erreurs."""
    errors = []
    if not row_data.get("full_name", "").strip():
        errors.append(f"Ligne {row_num}: nom manquant")

    email = row_data.get("email", "").strip()
    if not email:
        errors.append(f"Ligne {row_num}: email manquant")
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors.append(f"Ligne {row_num}: email invalide '{email}'")

    phone = row_data.get("phone", "").strip()
    if phone and not PHONE_RE.match(phone):
        errors.append(f"Ligne {row_num}: téléphone invalide '{phone}'")

    return errors


def import_clients_from_excel(file_obj: IO, *, update_existing: bool = False) -> ImportResult:
    """Importe des clients depuis un fichier Excel.

    Args:
        file_obj: Fichier Excel ouvert (BytesIO ou UploadedFile).
        update_existing: Si True, met à jour les clients existants (par email).

    Returns:
        ImportResult avec le détail de l'import.
    """
    try:
        import openpyxl
    except ImportError:
        return ImportResult(errors=["openpyxl n'est pas installé. Ajoutez-le aux requirements."])

    result = ImportResult()

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as e:
        return ImportResult(errors=[f"Impossible de lire le fichier Excel: {e}"])

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return ImportResult(errors=["Le fichier est vide."])

    # Mapper les en-têtes
    raw_headers = [str(h or "").strip() for h in rows[0]]
    field_map = {}
    for idx, header in enumerate(raw_headers):
        normalized = _normalize_header(header)
        if normalized in COLUMN_MAP:
            field_map[idx] = COLUMN_MAP[normalized]

    # Vérifier colonnes requises
    mapped_fields = set(field_map.values())
    missing = REQUIRED_FIELDS - mapped_fields
    if missing:
        return ImportResult(errors=[f"Colonnes requises manquantes: {', '.join(missing)}. "
                                    f"Colonnes trouvées: {', '.join(raw_headers)}"])

    seen_emails = set()

    # Parser les lignes
    for row_idx, row in enumerate(rows[1:], start=2):
        row_data = {}
        for col_idx, field_name in field_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            row_data[field_name] = _cell_to_string(val)

        if not any(row_data.values()):
            continue

        result.total += 1

        # Validation
        row_errors = _validate_row(row_data, row_idx)
        if row_errors:
            result.errors.extend(row_errors)
            result.skipped += 1
            continue

        email = row_data["email"].lower().strip()
        if email in seen_emails:
            result.errors.append(f"Ligne {row_idx}: email dupliqué dans le fichier '{email}'")
            result.skipped += 1
            continue
        seen_emails.add(email)

        try:
            existing = Client.all_objects.filter(email__iexact=email).first()
            if existing:
                if update_existing:
                    for fld, val in row_data.items():
                        if fld != "email" and val:
                            setattr(existing, fld, val)
                    existing.deleted_at = None  # Restore si soft-deleted
                    existing.save()
                    result.updated += 1
                else:
                    result.skipped += 1
            else:
                Client.objects.create(
                    full_name=row_data.get("full_name", ""),
                    email=email,
                    phone=row_data.get("phone", ""),
                    address_line=row_data.get("address_line", ""),
                    city=row_data.get("city", ""),
                    zip_code=row_data.get("zip_code", ""),
                    company=row_data.get("company", ""),
                )
                result.created += 1
        except Exception as e:
            result.errors.append(f"Ligne {row_idx}: erreur de création — {e}")
            result.skipped += 1

    wb.close()
    return result
