"""Contrat de déconnexion : POST obligatoire, et aucun gabarit ne doit y accéder en GET.

Un lien ``<a href>`` vers la déconnexion a atteint la production et renvoyait 405 :
``custom_logout`` est décorée ``require_http_methods(["POST"])``. Le rendu de la
page n'échouait pas — seul le clic échouait — donc aucun test existant ne le
voyait. Ces cas verrouillent les deux moitiés du contrat.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import resolve, reverse

User = get_user_model()


@pytest.fixture
def connecte(db) -> Client:
    # force_login et non login : django-axes impose un `request` à authenticate(),
    # que le client de test ne transmet pas. Ce qu'on éprouve ici est la
    # déconnexion, pas le parcours d'authentification.
    utilisateur = User.objects.create_user(username="marie", password="mot-de-passe-solide-1")
    client = Client()
    client.force_login(utilisateur)
    return client


@pytest.mark.django_db
def test_la_deconnexion_est_servie_par_la_vue_du_projet():
    """accounts.urls est inclus avant django.contrib.auth.urls, sur le même préfixe.

    Les deux déclarent une route ``logout``. Si l'ordre d'inclusion changeait, la
    LogoutView native prendrait la main et le message d'au revoir disparaîtrait
    sans que rien n'échoue visiblement.
    """
    correspondance = resolve(reverse("accounts:logout"))
    assert correspondance.func.__module__ == "accounts.views"
    assert correspondance.func.__name__ == "custom_logout"


@pytest.mark.django_db
def test_le_get_est_refuse(connecte: Client):
    """C'est la protection recherchée : une image distante ne doit pas déconnecter."""
    reponse = connecte.get(reverse("accounts:logout"))

    assert reponse.status_code == 405
    assert "_auth_user_id" in connecte.session


@pytest.mark.django_db
def test_le_post_deconnecte(connecte: Client):
    reponse = connecte.post(reverse("accounts:logout"))

    assert reponse.status_code == 302
    assert "_auth_user_id" not in connecte.session


def test_aucun_gabarit_ne_pointe_vers_la_deconnexion_par_un_lien():
    """Interdit la régression exacte : ``<a href="{% url ... logout %}">``.

    Balayer les gabarits plutôt que tester chaque page évite qu'un nouvel écran
    réintroduise le lien sans être couvert.
    """
    lien_de_deconnexion = re.compile(
        r"<a\b[^>]*href=\"\{%\s*url\s*'[^']*logout'[^>]*>", re.IGNORECASE
    )

    fautifs = []
    for racine in [Path(settings.BASE_DIR)]:
        for gabarit in racine.rglob("*.html"):
            if any(part in {".venv", "node_modules", "staticfiles"} for part in gabarit.parts):
                continue
            if lien_de_deconnexion.search(gabarit.read_text(encoding="utf-8", errors="ignore")):
                fautifs.append(str(gabarit.relative_to(racine)))

    assert not fautifs, (
        "La déconnexion doit passer par un formulaire POST, jamais par un lien. "
        f"Gabarits fautifs : {fautifs}"
    )
