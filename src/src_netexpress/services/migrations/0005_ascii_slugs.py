"""Réécrit en ASCII les slugs accentués déjà enregistrés.

Les modèles généraient leurs slugs avec ``allow_unicode=True`` alors que la route
de détail utilise le convertisseur ``<slug:…>`` de Django, limité à
``[-a-zA-Z0-9_]+``. Une prestation nommée « Débroussaillage de terrain » recevait
donc un slug injoignable, et le ``{% url %}`` de la page de liste levait
NoReverseMatch : tout le catalogue répondait 500.

Les modèles sont corrigés, mais ``save()`` ne régénère un slug que si le titre
change. Cette migration répare l'existant.
"""

from __future__ import annotations

from django.db import migrations
from django.utils.text import slugify


def _ascii(valeur: str) -> str:
    return slugify(valeur, allow_unicode=False)


def _reecrire(modele, champ_source: str) -> None:
    """Réécrit les slugs non conformes en préservant l'unicité."""
    pris = set(modele.objects.values_list("slug", flat=True))

    for objet in modele.objects.all():
        if objet.slug == _ascii(objet.slug or ""):
            continue  # déjà conforme

        base = _ascii(getattr(objet, champ_source)) or _ascii(objet.slug) or "element"
        pris.discard(objet.slug)

        candidat, compteur = base, 1
        while candidat in pris:
            candidat = f"{base}-{compteur}"
            compteur += 1

        objet.slug = candidat
        pris.add(candidat)
        # update() court-circuite save() : inutile ici, et save() ne
        # régénérerait pas le slug puisque le titre n'a pas changé.
        modele.objects.filter(pk=objet.pk).update(slug=candidat)


def vers_ascii(apps, schema_editor):
    _reecrire(apps.get_model("services", "Category"), "name")
    _reecrire(apps.get_model("services", "Service"), "title")


def retour(apps, schema_editor):
    """Irréversible sans perte : les accents d'origine ne sont pas conservés.

    Laisser les slugs ASCII en place est sans danger — ils restent valides pour
    les deux versions du code.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0004_service_image_alt"),
    ]

    operations = [
        migrations.RunPython(vers_ascii, retour),
    ]
