from rest_framework import serializers

from apps.notifications.models import NotificationEvent


class NotificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = ("id", "event_type", "payload", "status", "created_at", "processed_at")
        read_only_fields = fields

