"""Administration interface for the tasks application.

The task admin configuration exposes the most important fields at a
glance and allows administrators to quickly update the status of
selected tasks.  An action is provided to mark tasks as completed.
"""

from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "get_status_display",
        "start_date",
        "due_date",
        "location",
        "team",
    )
    list_filter = ("status", "due_date", "team")
    search_fields = ("title", "description", "location", "team")
    date_hierarchy = "due_date"
    actions = ["mark_completed"]

    @admin.action(description="Marquer comme terminé les tâches sélectionnées")
    def mark_completed(self, request, queryset):
        updated = 0
        for task in queryset:
            if task.status != Task.STATUS_COMPLETED:
                task.status = Task.STATUS_COMPLETED
                task.save(update_fields=["status"])
                updated += 1
        self.message_user(request, f"{updated} tâche(s) marquée(s) comme terminée(s).")
