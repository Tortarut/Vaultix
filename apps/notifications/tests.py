from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.notifications.models import NotificationEvent
from apps.notifications.services import emit_event


User = get_user_model()
STRONG_PASSWORD = "Str0ng-Pass_12345!"


class NotificationsTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password=STRONG_PASSWORD
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password=STRONG_PASSWORD
        )

        emit_event(user=self.alice, event_type="test.a", payload={"x": 1})
        emit_event(user=self.bob, event_type="test.b", payload={"x": 2})

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "alice", "password": STRONG_PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.data['access']}")

    def test_list_returns_only_own_events(self):
        r = self.client.get("/api/v1/notifications/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["event_type"], "test.a")
        self.assertEqual(NotificationEvent.objects.count(), 2)

    def test_requires_authentication(self):
        self.client.credentials()
        r = self.client.get("/api/v1/notifications/")
        self.assertEqual(r.status_code, 401)
