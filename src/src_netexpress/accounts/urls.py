from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
    path("password-setup/<uidb64>/<token>/", views.password_setup, name="password_setup"),
    path("password-change/", views.password_change, name="password_change"),
    path("password-change/done/", views.password_change_done, name="password_change_done"),
]
