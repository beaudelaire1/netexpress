from django.utils.html import format_html
from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Client, Service, Devis, Tache, EmailService
from django.urls import reverse


# Fonction pour exporter les données sélectionnées en format CSV
def export_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export.csv"'
    writer = csv.writer(response)
    fields = [field.name for field in modeladmin.model._meta.fields]
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in fields])
    return response


export_to_csv.short_description = "Exporter en CSV"


# Enregistrement et configuration de l'administration du modèle Client
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Client', {'fields': ('nom', 'prenom',)}),
        ('Contact', {'fields': ('email', 'telephone', 'adresse', 'code_postal')}),
    )
    actions = [export_to_csv]
    list_display = ('nom', 'prenom', 'email', 'telephone',)
    search_fields = ('nom', 'prenom', 'code_postal')
    list_filter = ('nom', 'prenom', 'code_postal')
    list_per_page = 10


# Enregistrement et configuration de l'administration du modèle Service
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Service', {'fields': ('nom', 'prix',)}),
        ('Catégorie', {'fields': ('service',)}),
    )
    list_display = ('nom', 'prix', 'service')
    search_fields = ('nom',)
    list_filter = ('nom', 'service')
    list_per_page = 10


# Enregistrement et configuration de l'administration du modèle Devis
@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Client', {'fields': ('client', 'service')}),
        ('Prix', {'fields': ('prix_total',)}),
    )
    list_display = ('client', 'prix_initial', 'reduction', 'prix_total', 'date_de_creation', 'voir_detail')
    search_fields = ('client', 'prix_total',)
    list_filter = ('client',)
    list_per_page = 10
    readonly_fields = ('prix_total',)

    def voir_detail(self, obj):
        url = reverse('detail_devis', args=[obj.id])
        return format_html('<a href="{}">Voir Détail</a>', url)

    voir_detail.short_description = 'Détails'


# Enregistrement et configuration de l'administration du modèle Tache
@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Tâche', {'fields': ('titre', 'localisation', 'description')}),
        ('Date', {'fields': ('date_debut', 'date_fin')}),
        ('Statut', {'fields': ('statut',)}),
    )
    list_display = ('titre', 'description', 'localisation', 'statut', 'date_debut', 'date_fin')
    search_fields = ('titre',)
    list_per_page = 10

