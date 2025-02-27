from django.utils.html import format_html
from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Client, Service, Devis, Tache
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

# Classe de base pour les configurations d'administration
class BaseAdmin(admin.ModelAdmin):
    actions = [export_to_csv]
    list_per_page = 10

# Enregistrement et configuration de l'administration du modèle Client
@admin.register(Client)
class ClientAdmin(BaseAdmin):
    fieldsets = (
        ('Client', {'fields': ('nom', 'prenom',)}),
        ('Contact', {'fields': ('email', 'telephone', 'adresse', 'code_postal')}),
    )
    list_display = ('nom', 'prenom', 'email', 'telephone',)
    search_fields = ('nom', 'prenom', 'code_postal')
    list_filter = ('code_postal', )

# Enregistrement et configuration de l'administration du modèle Service
@admin.register(Service)
class ServiceAdmin(BaseAdmin):
    fieldsets = (
        ('Service', {'fields': ('nom', 'prix',)}),
        ('Catégorie', {'fields': ('service',)}),
    )
    list_display = ('nom', 'prix', 'service')
    search_fields = ('nom',)
    list_filter = ('service', )

# Enregistrement et configuration de l'administration du modèle Devis
@admin.register(Devis)
class DevisAdmin(BaseAdmin):
    fieldsets = (
        ('Client', {'fields': ('client', 'service')}),
        ('Prix', {'fields': ('prix_total',)}),
        ('Réduction', {'fields': ('reduction',)}),
        ('Date', {'fields': ('date_de_validite', 'date_de_creation' )}),
        ('Description', {'fields': ('description',)}),
    )
    list_display = ('client', 'prix_initial', 'reduction', 'prix_total', 'numero_devis', 'date_de_validite', 'voir_detail', )
    search_fields = ('client_nom', 'client_prenom', 'prix_total', 'numero_devis')
    list_editable = ('prix_initial', 'reduction', 'date_de_validite')
    readonly_fields = ('prix_total',)
    list_filter = ('date_de_validite', 'service')

    def voir_detail(self, obj):
        url = reverse('detail_devis', args=[obj.id])
        return format_html('<a href="{}">Voir Détail</a>', url)

    voir_detail.short_description = 'Détails'

# Enregistrement et configuration de l'administration du modèle Tache
@admin.register(Tache)
class TacheAdmin(BaseAdmin):
    fieldsets = (
        ('Tâche', {'fields': ('titre', 'localisation', 'description')}),
        ('Date', {'fields': ('date_debut', 'date_fin')}),
        ('Statut', {'fields': ('statut',)}),
    )
    list_display = ('titre', 'localisation', 'statut', 'date_debut', 'date_fin')
    search_fields = ('titre', 'localisation')
    list_filter = ('localisation', )
    list_editable = ('statut', 'date_fin')
