"""URL configuration for the tasks application.

This module defines a minimal set of routes for listing and viewing
individual tasks.  The routes are namespaced under ``tasks`` and may
be included in the project's URL configuration.  The list view
displays upcoming, in‑progress, overdue and completed tasks.  The
detail view shows all the information for a single task.
"""

from django.urls import path
from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("<int:pk>/", views.task_detail, name="detail"),
]
