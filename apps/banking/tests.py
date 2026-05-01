from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import InsufficientFunds, InvalidTransfer
from apps.banking.services.transfer import transfer_between_accounts
from rest_framework.test import APITestCase
from apps.cards.models import Card


User = get_user_model()
STRONG_PASSWORD = "Str0ng-Pass_12345!"


class TransferServiceTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password=STRONG_PASSWORD
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password=STRONG_PASSWORD
        )

        self.a1 = Account.objects.create(owner=self.alice, balance_minor=100_00)
        self.a2 = Account.objects.create(owner=self.alice, balance_minor=0)
        self.b1 = Account.objects.create(owner=self.bob, balance_minor=0)

    def test_success_internal_transfer(self):
        op = transfer_between_accounts(
            created_by=self.alice,
            from_account_id=self.a1.id,
            to_account_id=self.a2.id,
            amount_minor=25_00,
            description="test",
        )

        self.assertEqual(op.status, Operation.Status.COMPLETED)
        self.a1.refresh_from_db()
        self.a2.refresh_from_db()

        self.assertEqual(self.a1.balance_minor, 75_00)
        self.assertEqual(self.a2.balance_minor, 25_00)

        entries = LedgerEntry.objects.filter(operation=op).order_by("amount_minor")
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].account_id, self.a1.id)
        self.assertEqual(entries[0].amount_minor, -25_00)
        self.assertEqual(entries[1].account_id, self.a2.id)
        self.assertEqual(entries[1].amount_minor, 25_00)

    def test_insufficient_funds(self):
        with self.assertRaises(InsufficientFunds):
            transfer_between_accounts(
                created_by=self.alice,
                from_account_id=self.a1.id,
                to_account_id=self.a2.id,
                amount_minor=999_00,
            )

    def test_cannot_transfer_from_foreign_account(self):
        with self.assertRaises(InvalidTransfer):
            transfer_between_accounts(
                created_by=self.alice,
                from_account_id=self.b1.id,
                to_account_id=self.a1.id,
                amount_minor=1_00,
            )

    def test_idempotency_key_returns_same_operation(self):
        op1 = transfer_between_accounts(
            created_by=self.alice,
            from_account_id=self.a1.id,
            to_account_id=self.a2.id,
            amount_minor=10_00,
            idempotency_key="k1",
        )
        op2 = transfer_between_accounts(
            created_by=self.alice,
            from_account_id=self.a1.id,
            to_account_id=self.a2.id,
            amount_minor=10_00,
            idempotency_key="k1",
        )
        self.assertEqual(op1.id, op2.id)
        self.assertEqual(
            Operation.objects.filter(created_by=self.alice, idempotency_key="k1").count(), 1
        )


class BankingApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password=STRONG_PASSWORD
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password=STRONG_PASSWORD
        )
        self.a1 = Account.objects.create(owner=self.alice, balance_minor=100_00)
        self.a2 = Account.objects.create(owner=self.alice, balance_minor=0)
        self.b1 = Account.objects.create(owner=self.bob, balance_minor=0)

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "alice", "password": STRONG_PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.data['access']}")

    def test_transfers_only_to_own_accounts(self):
        r = self.client.post(
            "/api/v1/banking/transfers/",
            {
                "from_account_id": str(self.a1.id),
                "to_account_id": str(self.b1.id),
                "amount_minor": 1,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_ledger_date_validation(self):
        r = self.client.get(f"/api/v1/banking/accounts/{self.a1.id}/ledger/?date_from=bad")
        self.assertEqual(r.status_code, 400)

    def test_p2p_transfer_by_public_number(self):
        r = self.client.post(
            "/api/v1/banking/p2p/",
            {
                "from_account_id": str(self.a1.id),
                "to_public_number": self.b1.public_number,
                "amount_minor": 10_00,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.a1.refresh_from_db()
        self.b1.refresh_from_db()
        self.assertEqual(self.a1.balance_minor, 90_00)
        self.assertEqual(self.b1.balance_minor, 10_00)

    def test_operation_detail_only_owner(self):
        op = transfer_between_accounts(
            created_by=self.alice,
            from_account_id=self.a1.id,
            to_account_id=self.a2.id,
            amount_minor=1_00,
        )

        t = self.client.post(
            "/api/v1/users/token/",
            {"username": "bob", "password": STRONG_PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.data['access']}")

        r = self.client.get(f"/api/v1/banking/operations/{op.id}/")
        self.assertEqual(r.status_code, 404)

    def test_card_daily_limit_enforced(self):
        card = Card.objects.create(
            account=self.a1, masked_pan="4000 **** **** 0001", daily_limit_minor=5_00
        )
        r = self.client.post(
            "/api/v1/banking/transfers/",
            {
                "from_account_id": str(self.a1.id),
                "to_account_id": str(self.a2.id),
                "card_id": card.id,
                "amount_minor": 6_00,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)
