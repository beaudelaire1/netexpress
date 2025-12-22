"""Models for the task tracking system.

The ``Task`` model offers a lightweight way to organise work across
your business.  Each task stores a title, an optional description,
a location where the work will take place and the team responsible for
execution.  The start and due dates define the planned timeframe.  A
status field tracks whether the task is upcoming (not yet started),
in progress, completed or overdue.  The status is recalculated
automatically whenever the task is saved unless it has been marked
completed manually.

Tasks can compute whether they are due soon via the
:meth:`~unzip.src.netexpress.tasks.models.Task.is_due_soon` helper.
Notification signals are registered in ``tasks.signals`` to
automatically send emails when a task changes status or approaches
its deadline.  See ``tasks.services.EmailNotificationService`` for
details on configuring the outgoing mail server.
"""

from __future__ import annotations

from datetime import date
from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):
    """Represents a work item to be tracked on the dashboard.

    Attributes
    ----------
    title : str
        A concise label describing the work to be done.
    description : str
        An optional free‑form description.  Leave blank for a short
        task summary.
    location : str
        Where the task will be executed (e.g. address or site name).  May
        be left empty if not relevant.
    team : str
        A human readable identifier of the team responsible for this
        task (for example "Équipe espaces verts").  Notification
        emails may be sent to a central address for all tasks; this
        field is provided for administrative reference only.
    start_date : date
        The planned start date.  Defaults to the day the task is
        created.  If this date is in the future, the status is set to
        ``upcoming``.
    due_date : date
        The deadline by which the task should be completed.  Must be
        provided by the user.  If the deadline has passed and the
        task is not completed the status becomes ``overdue``.
    status : str
        Tracks the current state of the task.  This field is
        automatically maintained on save based on the dates unless it
        has been explicitly set to ``completed``.  The possible values
        are:

        * ``upcoming`` (À venir) — the task is scheduled but not
          started yet.
        * ``in_progress`` (En cours) — the task is underway.
        * ``completed`` (Terminé) — the task has been finished.
        * ``overdue`` (En retard) — the due date has passed and the task
          is not yet completed.
    created_at : datetime
        Timestamp of when the task record was created.
    updated_at : datetime
        Timestamp of the last update to the task record.
    """

    STATUS_UPCOMING = "upcoming"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_OVERDUE = "overdue"
    STATUS_ALMOST_OVERDUE = "almost_overdue"

    STATUS_CHOICES = [
        (STATUS_UPCOMING, "À venir"),
        (STATUS_IN_PROGRESS, "En cours"),
        (STATUS_COMPLETED, "Terminé"),
        (STATUS_OVERDUE, "En retard"),
        (STATUS_ALMOST_OVERDUE, "Presque en retard"),
    ]

    title: str = models.CharField(max_length=200)
    description: str = models.TextField(blank=True)
    location: str = models.CharField(max_length=200, blank=True)
    team: str = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nom de l'équipe en charge de cette tâche (information interne)"
    )
    start_date: date = models.DateField(default=date.today)
    due_date: date = models.DateField()
    status: str = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UPCOMING,
    )
    
    # Worker assignment fields
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        limit_choices_to={'groups__name': 'Workers'},
        help_text="Worker assigned to this task"
    )
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes added by the worker upon task completion"
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_tasks',
        help_text="Worker who marked this task as completed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "title"]
        verbose_name = "tâche"
        verbose_name_plural = "tâches"

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self) -> str:
        """
        Retourne l'URL canonique vers le détail de cette tâche.

        Cette méthode est utilisée par Django pour générer automatiquement
        des liens vers les vues détaillées des instances.  Elle s'appuie sur
        l'espace de noms ``tasks`` défini dans ``tasks/urls.py``.

        >>> from django.urls import reverse
        >>> t = Task(id=1, title='Exemple')
        >>> t.get_absolute_url()  # doctest: +SKIP
        '/taches/1/'
        """
        from django.urls import reverse
        return reverse("tasks:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs) -> None:
        """Persist the task and update its status automatically.

        Unless the status is explicitly set to ``completed``, the value
        will be recalculated based on the start and due dates.  If the
        due date has passed the status becomes ``overdue``.  If the
        start date is in the future the status becomes ``upcoming``.
        Otherwise the status is set to ``in_progress``.
        """
        today = date.today()
        # Recalcule systématiquement le statut (sauf terminé) pour refléter la réalité du planning.
        if self.status != self.STATUS_COMPLETED:
            if self.due_date and self.due_date < today:
                # Jour passé -> en retard
                self.status = self.STATUS_OVERDUE
            elif self.due_date and (self.due_date - today).days <= 1:
                # 0 ou 1 jour restant -> presque en retard (même si déjà "en cours")
                self.status = self.STATUS_ALMOST_OVERDUE
            elif self.start_date and self.start_date > today:
                # Début dans le futur
                self.status = self.STATUS_UPCOMING
            else:
                # Par défaut : en cours (si start_date est vide ou <= aujourd'hui)
                self.status = self.STATUS_IN_PROGRESS

        # Enforce that the due date cannot precede the start date
        if self.due_date and self.start_date and self.due_date < self.start_date:
            raise ValueError("La date d'échéance ne peut pas être antérieure à la date de début.")
        super().save(*args, **kwargs)

    def is_due_soon(self, days_threshold: int = 3) -> bool:
        """Return ``True`` if the task's due date is within ``days_threshold`` days.

        Completed tasks always return ``False``.  Tasks with no due date
        also return ``False``.  The threshold is inclusive, i.e. if the
        due date is today and ``days_threshold`` is 0 the method
        returns ``True``.

        Parameters
        ----------
        days_threshold : int
            Number of days before the deadline at which the task is
            considered due soon.
        """
        if self.status == self.STATUS_COMPLETED or not self.due_date:
            return False
        remaining = (self.due_date - date.today()).days
        return remaining <= days_threshold
