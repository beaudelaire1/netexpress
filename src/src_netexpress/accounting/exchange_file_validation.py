from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.core.exceptions import ValidationError

MAX_EXCHANGE_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024

EXCHANGE_DOCUMENT_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def exchange_document_mime_type(filename: str) -> str:
    return EXCHANGE_DOCUMENT_MIME_TYPES.get(
        Path(filename or "").suffix.lower(),
        "application/octet-stream",
    )


def _validate_office_archive(file, extension: str) -> None:
    try:
        file.seek(0)
        with ZipFile(file) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ValidationError(
                    "Archive Office trop volumineuse après décompression."
                )
            if "[Content_Types].xml" not in names:
                raise ValidationError("Document Office invalide.")
            required_prefix = "xl/" if extension == ".xlsx" else "word/"
            if not any(name.startswith(required_prefix) for name in names):
                raise ValidationError("Le contenu ne correspond pas au format annoncé.")
    except (BadZipFile, OSError, ValueError) as exc:
        raise ValidationError("Document Office illisible ou invalide.") from exc


def validate_exchange_document(file) -> None:
    """Validate accountant/NetExpress exchange uploads without trusting MIME headers."""
    size = getattr(file, "size", 0) or 0
    if size < 1 or size > MAX_EXCHANGE_DOCUMENT_BYTES:
        raise ValidationError("Le document doit contenir entre 1 octet et 10 Mo.")

    extension = Path(getattr(file, "name", "")).suffix.lower()
    if extension not in EXCHANGE_DOCUMENT_MIME_TYPES:
        raise ValidationError(
            "Formats autorisés : PDF, JPEG, PNG, CSV, XLSX et DOCX."
        )

    position = file.tell()
    try:
        file.seek(0)
        signature = file.read(16)

        if extension == ".pdf" and not signature.startswith(b"%PDF-"):
            raise ValidationError("Le contenu ne correspond pas à un fichier PDF.")
        if extension == ".png" and not signature.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValidationError("Le contenu ne correspond pas à une image PNG.")
        if extension in {".jpg", ".jpeg"} and not signature.startswith(b"\xff\xd8\xff"):
            raise ValidationError("Le contenu ne correspond pas à une image JPEG.")

        if extension in {".png", ".jpg", ".jpeg"}:
            from PIL import Image

            file.seek(0)
            try:
                with Image.open(file) as image:
                    if image.width * image.height > 30_000_000:
                        raise ValidationError("Image trop grande (30 mégapixels maximum).")
                    image.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise ValidationError("Image illisible ou trop grande.") from exc

        if extension in {".xlsx", ".docx"}:
            _validate_office_archive(file, extension)

        if extension == ".csv":
            file.seek(0)
            sample = file.read(min(size, 64 * 1024))
            if b"\x00" in sample:
                raise ValidationError("Fichier CSV invalide.")
            try:
                sample.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValidationError("Le CSV doit être encodé en UTF-8.") from exc
    finally:
        file.seek(position)
