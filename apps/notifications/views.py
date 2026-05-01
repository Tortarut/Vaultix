from rest_framework import generics, permissions

from drf_spectacular.utils import extend_schema

from apps.notifications.models import NotificationEvent
from apps.notifications.serializers import NotificationEventSerializer


@extend_schema(tags=["Notifications"])
class NotificationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationEventSerializer

    def get_queryset(self):
        return NotificationEvent.objects.filter(user=self.request.user).order_by("-created_at")
