from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.WorkerDashboardView.as_view(), name="worker_dashboard"),
    path("list/", views.TaskListView.as_view(), name="list"),
    path("calendar/", views.TaskCalendarView.as_view(), name="calendar"),
    path("schedule/", views.WorkerScheduleView.as_view(), name="worker_schedule"),
    path("events/", views.task_events, name="events"),
    path("worker-events/", views.worker_task_events, name="worker_events"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="detail"),
    path("<int:pk>/complete/", views.TaskCompleteView.as_view(), name="complete"),
]
