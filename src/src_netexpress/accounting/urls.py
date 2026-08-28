from django.urls import path

from . import communication, exchange_views, filter_views, search_views, views, workspace

app_name = "accounting"

urlpatterns = [
    path("", workspace.dashboard, name="dashboard"),
    path("recherche/", search_views.search, name="search"),
    path("message-netexpress/", communication.send_message_to_netexpress, name="message_netexpress"),
    path("echanges/", filter_views.exchanges, name="exchanges"),
    path("echanges/nouveau/", exchange_views.exchange_create, name="exchange_create"),
    path("echanges/<int:pk>/", exchange_views.exchange_detail, name="exchange_detail"),
    path("echanges/<int:pk>/repondre/", exchange_views.exchange_reply, name="exchange_reply"),
    path("echanges/<int:pk>/document/", exchange_views.exchange_document_upload, name="exchange_document_upload"),
    path("echanges/<int:pk>/statut/", exchange_views.exchange_status, name="exchange_status"),
    path(
        "echanges/<int:pk>/document/<int:document_id>/classer/",
        exchange_views.exchange_document_promote,
        name="exchange_document_promote",
    ),
    path("devis/<int:pk>/", views.quote_detail, name="quote_detail"),
    path("devis/<int:pk>/pdf/", views.quote_pdf, name="quote_pdf"),
    path("ventes/", workspace.sales, name="sales"),
    path("ventes/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("ventes/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("ventes/<int:pk>/controle/", workspace.review_invoice, name="review_invoice"),
    path("achats/", workspace.suppliers, name="suppliers"),
    path("achats/ajouter/", views.supplier_edit, name="supplier_add"),
    path("achats/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("achats/<int:pk>/modifier/", views.supplier_edit, name="supplier_edit"),
    path("achats/<int:pk>/controle/", workspace.review_supplier, name="review_supplier"),
    path("documents/", filter_views.documents, name="documents"),
    path("documents/ajouter/", views.document_edit, name="document_add"),
    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/modifier/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/controle/", workspace.review_document, name="review_document"),
    path("export/", views.export_documents, name="export"),
    path("acces/", views.accountants, name="accountants"),
    path("acces/<int:pk>/", views.accountant_action, name="accountant_action"),
]
