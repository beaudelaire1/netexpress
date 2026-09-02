"""Toute référence {% static 'chemin' %} doit désigner un fichier réel.

En développement, un fichier statique absent donne une image cassée — on le
remarque, ou pas. En production, `CompressedManifestStaticFilesStorage` lève une
ValueError au rendu : la page entière retourne 500.

La fiche service référençait cinq images inexistantes, héritées d'un jeu de
visuels retiré depuis. Le défaut est resté invisible tant qu'aucune prestation
n'existait en base ; il est apparu à la première fiche consultée en production.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders

REPERTOIRES_IGNORES = {".venv", "node_modules", "staticfiles", "__pycache__"}

# {% static 'chemin' %} ou {% static "chemin" %}, littéral uniquement : les
# chemins construits depuis une variable ne sont pas vérifiables ici.
REFERENCE_STATIQUE = re.compile(r"\{%\s*static\s+[\"']([^\"']+)[\"']")


def test_toutes_les_references_statiques_existent():
    racine = Path(settings.BASE_DIR)
    manquants: dict[str, list[str]] = {}

    for gabarit in racine.rglob("*.html"):
        if any(part in REPERTOIRES_IGNORES for part in gabarit.parts):
            continue

        contenu = gabarit.read_text(encoding="utf-8", errors="ignore")
        for chemin in set(REFERENCE_STATIQUE.findall(contenu)):
            if finders.find(chemin) is None:
                manquants.setdefault(chemin, []).append(
                    str(gabarit.relative_to(racine))
                )

    assert not manquants, (
        "Ces fichiers statiques sont référencés mais absents. En production, "
        "le stockage à manifeste fera échouer le rendu avec une 500 :\n"
        + "\n".join(
            f"  {chemin} — référencé par {', '.join(sorted(gabarits))}"
            for chemin, gabarits in sorted(manquants.items())
        )
    )
