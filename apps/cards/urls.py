from django.urls import path

from .views import CardBlockToggleView, CardCreateView, CardListView

urlpatterns = [
    path("", CardListView.as_view(), name="card-list"),
    path("create/", CardCreateView.as_view(), name="card-create"),
    path("<int:card_id>/block/", CardBlockToggleView.as_view(), name="card-block"),
]

