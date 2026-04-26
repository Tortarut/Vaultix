from rest_framework import serializers

from apps.banking.models import Account, LedgerEntry
from apps.open_banking.models import Consent


class ConsentCreateSerializer(serializers.Serializer):
    tpp_client_id = serializers.CharField(max_length=64)
    scopes = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    account_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    expires_in_seconds = serializers.IntegerField(min_value=60, max_value=60 * 60 * 24 * 30)


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = (
            "id",
            "tpp_client",
            "scopes",
            "status",
            "expires_at",
            "created_at",
            "authorized_at",
            "revoked_at",
        )
        read_only_fields = fields


class OBAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "public_number", "currency", "status", "balance_minor")
        read_only_fields = fields


class OBLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ("id", "operation", "amount_minor", "balance_after_minor", "created_at")
        read_only_fields = fields


class OBPaymentInitiateSerializer(serializers.Serializer):
    consent_id = serializers.UUIDField()
    from_account_id = serializers.UUIDField()
    to_public_number = serializers.CharField(max_length=32)
    amount_minor = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        # quick sanity for expiry param usage elsewhere
        return attrs

