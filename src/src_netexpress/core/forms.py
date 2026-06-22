"""Outils de formulaire transverses (anti-spam).

``HoneypotMixin`` ajoute un champ piège invisible (``website``) aux
formulaires publics.  Les humains ne le voient pas (masqué en CSS, retiré du
flux de tabulation et de l'arbre d'accessibilité) ; les robots de spam le
remplissent automatiquement.  Si le champ est rempli, la validation échoue
silencieusement côté serveur.
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

# Extensions d'image autorisées et taille maximale par fichier (5 Mo).
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "heic"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_uploaded_images(files) -> None:
    """Valide une liste de fichiers image (extension + taille).

    Lève ``forms.ValidationError`` au premier fichier non conforme.
    """
    for f in files:
        if not f:
            continue
        name = getattr(f, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise forms.ValidationError(
                _("Format de fichier non autorisé : %(name)s. Formats acceptés : %(exts)s."),
                params={"name": name, "exts": ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))},
            )
        size = getattr(f, "size", 0) or 0
        if size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                _("Le fichier %(name)s dépasse la taille maximale de 5 Mo."),
                params={"name": name},
            )


class HoneypotMixin(forms.Form):
    """Ajoute un champ piège anti-spam à un formulaire.

    À placer en première classe de base (avant ``forms.Form`` /
    ``forms.ModelForm``) pour que le champ et la validation soient pris en
    compte.
    """

    # Le nom ``website`` est volontairement plausible pour attirer les robots.
    website = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                # Masquage accessible : hors écran, non focusable, ignoré par
                # les lecteurs d'écran.
                "class": "hp-field",
                "style": "position:absolute;left:-9999px;top:-9999px;height:0;width:0;opacity:0;",
                "autocomplete": "off",
                "tabindex": "-1",
                "aria-hidden": "true",
            }
        ),
    )

    def clean_website(self) -> str:
        value = self.cleaned_data.get("website", "")
        if value:
            # Détecté comme spam : on rejette sans révéler le motif.
            raise forms.ValidationError(_("Une erreur est survenue. Veuillez réessayer."))
        return value
