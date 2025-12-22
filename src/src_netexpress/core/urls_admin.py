"""
Admin Portal URL configuration.

Defines URL patterns specific to the Admin Portal (/admin-dashboard/...).
All URLs in this file are prefixed with /admin-dashboard/ by the main URL configuration.
"""

from django.urls import path
from . import views

app_name = "admin_portal"

urlpatterns = [
    # Admin Portal Dashboard
    path("", views.admin_dashboard, name="dashboard"),
    
    # Global Planning and Management
    path("planning/", views.admin_global_planning, name="global_planning"),
    
    # Worker Management
    path("workers/", views.admin_workers_list, name="workers_list"),
    path("workers/create/", views.admin_create_worker, name="create_worker"),
    
    # Client Management
    path("clients/", views.admin_clients_list, name="clients_list"),
    path("clients/create/", views.admin_create_client, name="create_client"),
    
    # Quote Management
    path("quotes/create/", views.admin_create_quote, name="create_quote"),
    
    # Task Management
    path("tasks/create/", views.admin_create_task, name="create_task"),
    
    # Legacy dashboard redirects for backward compatibility
    path("dashboard/", views.dashboard, name="legacy_dashboard"),
    
    # Notification endpoints (HTMX)
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/list/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]