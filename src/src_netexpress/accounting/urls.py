from django.urls import path
from . import views

app_name = "accounting"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ventes/", views.sales, name="sales"),
    path("ventes/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("ventes/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("ventes/<int:pk>/controle/", views.review_invoice, name="review_invoice"),
    path("achats/", views.suppliers, name="suppliers"),
    path("achats/ajouter/", views.supplier_edit, name="supplier_add"),
    path("achats/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("achats/<int:pk>/modifier/", views.supplier_edit, name="supplier_edit"),
    path("achats/<int:pk>/controle/", views.review_supplier, name="review_supplier"),
    path("export/", views.export_documents, name="export"),
    path("acces/", views.accountants, name="accountants"),
    path("acces/<int:pk>/", views.accountant_action, name="accountant_action"),
]
