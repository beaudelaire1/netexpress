"""Views for the tasks application.

Two simple views are provided: one to list all tasks and one to display
the details of a single task.  These views are intentionally kept
lightweight and rely on the default Django template naming
conventions.  Feel free to extend or replace them with class‑based
views, forms for editing tasks or API endpoints according to your
project's needs.
"""

from __future__ import annotations

from django.shortcuts import render, get_object_or_404

from .models import Task


def task_list(request):
    """Render a page with a list of all tasks ordered by due date.

    The list groups tasks by their status and displays them chronologically
    so that upcoming deadlines are easy to identify.  A future
    improvement could add filtering or pagination for large task lists.
    """
    tasks = Task.objects.all().order_by("due_date")
    return render(request, "tasks/task_list.html", {"tasks": tasks})


def task_detail(request, pk: int):
    """Render a page with the details of a single task identified by ``pk``.

    If the task does not exist a 404 error is raised.  The detail view
    shows all fields of the task and could be extended to include
    history, comments or attachments.
    """
    task = get_object_or_404(Task, pk=pk)
    return render(request, "tasks/task_detail.html", {"task": task})
