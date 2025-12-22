from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    # Email messaging (existing)
    path("compose/", views.compose, name="compose"),
    path("", views.MessageListView.as_view(), name="list"),
    path("<int:pk>/", views.MessageDetailView.as_view(), name="detail"),
    
    # Internal messaging system
    path("internal/", views.InternalMessageListView.as_view(), name="internal_list"),
    path("internal/compose/", views.InternalMessageComposeView.as_view(), name="internal_compose"),
    path("internal/<int:pk>/", views.InternalMessageDetailView.as_view(), name="internal_detail"),
    path("threads/", views.MessageThreadListView.as_view(), name="thread_list"),
    
    # AJAX endpoints
    path("reply/<int:message_id>/", views.message_reply, name="message_reply"),
    path("mark-read/<int:message_id>/", views.mark_message_read, name="mark_read"),
]
