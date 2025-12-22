"""
Worker Portal URL configuration.

Defines URL patterns specific to the Worker Portal (/worker/...).
All URLs in this file are prefixed with /worker/ by the main URL configuration.
"""

from django.urls import path
from tasks import views as task_views
from core import views as core_views

app_name = "worker"

urlpatterns = [
    # Worker Portal Dashboard
    path("", task_views.WorkerDashboardView.as_view(), name="worker_dashboard"),
    
    # Task Management
    path("tasks/", task_views.TaskListView.as_view(), name="task_list"),
    path("tasks/<int:pk>/", task_views.TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/complete/", task_views.TaskCompleteView.as_view(), name="complete"),
    
    # Schedule and Calendar
    path("schedule/", task_views.WorkerScheduleView.as_view(), name="worker_schedule"),
    path("calendar/", task_views.TaskCalendarView.as_view(), name="calendar"),
    path("events/", task_views.worker_task_events, name="worker_events"),
    
    # Notification endpoints (HTMX)
    path("notifications/count/", core_views.notification_count, name="notification_count"),
    path("notifications/list/", core_views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/read/", core_views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", core_views.mark_all_notifications_read, name="mark_all_notifications_read"),
]