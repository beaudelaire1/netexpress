"""Routes pour l'application ``messaging``.

Ces URL permettent d'accéder à la liste des messages et au détail
d'un message.  Elles sont préfixées par ``messages/`` dans
``netexpress/netexpress/urls.py``.
"""

from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.message_list, name="list"),
    path("<int:pk>/", views.message_detail, name="detail"),
]