"""Un fichier statique introuvable ne doit pas rendre une page inaccessible.

Jazzmin écrit ``{% static 'vendor/bootswatch' %}`` — un répertoire, qui ne peut
par nature figurer dans le manifeste. En mode strict, cette seule ligne levait
une ValueError et renvoyait 500 sur toute l'administration, alors que le reste
de la page était parfaitement rendable.

Le contrôle strict n'est pas abandonné : il est déplacé dans
``tests/test_static_references``, qui refuse toute référence sans fichier dans
les gabarits du projet. On garde donc l'exigence là où l'on écrit le code, sans
qu'une dépendance puisse couper l'accès à l'administration.
"""

from __future__ import annotations

import pytest

from core.storage import ToleranteStaticFilesStorage


def test_le_stockage_n_est_pas_strict():
    assert ToleranteStaticFilesStorage.manifest_strict is False


def test_un_chemin_absent_du_manifeste_ne_leve_pas():
    stockage = ToleranteStaticFilesStorage()
    # Le manifeste n'est pas construit dans les tests : toute entrée est donc
    # absente, ce qui reproduit exactement le cas de 'vendor/bootswatch'.
    url = stockage.url("vendor/bootswatch")

    assert url, "une URL doit être produite plutôt qu'une exception"
    assert "vendor/bootswatch" in url


def test_le_mode_strict_aurait_leve():
    """Fige la cause : sans cette sous-classe, le comportement était fatal."""
    from whitenoise.storage import CompressedManifestStaticFilesStorage

    strict = CompressedManifestStaticFilesStorage()

    with pytest.raises(ValueError):
        strict.url("vendor/bootswatch")
