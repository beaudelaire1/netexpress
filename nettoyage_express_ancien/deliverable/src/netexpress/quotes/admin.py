"""
Admin registration for the Quote model.

This exposes customer quote requests in the Django admin.  Staff can filter
requests by status and search for particular clients.  Jazzmin will apply
styling automatically.
"""

from django.contrib import admin
from .models import Quote


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "service")
    date_hierarchy = "created_at"