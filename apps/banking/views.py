from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.adjustments import topup_account
from apps.banking.services.exceptions import BankingError
from apps.banking.services.transfer import transfer_between_accounts

from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    LedgerEntrySerializer,
    OperationSerializer,
    P2PCreateSerializer,
    TopUpCreateSerializer,
    TransferCreateSerializer,
)


class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Account.objects.filter(owner=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AccountCreateSerializer
        return AccountSerializer


class AccountDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(owner=self.request.user)


class AccountLedgerView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = LedgerEntrySerializer

    def get_queryset(self):
        account = get_object_or_404(
            Account.objects.filter(owner=self.request.user), id=self.kwargs["account_id"]
        )
        qs = LedgerEntry.objects.filter(account=account)
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            dt = parse_datetime(date_from)
            if dt is None:
                raise ValidationError({"date_from": "Invalid ISO-8601 datetime."})
            qs = qs.filter(created_at__gte=dt)
        if date_to:
            dt = parse_datetime(date_to)
            if dt is None:
                raise ValidationError({"date_to": "Invalid ISO-8601 datetime."})
            qs = qs.filter(created_at__lte=dt)
        return qs.order_by("-created_at")


class OperationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OperationSerializer

    def get_queryset(self):
        qs = Operation.objects.filter(created_by=self.request.user)
        status_param = self.request.query_params.get("status")
        kind_param = self.request.query_params.get("kind")
        if status_param:
            qs = qs.filter(status=status_param)
        if kind_param:
            qs = qs.filter(kind=kind_param)
        return qs.order_by("-created_at")


class OperationDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OperationSerializer

    def get_queryset(self):
        return Operation.objects.filter(created_by=self.request.user)


class TransferCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not Account.objects.filter(id=data["to_account_id"], owner=request.user).exists():
            raise ValidationError(
                {
                    "to_account_id": "Destination account must belong to the current user. Use P2P for external transfers."
                }
            )

        idempotency_key = request.headers.get("Idempotency-Key")

        try:
            op = transfer_between_accounts(
                created_by=request.user,
                from_account_id=data["from_account_id"],
                to_account_id=data["to_account_id"],
                card_id=data.get("card_id"),
                amount_minor=data["amount_minor"],
                description=data.get("description", ""),
                idempotency_key=idempotency_key,
            )
        except BankingError as e:
            raise ValidationError({"detail": str(e)})

        return Response(OperationSerializer(op).data, status=status.HTTP_201_CREATED)


class P2PCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = P2PCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dst = Account.objects.filter(public_number=data["to_public_number"]).first()
        if dst is None:
            raise ValidationError({"to_public_number": "Destination account not found."})

        idempotency_key = request.headers.get("Idempotency-Key")

        try:
            op = transfer_between_accounts(
                created_by=request.user,
                from_account_id=data["from_account_id"],
                to_account_id=dst.id,
                card_id=data.get("card_id"),
                amount_minor=data["amount_minor"],
                description=data.get("description", ""),
                idempotency_key=idempotency_key,
                kind=Operation.Kind.P2P,
            )
        except BankingError as e:
            raise ValidationError({"detail": str(e)})

        return Response(OperationSerializer(op).data, status=status.HTTP_201_CREATED)


class TopUpView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        serializer = TopUpCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            op = topup_account(
                created_by=request.user,
                account_id=data["account_id"],
                amount_minor=data["amount_minor"],
                description=data.get("description") or "Top-up",
            )
        except BankingError as e:
            raise ValidationError({"detail": str(e)})

        return Response(OperationSerializer(op).data, status=status.HTTP_201_CREATED)
