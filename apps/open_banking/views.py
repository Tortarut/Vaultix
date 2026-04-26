from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import BankingError
from apps.banking.services.transfer import transfer_between_accounts
from apps.notifications.services import emit_event
from apps.open_banking.auth import TPPHeaderAuthentication, _hash_secret
from apps.open_banking.models import Consent, TPPAccessLog, TPPClient
from apps.open_banking.permissions import IsTPPAuthenticated, _require_scope
from apps.open_banking.serializers import (
    ConsentCreateSerializer,
    ConsentSerializer,
    OBAccountSerializer,
    OBLedgerSerializer,
    OBPaymentInitiateSerializer,
)


class ConsentCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        s = ConsentCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        tpp = TPPClient.objects.filter(client_id=data["tpp_client_id"]).first()
        if tpp is None or tpp.status != TPPClient.Status.ACTIVE:
            raise ValidationError({"tpp_client_id": "TPP client not found."})

        accounts = list(
            Account.objects.filter(owner=request.user, id__in=data["account_ids"])
        )
        if len(accounts) != len(set(data["account_ids"])):
            raise ValidationError({"account_ids": "One or more accounts not found."})

        consent = Consent.objects.create(
            user=request.user,
            tpp_client=tpp,
            scopes=data["scopes"],
            status=Consent.Status.CREATED,
            expires_at=timezone.now() + timezone.timedelta(seconds=data["expires_in_seconds"]),
        )
        consent.accounts.set(accounts)

        return Response(ConsentSerializer(consent).data, status=status.HTTP_201_CREATED)


class ConsentAuthorizeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, consent_id):
        consent = Consent.objects.filter(id=consent_id, user=request.user).first()
        if consent is None:
            raise ValidationError({"detail": "Consent not found."})
        consent.status = Consent.Status.AUTHORIZED
        consent.authorized_at = timezone.now()
        consent.save(update_fields=["status", "authorized_at"])
        return Response(ConsentSerializer(consent).data, status=status.HTTP_200_OK)


class ConsentRevokeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, consent_id):
        consent = Consent.objects.filter(id=consent_id, user=request.user).first()
        if consent is None:
            raise ValidationError({"detail": "Consent not found."})
        consent.status = Consent.Status.REVOKED
        consent.revoked_at = timezone.now()
        consent.save(update_fields=["status", "revoked_at"])
        return Response(ConsentSerializer(consent).data, status=status.HTTP_200_OK)


class TPPClientCreateView(APIView):
    """
    Admin helper to create a TPP client. Returns the plain secret once.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        client_id = request.data.get("client_id")
        name = request.data.get("name") or "TPP"
        secret = request.data.get("client_secret")
        if not client_id or not secret:
            raise ValidationError({"detail": "client_id and client_secret are required."})

        if TPPClient.objects.filter(client_id=client_id).exists():
            raise ValidationError({"client_id": "Already exists."})

        client = TPPClient.objects.create(
            client_id=client_id,
            client_secret_hash=_hash_secret(secret),
            name=name,
            status=TPPClient.Status.ACTIVE,
        )
        return Response(
            {"client_id": client.client_id, "client_secret": secret, "name": client.name},
            status=status.HTTP_201_CREATED,
        )


class TPPBaseAPIView(APIView):
    authentication_classes = (TPPHeaderAuthentication,)
    permission_classes = (IsTPPAuthenticated,)

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            consent_id = request.query_params.get("consent_id") or request.data.get("consent_id")
        except Exception:
            consent_id = None
        consent = None
        if consent_id:
            consent = Consent.objects.filter(id=consent_id).first()

        tpp = request.auth
        if tpp is not None:
            TPPAccessLog.objects.create(
                tpp_client=tpp,
                consent=consent,
                method=request.method,
                path=request.path,
                ip=request.META.get("REMOTE_ADDR", ""),
                status_code=response.status_code,
            )
        return super().finalize_response(request, response, *args, **kwargs)


def _get_active_consent_for_tpp(*, consent_id, tpp_client: TPPClient) -> Consent:
    consent = Consent.objects.filter(id=consent_id, tpp_client=tpp_client).first()
    if consent is None:
        raise ValidationError({"consent_id": "Consent not found."})
    if not consent.is_active():
        raise ValidationError({"consent_id": "Consent is not active."})
    return consent


class TPPAccountsListView(TPPBaseAPIView):
    def get(self, request):
        consent_id = request.query_params.get("consent_id")
        if not consent_id:
            raise ValidationError({"consent_id": "Required."})

        consent = _get_active_consent_for_tpp(consent_id=consent_id, tpp_client=request.auth)
        _require_scope(consent, Consent.SCOPE_ACCOUNTS_READ)

        qs = consent.accounts.all().order_by("created_at")
        return Response(OBAccountSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class TPPAccountLedgerView(TPPBaseAPIView):
    def get(self, request, account_id):
        consent_id = request.query_params.get("consent_id")
        if not consent_id:
            raise ValidationError({"consent_id": "Required."})

        consent = _get_active_consent_for_tpp(consent_id=consent_id, tpp_client=request.auth)
        _require_scope(consent, Consent.SCOPE_TRANSACTIONS_READ)

        account = consent.accounts.filter(id=account_id).first()
        if account is None:
            raise ValidationError({"account_id": "Account not allowed by consent."})

        qs = LedgerEntry.objects.filter(account=account).order_by("-created_at")[:200]
        return Response(OBLedgerSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class TPPPaymentInitiateView(TPPBaseAPIView):
    def post(self, request):
        s = OBPaymentInitiateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        consent = _get_active_consent_for_tpp(
            consent_id=data["consent_id"], tpp_client=request.auth
        )
        _require_scope(consent, Consent.SCOPE_PAYMENTS_CREATE)

        from_account = consent.accounts.filter(id=data["from_account_id"]).first()
        if from_account is None:
            raise ValidationError({"from_account_id": "Account not allowed by consent."})

        to_account = Account.objects.filter(public_number=data["to_public_number"]).first()
        if to_account is None:
            raise ValidationError({"to_public_number": "Destination account not found."})

        idempotency_key = request.headers.get("Idempotency-Key")
        # Create PENDING operation. Settlement happens later via management command.
        existing = None
        if idempotency_key:
            existing = Operation.objects.filter(
                created_by=consent.user, idempotency_key=idempotency_key
            ).first()
        if existing:
            op = existing
        else:
            op = Operation.objects.create(
                kind=Operation.Kind.TPP_PAYMENT,
                status=Operation.Status.PENDING,
                currency=from_account.currency,
                amount_minor=data["amount_minor"],
                from_account=from_account,
                to_account=to_account,
                description=data.get("description", ""),
                created_by=consent.user,
                idempotency_key=idempotency_key,
                completed_at=None,
            )

        emit_event(
            user=consent.user,
            event_type="open_banking.payment.initiated",
            payload={"operation_id": str(op.id), "tpp_client_id": request.auth.client_id},
        )

        return Response({"operation_id": str(op.id), "status": op.status}, status=status.HTTP_201_CREATED)
