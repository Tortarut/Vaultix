from rest_framework import serializers

from apps.cards.models import Card


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = (
            "id",
            "account",
            "masked_pan",
            "status",
            "daily_limit_minor",
            "created_at",
            "blocked_at",
        )
        read_only_fields = fields


class CardCreateSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    daily_limit_minor = serializers.IntegerField(min_value=1, required=False)


class CardBlockToggleSerializer(serializers.Serializer):
    blocked = serializers.BooleanField(required=False, default=True)

