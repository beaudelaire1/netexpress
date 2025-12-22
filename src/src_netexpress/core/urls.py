"""
Routes de l'application ``core``.

Cette configuration définit les chemins de l'accueil, d'une route de santé
pour les sondes de monitoring et de la page À propos.  Les chemins
utilisent un espace de noms afin de faciliter leur utilisation dans les
templates.
"""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Page d'accueil
    path("", views.home, name="home"),
    # Endpoint de monitoring, renvoie un JSON simple
    path("health/", views.health, name="health"),
    # Page "À propos" selon le cahier des charges
    path("a-propos/", views.about, name="about"),
    # Page "L’Excellence" dédiée aux valeurs de l'entreprise
    path("excellence/", views.excellence, name="excellence"),
    # Galerie de réalisations avec filtrage et lightbox
    path("realisations/", views.realisations, name="realisations"),
    # Tableau de bord agrégé
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/client/", views.client_dashboard, name="client_dashboard"),
    path("dashboard/ouvrier/", views.worker_dashboard, name="worker_dashboard"),
    
    # Client Portal URLs
    path("client/", views.client_dashboard, name="client_portal_dashboard"),
    path("client/quotes/", views.client_quotes, name="client_quotes"),
    path("client/invoices/", views.client_invoices, name="client_invoices"),
    path("client/quotes/<int:pk>/", views.client_quote_detail, name="client_quote_detail"),
    path("client/invoices/<int:pk>/", views.client_invoice_detail, name="client_invoice_detail"),
    
    # Client Portal Signature Workflow
    path("client/quotes/<int:pk>/validate/", views.client_quote_validate_start, name="client_quote_validate_start"),
    path("client/quotes/<int:pk>/validate/code/", views.client_quote_validate_code, name="client_quote_validate_code"),
    
    # Admin Portal URLs
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/planning/", views.admin_global_planning, name="admin_global_planning"),
    path("admin-dashboard/workers/", views.admin_workers_list, name="admin_workers_list"),
    path("admin-dashboard/workers/create/", views.admin_create_worker, name="admin_create_worker"),
    path("admin-dashboard/clients/", views.admin_clients_list, name="admin_clients_list"),
    path("admin-dashboard/clients/create/", views.admin_create_client, name="admin_create_client"),
    path("admin-dashboard/quotes/", views.admin_quotes_list, name="admin_quotes_list"),
    path("admin-dashboard/quotes/create/", views.admin_create_quote, name="admin_create_quote"),
    path("admin-dashboard/quotes/<int:pk>/send-email/", views.admin_send_quote_email, name="admin_send_quote_email"),
    path("admin-dashboard/invoices/", views.admin_invoices_list, name="admin_invoices_list"),
    path("admin-dashboard/invoices/create/", views.admin_create_invoice, name="admin_create_invoice"),
    path("admin-dashboard/tasks/create/", views.admin_create_task, name="admin_create_task"),
    
    # Notification HTMX endpoints
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/list/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]