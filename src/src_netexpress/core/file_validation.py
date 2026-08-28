from pathlib import Path
from django.core.exceptions import ValidationError

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def validate_document(file):
    """Bounded PDF/JPEG/PNG uploads. Never trust the browser's MIME type."""
    if file.size > MAX_DOCUMENT_BYTES or not file.size:
        raise ValidationError("La pièce doit contenir entre 1 octet et 10 Mo.")
    position = file.tell()
    try:
        file.seek(0)
        signature = file.read(12)
        extension = Path(file.name).suffix.lower()
        valid = ((extension == ".pdf" and signature.startswith(b"%PDF-")) or
                 (extension == ".png" and signature.startswith(b"\x89PNG\r\n\x1a\n")) or
                 (extension in {".jpg", ".jpeg"} and signature.startswith(b"\xff\xd8\xff")))
        if not valid:
            raise ValidationError("Formats autorisés : PDF, JPEG et PNG. Le contenu doit correspondre au format.")
        if extension != ".pdf":
            from PIL import Image
            file.seek(0)
            try:
                with Image.open(file) as img:
                    if img.width * img.height > 30_000_000:
                        raise ValidationError("Image trop grande (30 mégapixels maximum).")
                    img.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise ValidationError("Image illisible ou trop grande.") from exc
    finally:
        file.seek(position)
