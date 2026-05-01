from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()

STRONG_PASSWORD = "Str0ng-Pass_12345!"

class UsersApiTests(APITestCase):
    def test_register_and_token_and_me(self):
        r = self.client.post(
            "/api/v1/users/register/",
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": STRONG_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "alice", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(t.status_code, 200)
        access = t.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get("/api/v1/users/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "alice@example.com")

    def test_change_password(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password=STRONG_PASSWORD
        )

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "bob", "password": STRONG_PASSWORD},
            format="json",
        )
        access = t.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        r = self.client.post(
            "/api/v1/users/password/change/",
            {"old_password": STRONG_PASSWORD, "new_password": "An0ther-Str0ngPass_67890!"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

        # Old password should no longer work.
        t2 = self.client.post(
            "/api/v1/users/token/",
            {"username": "bob", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(t2.status_code, 401)

        # New password should work.
        t3 = self.client.post(
            "/api/v1/users/token/",
            {"username": "bob", "password": "An0ther-Str0ngPass_67890!"},
            format="json",
        )
        self.assertEqual(t3.status_code, 200)

    def test_token_refresh(self):
        User.objects.create_user(
            username="alice", email="alice@example.com", password=STRONG_PASSWORD
        )

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "alice", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(t.status_code, 200)
        refresh = t.data["refresh"]

        r = self.client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
