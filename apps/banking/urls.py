from django.urls import path

from .views import (
    AccountDetailView,
    AccountLedgerView,
    AccountListCreateView,
    P2PCreateView,
    TransferCreateView,
)

urlpatterns = [
    path("accounts/", AccountListCreateView.as_view(), name="accounts"),
    path("accounts/<uuid:pk>/", AccountDetailView.as_view(), name="account-detail"),
    path(
        "accounts/<uuid:account_id>/ledger/",
        AccountLedgerView.as_view(),
        name="account-ledger",
    ),
    path("transfers/", TransferCreateView.as_view(), name="transfer-create"),
    path("p2p/", P2PCreateView.as_view(), name="p2p-create"),
]

