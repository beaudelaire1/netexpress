"""Vues pour le suivi des tâches (class-based views)."""

from django.views.generic import ListView, DetailView

from .models import Task


class TaskListView(ListView):
    """Liste toutes les tâches pour le tableau de bord opérationnel."""
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    ordering = ["-created_at"]


class TaskDetailView(DetailView):
    """Affiche le détail d'une tâche individuelle."""
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"
