from apps.notifications.models import NotificationEvent


def emit_event(*, user=None, event_type: str, payload: dict | None = None) -> NotificationEvent:
    return NotificationEvent.objects.create(
        user=user,
        event_type=event_type,
        payload=payload or {},
    )

