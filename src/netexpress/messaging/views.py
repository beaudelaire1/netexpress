"""Vues de l'application ``messaging``.

Ces vues fournissent une interface simple pour lister les messages
envoyés et consulter le détail d'un message.  Elles peuvent être
étendues pour permettre la création de nouveaux messages ou la
réponse directe depuis l'interface.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import EmailMessage


@login_required
def message_list(request):
    """Afficher la liste des messages envoyés.

    Les messages sont triés par ordre antichronologique.  Seuls les
    utilisateurs connectés peuvent accéder à cette page.

    Utilise le nom de contexte ``email_messages`` pour éviter de masquer
    la variable ``messages`` du framework de messagerie de Django.
    """
    email_messages = EmailMessage.objects.all().order_by("-created_at")
    return render(request, "messaging/message_list.html", {"email_messages": email_messages})


@login_required
def message_detail(request, pk: int):
    """Afficher le détail d'un message spécifique.

    Les utilisateurs peuvent consulter le contenu, l'état et les
    éventuelles pièces jointes du message.  Un bouton pourrait être
    ajouté pour renvoyer le message en cas d'échec.
    """
    msg = get_object_or_404(EmailMessage, pk=pk)
    return render(request, "messaging/message_detail.html", {"message": msg})