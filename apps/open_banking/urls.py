from django.urls import path

from .views import (
    ConsentAuthorizeView,
    ConsentCreateView,
    ConsentRevokeView,
    TPPAccountLedgerView,
    TPPAccountsListView,
    TPPClientCreateView,
    TPPPaymentInitiateView,
)

urlpatterns = [
    # User-facing consent flow
    path("consents/", ConsentCreateView.as_view(), name="ob-consent-create"),
    path("consents/<uuid:consent_id>/authorize/", ConsentAuthorizeView.as_view(), name="ob-consent-authorize"),
    path("consents/<uuid:consent_id>/revoke/", ConsentRevokeView.as_view(), name="ob-consent-revoke"),
    # Admin helper
    path("admin/tpp-clients/", TPPClientCreateView.as_view(), name="ob-tpp-client-create"),
    # TPP-facing endpoints
    path("tpp/accounts/", TPPAccountsListView.as_view(), name="ob-tpp-accounts"),
    path("tpp/accounts/<uuid:account_id>/ledger/", TPPAccountLedgerView.as_view(), name="ob-tpp-ledger"),
    path("tpp/payments/", TPPPaymentInitiateView.as_view(), name="ob-tpp-payments"),
]

