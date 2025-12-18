from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("compose/", views.compose, name="compose"),
    path("", views.MessageListView.as_view(), name="list"),
    path("<int:pk>/", views.MessageDetailView.as_view(), name="detail"),
]
