from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("calendar/", views.TaskCalendarView.as_view(), name="calendar"),
    path("events/", views.task_events, name="events"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="detail"),
]
