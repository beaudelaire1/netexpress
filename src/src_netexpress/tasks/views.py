"""Vues pour le suivi des tâches (class-based views)."""

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.generic import ListView, DetailView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .models import Task
from core.decorators import worker_portal_required
from tasks.application.status import sync_task_status


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


@method_decorator(worker_portal_required, name='dispatch')
class WorkerDashboardView(LoginRequiredMixin, TemplateView):
    """Worker Portal dashboard showing tasks assigned to the authenticated worker."""
    template_name = "tasks/worker_dashboard.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter tasks by assigned worker
        user_tasks = Task.objects.filter(assigned_to=self.request.user).order_by('due_date', 'start_date')
        
        # Separate tasks by status for better organization (evaluate QuerySets to avoid multiple DB queries)
        upcoming_tasks_qs = user_tasks.filter(status=Task.STATUS_UPCOMING)
        in_progress_tasks_qs = user_tasks.filter(status=Task.STATUS_IN_PROGRESS)
        almost_overdue_tasks_qs = user_tasks.filter(status=Task.STATUS_ALMOST_OVERDUE)
        overdue_tasks_qs = user_tasks.filter(status=Task.STATUS_OVERDUE)
        completed_tasks_qs = user_tasks.filter(status=Task.STATUS_COMPLETED)[:10]  # Show last 10 completed
        
        # Convert to lists to avoid lazy evaluation issues in templates
        context['upcoming_tasks'] = list(upcoming_tasks_qs)
        context['in_progress_tasks'] = list(in_progress_tasks_qs)
        context['almost_overdue_tasks'] = list(almost_overdue_tasks_qs)
        context['overdue_tasks'] = list(overdue_tasks_qs)
        context['completed_tasks'] = list(completed_tasks_qs)
        
        # Summary statistics (pre-calculate counts to avoid template queries)
        context['total_assigned'] = user_tasks.count()
        context['pending_tasks'] = user_tasks.exclude(status=Task.STATUS_COMPLETED).count()
        context['upcoming_tasks_count'] = len(context['upcoming_tasks'])
        context['in_progress_tasks_count'] = len(context['in_progress_tasks'])
        context['almost_overdue_tasks_count'] = len(context['almost_overdue_tasks'])
        context['overdue_tasks_count'] = len(context['overdue_tasks'])
        
        # Unread messages count for worker
        from messaging.models import Message
        context['unread_messages_count'] = Message.objects.filter(
            recipient=self.request.user,
            read_at__isnull=True
        ).count()
        
        return context


@method_decorator(worker_portal_required, name='dispatch')
class WorkerScheduleView(LoginRequiredMixin, TemplateView):
    """Worker schedule calendar view showing daily and weekly schedules."""
    template_name = "tasks/worker_schedule.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter tasks by assigned worker
        user_tasks = Task.objects.filter(assigned_to=self.request.user).order_by('start_date', 'due_date')
        
        # Get tasks for the current week/month for calendar display
        context['user_tasks'] = user_tasks
        
        return context


@require_GET
def worker_task_events(request):
    """Return FullCalendar events for worker's assigned tasks with client information.
    
    This endpoint provides task events specifically for the authenticated worker,
    including client details and intervention information.
    """
    from datetime import date, timedelta
    
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)
    
    today = date.today()
    events = []
    
    # Filter tasks by assigned worker
    user_tasks = Task.objects.filter(assigned_to=request.user).prefetch_related('assigned_to').order_by("due_date", "start_date", "pk")
    
    for task in user_tasks:
        # Update task status dynamically via application service (best-effort persist)
        try:
            sync_task_status(task, today=today, save_if_changed=True)
        except Exception:
            pass
        
        # Color coding for worker calendar
        if task.status == Task.STATUS_COMPLETED:
            color = "#2563eb"  # blue (completed)
        elif task.status == Task.STATUS_OVERDUE:
            color = "#dc2626"  # red
        elif task.status == Task.STATUS_ALMOST_OVERDUE:
            color = "#f59e0b"  # orange
        else:
            # Proximity coloring for non-completed tasks
            if task.due_date:
                remaining = (task.due_date - today).days
                if remaining <= 3:
                    color = "#facc15"  # yellow (due soon)
                else:
                    color = "#16a34a"  # green (on schedule)
            else:
                color = "#16a34a"
        
        # FullCalendar requires start date
        start_date = task.start_date or task.due_date
        if not start_date:
            continue
        end_date = (task.due_date + timedelta(days=1)) if task.due_date else (start_date + timedelta(days=1))
        
        # Enhanced title with location information for workers
        title = (task.title or "").strip() or f"Tâche #{task.pk}"
        if task.location:
            title += f" - {task.location}"
        
        events.append({
            "id": task.pk,
            "title": title,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "url": task.get_absolute_url(),
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#ffffff",
            "extendedProps": {
                "location": task.location,
                "description": task.description,
                "team": task.team,
                "status": task.get_status_display(),
            }
        })
    
    return JsonResponse(events, safe=False)


@method_decorator(worker_portal_required, name='dispatch')
class TaskCompleteView(LoginRequiredMixin, View):
    """Handle task completion by workers."""
    
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
        
        # Only allow completion if task is not already completed
        if task.status == Task.STATUS_COMPLETED:
            messages.warning(request, "Cette tâche est déjà marquée comme terminée.")
            return redirect('worker:worker_dashboard')
        
        # Update task status and completion info
        task.status = Task.STATUS_COMPLETED
        task.completed_by = request.user
        task.completion_notes = request.POST.get('completion_notes', '')
        task.save()
        
        messages.success(request, f"Tâche '{task.title}' marquée comme terminée avec succès!")
        
        # Return JSON response for HTMX requests
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'success', 'message': 'Tâche terminée avec succès!'})
        
        return redirect('worker:worker_dashboard')


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
        try:
            sync_task_status(t, today=today, save_if_changed=True)
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

