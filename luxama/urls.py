from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),       # Page d'accueil
    path('contact/', views.contact, name='contact'),  # Page de contact
    path('submit_contact/', views.submit_contact, name='submit_contact'),
    path('contact/', views.handle_contact_form, name='contact'),
    path('forms/', views.handle_contact_form, name='forms'),
    path('nettoyage/', views.nettoyage, name='nettoyage'),
    path('peinture/', views.peinture, name='peinture'),
    path('renovation/', views.renovation, name='renovation'),
    path('bricolage/', views.bricolage, name='bricolage'),
    path('creer_devis/', views.creer_devis, name='creer_devis'),
    path('devis/<int:devis_id>/', views.detail_devis, name='detail_devis'),
    path('devis/', views.detail_devis, name='detail_devis'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('sending_data/', views.sendingData, name='sendingData'),
    #path('creer_tache/', views.creer_tache, name='creer_tache'),
]
