"""
Admin Portal URL configuration.

Defines URL patterns specific to the Admin Portal (/admin-dashboard/...).
All URLs in this file are prefixed with /admin-dashboard/ by the main URL configuration.
"""

from django.urls import path
from . import views

# Note: app_name is not set here to avoid namespace conflicts with core.urls
# The namespace is specified explicitly in netexpress/urls.py

urlpatterns = [
    # Admin Portal Dashboard
    path("", views.admin_dashboard, name="admin_dashboard"),
    
    # Global Planning and Management
    path("planning/", views.admin_global_planning, name="admin_global_planning"),
    
    # Worker Management
    path("workers/", views.admin_workers_list, name="admin_workers_list"),
    path("workers/create/", views.admin_create_worker, name="admin_create_worker"),
    
    # Client Management
    path("clients/", views.admin_clients_list, name="admin_clients_list"),
    path("clients/create/", views.admin_create_client, name="admin_create_client"),
    
    # Quote Management
    path("quotes/", views.admin_quotes_list, name="admin_quotes_list"),
    path("quotes/create/", views.admin_create_quote, name="admin_create_quote"),
    path("quotes/<int:pk>/send-email/", views.admin_send_quote_email, name="admin_send_quote_email"),
    
    # Invoice Management
    path("invoices/", views.admin_invoices_list, name="admin_invoices_list"),
    path("invoices/create/", views.admin_create_invoice, name="admin_create_invoice"),
    
    # Task Management
    path("tasks/create/", views.admin_create_task, name="admin_create_task"),
    
    # Legacy dashboard redirects for backward compatibility
    path("dashboard/", views.dashboard, name="legacy_dashboard"),
    
    # Notification endpoints (HTMX)
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/list/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]