from django.urls import include, path

urlpatterns = [
    path("users/", include("apps.users.urls")),
    path("banking/", include("apps.banking.urls")),
    path("cards/", include("apps.cards.urls")),
    path("open-banking/", include("apps.open_banking.urls")),
    path("notifications/", include("apps.notifications.urls")),
]

