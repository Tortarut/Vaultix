from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import InsufficientFunds, InvalidTransfer
from apps.banking.services.transfer import transfer_between_accounts


User = get_user_model()


class TransferServiceTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password="password12345"
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password="password12345"
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
