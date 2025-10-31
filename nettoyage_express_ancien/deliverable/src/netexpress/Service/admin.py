"""
Admin registration for the service catalogue.

This configuration exposes the Service model in the Django admin and adds a few
list displays and filters to improve usability for staff members. When Jazzmin
is installed, this admin will inherit the modern look and feel provided by
Jazzmin out of the box.
"""

from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "base_price", "duration_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description", "short_description")
    prepopulated_fields = {"slug": ("title",)}
