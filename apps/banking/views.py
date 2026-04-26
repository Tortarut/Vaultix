from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import BankingError
from apps.banking.services.transfer import transfer_between_accounts

from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    LedgerEntrySerializer,
    OperationSerializer,
    P2PCreateSerializer,
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
        return LedgerEntry.objects.filter(account=account).order_by("-created_at")


class TransferCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idempotency_key = request.headers.get("Idempotency-Key")

        try:
            op = transfer_between_accounts(
                created_by=request.user,
                from_account_id=data["from_account_id"],
                to_account_id=data["to_account_id"],
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
                amount_minor=data["amount_minor"],
                description=data.get("description", ""),
                idempotency_key=idempotency_key,
                kind=Operation.Kind.P2P,
            )
        except BankingError as e:
            raise ValidationError({"detail": str(e)})

        return Response(OperationSerializer(op).data, status=status.HTTP_201_CREATED)
