from rest_framework import generics, permissions

from apps.notifications.models import NotificationEvent
from apps.notifications.serializers import NotificationEventSerializer


class NotificationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationEventSerializer

    def get_queryset(self):
        return NotificationEvent.objects.filter(user=self.request.user).order_by("-created_at")
