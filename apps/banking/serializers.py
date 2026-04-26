from rest_framework import serializers

from apps.banking.models import Account, LedgerEntry, Operation


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            "id",
            "public_number",
            "currency",
            "status",
            "balance_minor",
            "created_at",
            "closed_at",
        )
        read_only_fields = fields


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "public_number", "currency", "status", "balance_minor", "created_at")
        read_only_fields = ("id", "public_number", "status", "balance_minor", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        return Account.objects.create(owner=request.user, **validated_data)


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = (
            "id",
            "operation",
            "account",
            "amount_minor",
            "balance_after_minor",
            "created_at",
        )
        read_only_fields = fields


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operation
        fields = (
            "id",
            "kind",
            "status",
            "currency",
            "amount_minor",
            "from_account",
            "to_account",
            "card",
            "description",
            "idempotency_key",
            "failure_reason",
            "created_at",
            "completed_at",
        )
        read_only_fields = fields


class TransferCreateSerializer(serializers.Serializer):
    from_account_id = serializers.UUIDField()
    to_account_id = serializers.UUIDField()
    card_id = serializers.IntegerField(required=False)
    amount_minor = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class P2PCreateSerializer(serializers.Serializer):
    from_account_id = serializers.UUIDField()
    to_public_number = serializers.CharField(max_length=32)
    card_id = serializers.IntegerField(required=False)
    amount_minor = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class TopUpCreateSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

