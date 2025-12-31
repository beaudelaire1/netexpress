"""
Routes de l'application ``core``.

Cette configuration définit les chemins de l'accueil, d'une route de santé
pour les sondes de monitoring et de la page À propos.  Les chemins
utilisent un espace de noms afin de faciliter leur utilisation dans les
templates.
"""

from django.urls import path
from . import views
from . import views_campaigns

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
    # Dashboard technique supprimé - Migration vers /admin-dashboard/
    # Les clients utilisent /client/
    # Les ouvriers utilisent /worker/
    # Les admins business utilisent /admin-dashboard/
    # Les admins techniques utilisent /gestion/ (Django Admin)
    
    # Client Portal URLs
    path("client/", views.client_dashboard, name="client_portal_dashboard"),
    path("client/quotes/", views.client_quotes, name="client_quotes"),
    path("client/invoices/", views.client_invoices, name="client_invoices"),
    path("client/quotes/<int:pk>/", views.client_quote_detail, name="client_quote_detail"),
    path("client/invoices/<int:pk>/", views.client_invoice_detail, name="client_invoice_detail"),
    
    # Client Portal PDF Downloads
    path("client/invoices/<int:pk>/download/", views.client_invoice_download, name="client_invoice_download"),
    path("client/quotes/<int:pk>/download/", views.client_quote_download, name="client_quote_download"),
    
    # Client Portal Signature Workflow
    path("client/quotes/<int:pk>/validate/", views.client_quote_validate_start, name="client_quote_validate_start"),
    path("client/quotes/<int:pk>/validate/code/", views.client_quote_validate_code, name="client_quote_validate_code"),
    
    # Admin Portal URLs (moved from urls_admin.py to avoid namespace conflicts)
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/planning/", views.admin_global_planning, name="admin_global_planning"),
    
    # Workers
    path("admin-dashboard/workers/", views.admin_workers_list, name="admin_workers_list"),
    path("admin-dashboard/workers/<int:pk>/", views.admin_worker_detail, name="admin_worker_detail"),
    path("admin-dashboard/workers/create/", views.admin_create_worker, name="admin_create_worker"),
    
    # Clients
    path("admin-dashboard/clients/", views.admin_clients_list, name="admin_clients_list"),
    path("admin-dashboard/clients/<int:pk>/", views.admin_client_detail, name="admin_client_detail"),
    path("admin-dashboard/clients/create/", views.admin_create_client, name="admin_create_client"),
    
    # Quotes
    path("admin-dashboard/quotes/", views.admin_quotes_list, name="admin_quotes_list"),
    path("admin-dashboard/quotes/<int:pk>/", views.admin_quote_detail, name="admin_quote_detail"),
    path("admin-dashboard/quotes/create/", views.admin_create_quote, name="admin_create_quote"),
    path("admin-dashboard/quotes/<int:pk>/edit/", views.admin_edit_quote, name="admin_edit_quote"),
    path("admin-dashboard/quotes/<int:pk>/send-email/", views.admin_send_quote_email, name="admin_send_quote_email"),
    path("admin-dashboard/quotes/<int:pk>/convert/", views.admin_convert_quote_to_invoice, name="admin_convert_quote_to_invoice"),
    
    # Invoices
    path("admin-dashboard/invoices/", views.admin_invoices_list, name="admin_invoices_list"),
    path("admin-dashboard/invoices/<int:pk>/", views.admin_invoice_detail, name="admin_invoice_detail"),
    path("admin-dashboard/invoices/<int:pk>/mark-paid/", views.admin_invoice_mark_paid, name="admin_invoice_mark_paid"),
    path("admin-dashboard/invoices/create/", views.admin_create_invoice, name="admin_create_invoice"),
    
    # Tasks
    path("admin-dashboard/tasks/", views.admin_tasks_list, name="admin_tasks_list"),
    path("admin-dashboard/tasks/<int:pk>/", views.admin_task_detail, name="admin_task_detail"),
    path("admin-dashboard/tasks/create/", views.admin_create_task, name="admin_create_task"),
    
    # Analytics & Reporting
    path("admin-dashboard/analytics/", views.admin_analytics, name="admin_analytics"),
    path("admin-dashboard/reports/", views.admin_reports, name="admin_reports"),
    path("admin-dashboard/reports/export/", views.admin_export_report, name="admin_export_report"),
    
    # Notification HTMX endpoints
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/list/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    
    # Email Campaigns (Brevo)
    path("admin-dashboard/campaigns/", views_campaigns.campaigns_list, name="campaigns_list"),
    path("admin-dashboard/campaigns/create/", views_campaigns.create_campaign, name="create_campaign"),
    path("admin-dashboard/campaigns/<int:campaign_id>/", views_campaigns.campaign_detail, name="campaign_detail"),
    path("admin-dashboard/campaigns/<int:campaign_id>/send/", views_campaigns.send_campaign, name="send_campaign"),
    path("admin-dashboard/campaigns/<int:campaign_id>/delete/", views_campaigns.delete_campaign, name="delete_campaign"),
]