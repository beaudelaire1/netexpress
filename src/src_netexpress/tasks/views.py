"""Vues pour le suivi des tâches (class-based views)."""

from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.generic import ListView, DetailView, TemplateView

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


class TaskCalendarView(TemplateView):
    """Vue calendrier mensuel (FullCalendar) pour les tâches."""
    template_name = "tasks/task_calendar.html"


@require_GET
def task_events(request):
    """Retourne les événements FullCalendar (vue mensuelle).

    - Affiche toujours un intitulé (title)
    - Couleurs selon statut + proximité (rouge/orange/jaune/vert/bleu)
    - Met à jour automatiquement le statut en base si besoin
    """
    from datetime import date, timedelta

    today = date.today()
    events = []

    qs = Task.objects.all().order_by("due_date", "start_date", "pk")

    for t in qs:
        # --- Calcul dynamique du statut (et correction en base si nécessaire)
        new_status = t.status
        if t.status != Task.STATUS_COMPLETED:
            if t.due_date and t.due_date < today:
                new_status = Task.STATUS_OVERDUE
            elif t.due_date and (t.due_date - today).days <= 1:
                new_status = Task.STATUS_ALMOST_OVERDUE
            else:
                # si start_date est dans le futur => à venir, sinon en cours
                if t.start_date and t.start_date > today:
                    new_status = Task.STATUS_UPCOMING
                else:
                    new_status = Task.STATUS_IN_PROGRESS

        if new_status != t.status:
            t.status = new_status
            try:
                t.save(update_fields=["status"])
            except Exception:
                pass

        # --- Couleur FullCalendar
        if t.status == Task.STATUS_COMPLETED:
            color = "#2563eb"  # bleu (terminé)
        elif t.status == Task.STATUS_OVERDUE:
            color = "#dc2626"  # rouge
        elif t.status == Task.STATUS_ALMOST_OVERDUE:
            color = "#f59e0b"  # orange
        else:
            # Proximité (hors terminé)
            if t.due_date:
                remaining = (t.due_date - today).days
                if remaining <= 3:
                    color = "#facc15"  # jaune (proche)
                else:
                    color = "#16a34a"  # vert (dans le timing)
            else:
                color = "#16a34a"

        # FullCalendar nécessite start; fallback: due_date si start_date vide
        start_date = t.start_date or t.due_date
        if not start_date:
            continue
        end_date = (t.due_date + timedelta(days=1)) if t.due_date else (start_date + timedelta(days=1))

        title = (t.title or "").strip() or f"Tâche #{t.pk}"

        events.append({
            "id": t.pk,
            "title": title,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "url": t.get_absolute_url(),
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#ffffff",
        })

    return JsonResponse(events, safe=False)

