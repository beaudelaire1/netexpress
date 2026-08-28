"""Validation stricte des valeurs sensibles utilisées au démarrage de production."""

from __future__ import annotations

import re

from django.core.exceptions import ImproperlyConfigured


_BIC_PATTERN = re.compile(r"^[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$")


def normalize_iban(value: str) -> str:
    """Valide la structure et la clé de contrôle d'un IBAN puis le formate."""
    compact = "".join((value or "").split()).upper()
    if not 15 <= len(compact) <= 34:
        raise ImproperlyConfigured("BANK_ACCOUNT_NUMBER doit contenir un IBAN valide.")
    if not compact[:2].isalpha() or not compact[2:4].isdigit() or not compact.isalnum():
        raise ImproperlyConfigured("BANK_ACCOUNT_NUMBER doit contenir un IBAN valide.")

    rearranged = compact[4:] + compact[:4]
    remainder = 0
    for char in rearranged:
        digits = str(ord(char) - 55) if char.isalpha() else char
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    if remainder != 1:
        raise ImproperlyConfigured("BANK_ACCOUNT_NUMBER a une clé IBAN invalide.")

    return " ".join(compact[index:index + 4] for index in range(0, len(compact), 4))


def normalize_bic(value: str) -> str:
    """Normalise un BIC optionnel et rejette les formats incohérents."""
    compact = "".join((value or "").split()).upper()
    if not compact:
        return ""
    if not _BIC_PATTERN.fullmatch(compact):
        raise ImproperlyConfigured("COMPANY_BIC doit contenir un BIC de 8 ou 11 caractères valide.")
    return compact
