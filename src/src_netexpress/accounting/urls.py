from django.urls import path
from . import views, workspace

app_name = "accounting"
urlpatterns = [
    path("", workspace.dashboard, name="dashboard"),
    path("devis/", views.quotes, name="quotes"),
    path("devis/<int:pk>/", views.quote_detail, name="quote_detail"),
    path("devis/<int:pk>/pdf/", views.quote_pdf, name="quote_pdf"),
    path("ventes/", workspace.sales, name="sales"),
    path("ventes/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("ventes/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("ventes/<int:pk>/controle/", views.review_invoice, name="review_invoice"),
    path("achats/", views.suppliers, name="suppliers"),
    path("achats/ajouter/", views.supplier_edit, name="supplier_add"),
    path("achats/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("achats/<int:pk>/modifier/", views.supplier_edit, name="supplier_edit"),
    path("achats/<int:pk>/controle/", views.review_supplier, name="review_supplier"),
    path("documents/", views.documents, name="documents"),
    path("documents/ajouter/", views.document_edit, name="document_add"),
    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/modifier/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/controle/", views.review_document, name="review_document"),
    path("export/", views.export_documents, name="export"),
    path("acces/", views.accountants, name="accountants"),
    path("acces/<int:pk>/", views.accountant_action, name="accountant_action"),
]
