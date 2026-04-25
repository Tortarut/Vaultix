from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def generate_public_account_number() -> str:
    return f"VX{uuid.uuid4().hex[:20].upper()}"


class Account(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"
        CLOSED = "CLOSED", "Closed"

    class Currency(models.TextChoices):
        RUB = "RUB", "RUB"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="accounts"
    )
    public_number = models.CharField(
        max_length=32, unique=True, default=generate_public_account_number
    )
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.RUB
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    balance_minor = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["public_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.public_number} ({self.owner_id})"


class Operation(models.Model):
    class Kind(models.TextChoices):
        INTERNAL_TRANSFER = "INTERNAL_TRANSFER", "Internal transfer"
        P2P = "P2P", "P2P"
        TPP_PAYMENT = "TPP_PAYMENT", "TPP payment"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )

    currency = models.CharField(max_length=3, default=Account.Currency.RUB)
    amount_minor = models.BigIntegerField()

    from_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="outgoing_operations",
        null=True,
        blank=True,
    )
    to_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="incoming_operations",
        null=True,
        blank=True,
    )

    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="operations"
    )

    idempotency_key = models.CharField(max_length=128, null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"],
                condition=~models.Q(idempotency_key=None),
                name="uniq_operation_idempotency_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount_minor} {self.currency} ({self.status})"


class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation = models.ForeignKey(
        Operation, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    amount_minor = models.BigIntegerField()
    balance_after_minor = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["operation"]),
        ]

    def __str__(self) -> str:
        return f"{self.account_id}: {self.amount_minor}"
