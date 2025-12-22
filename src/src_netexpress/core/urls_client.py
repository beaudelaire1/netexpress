"""
Client Portal URL configuration.

Defines URL patterns specific to the Client Portal (/client/...).
All URLs in this file are prefixed with /client/ by the main URL configuration.
"""

from django.urls import path
from . import views

app_name = "client_portal"

urlpatterns = [
    # Client Portal Dashboard
    path("", views.client_dashboard, name="dashboard"),
    
    # Document Management
    path("quotes/", views.client_quotes, name="quotes"),
    path("invoices/", views.client_invoices, name="invoices"),
    path("quotes/<int:pk>/", views.client_quote_detail, name="quote_detail"),
    path("invoices/<int:pk>/", views.client_invoice_detail, name="invoice_detail"),
    
    # Electronic Signature Workflow
    path("quotes/<int:pk>/validate/", views.client_quote_validate_start, name="quote_validate_start"),
    path("quotes/<int:pk>/validate/code/", views.client_quote_validate_code, name="quote_validate_code"),
    
    # Notification endpoints (HTMX)
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/list/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]