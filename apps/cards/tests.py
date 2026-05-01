from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.banking.models import Account
from apps.cards.models import Card


User = get_user_model()
STRONG_PASSWORD = "Str0ng-Pass_12345!"


class CardsApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password=STRONG_PASSWORD
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password=STRONG_PASSWORD
        )
        self.a1 = Account.objects.create(owner=self.alice, balance_minor=0)
        self.b1 = Account.objects.create(owner=self.bob, balance_minor=0)

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "alice", "password": STRONG_PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.data['access']}")

    def test_create_and_list_and_block(self):
        r = self.client.post(
            "/api/v1/cards/create/",
            {"account_id": str(self.a1.id), "daily_limit_minor": 1000},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        card_id = r.data["id"]
        self.assertTrue(Card.objects.filter(id=card_id).exists())

        lst = self.client.get("/api/v1/cards/")
        self.assertEqual(lst.status_code, 200)
        self.assertTrue(any(c["id"] == card_id for c in lst.data["results"]))

        blk = self.client.post(
            f"/api/v1/cards/{card_id}/block/",
            {"blocked": True},
            format="json",
        )
        self.assertEqual(blk.status_code, 200)
        self.assertEqual(blk.data["status"], Card.Status.BLOCKED)

        unblk = self.client.post(
            f"/api/v1/cards/{card_id}/block/",
            {"blocked": False},
            format="json",
        )
        self.assertEqual(unblk.status_code, 200)
        self.assertEqual(unblk.data["status"], Card.Status.ACTIVE)

    def test_cannot_create_card_for_foreign_account(self):
        r = self.client.post(
            "/api/v1/cards/create/",
            {"account_id": str(self.b1.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_cannot_block_foreign_card(self):
        foreign_card = Card.objects.create(
            account=self.b1, masked_pan="4000 **** **** 9999", daily_limit_minor=1000
        )
        r = self.client.post(
            f"/api/v1/cards/{foreign_card.id}/block/",
            {"blocked": True},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
