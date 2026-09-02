"""Un commentaire Django multiligne s'affiche aux visiteurs.

L'analyseur de gabarits reconnaît ``{# … #}`` avec une expression régulière sans
l'option DOTALL : dès que le commentaire franchit une fin de ligne, il n'est plus
reconnu comme tel et part tel quel dans le HTML. Rien n'échoue, la page se rend
normalement — le texte apparaît simplement au milieu du contenu.

Trois gabarits en production étaient concernés. Ce balayage empêche la reprise.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.template import Context, Template

REPERTOIRES_IGNORES = {".venv", "node_modules", "staticfiles", "__pycache__"}

# Un {# … #} contenant au moins un saut de ligne avant sa fermeture.
COMMENTAIRE_MULTILIGNE = re.compile(r"\{#(?:(?!#\}).)*\n(?:(?!#\}).)*#\}", re.S)


def test_django_rend_bien_les_commentaires_multilignes():
    """Fige le comportement qui justifie le balayage ci-dessous.

    Si une version de Django venait à accepter le multiligne, ce cas échouerait
    et la règle pourrait être assouplie en connaissance de cause.
    """
    rendu = Template("debut{# une ligne\net une autre #}fin").render(Context({}))

    assert "{#" in rendu, "Django ne rend plus les commentaires multilignes : règle à revoir."


def test_aucun_gabarit_ne_contient_de_commentaire_multiligne():
    racine = Path(settings.BASE_DIR)
    fautifs = []

    for gabarit in racine.rglob("*.html"):
        if any(part in REPERTOIRES_IGNORES for part in gabarit.parts):
            continue
        contenu = gabarit.read_text(encoding="utf-8", errors="ignore")
        for correspondance in COMMENTAIRE_MULTILIGNE.finditer(contenu):
            ligne = contenu[: correspondance.start()].count("\n") + 1
            fautifs.append(f"{gabarit.relative_to(racine)}:{ligne}")

    assert not fautifs, (
        "Ces commentaires seront affichés aux visiteurs. "
        "Utiliser {% comment %} … {% endcomment %} sur plusieurs lignes. "
        f"Fautifs : {fautifs}"
    )
