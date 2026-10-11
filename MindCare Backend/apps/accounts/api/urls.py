"""URL routes for the accounts API, included under /api/v1/accounts/."""

from django.urls import path

from apps.accounts.api.views import (
    ClientIpDebugView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # TEMPORARY (NUM_PROXIES measurement): remove in the very next PR.
    path("debug/client-ip/", ClientIpDebugView.as_view(), name="debug-client-ip"),
]
