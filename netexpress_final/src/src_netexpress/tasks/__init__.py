"""Tasks app for NetExpress CRM.

This application provides a simple task tracking system used by the
dashboard.  Tasks can be created with a title, description, a location
where the work will occur and the team responsible for completing it.
Each task keeps track of a start date and a due date.  The status of
the task is automatically updated based on the current date whenever
the task is saved: upcoming tasks (``à venir``) have a start date in
the future, tasks ``en cours`` are currently underway, tasks ``en
retard`` are past their due date but not yet completed and tasks
``terminées`` have explicitly been marked as done.  Administrators
can filter and manage tasks through the Django admin interface.

To enable notifications when tasks approach their due date or when
their status changes, connect the signals in this app to your email
service.  See :mod:`unzip.src.netexpress.tasks.models` for details.
"""
