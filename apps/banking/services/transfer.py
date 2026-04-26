from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.banking.models import Account, LedgerEntry, Operation

from .exceptions import InsufficientFunds, InvalidTransfer


def transfer_between_accounts(
    *,
    created_by,
    from_account_id,
    to_account_id,
    amount_minor: int,
    description: str = "",
    idempotency_key: str | None = None,
    kind: str = Operation.Kind.INTERNAL_TRANSFER,
) -> Operation:
    if amount_minor <= 0:
        raise InvalidTransfer("Amount must be positive.")
    if from_account_id == to_account_id:
        raise InvalidTransfer("Source and destination accounts must be different.")

    if idempotency_key:
        existing = Operation.objects.filter(
            created_by=created_by, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing

    with transaction.atomic():
        # Lock accounts in deterministic order to reduce deadlock risk.
        ids = sorted([from_account_id, to_account_id])
        locked = {
            a.id: a
            for a in Account.objects.select_for_update().filter(id__in=ids).select_related("owner")
        }
        if from_account_id not in locked or to_account_id not in locked:
            raise InvalidTransfer("Account not found.")

        src = locked[from_account_id]
        dst = locked[to_account_id]

        if src.status != Account.Status.ACTIVE or dst.status != Account.Status.ACTIVE:
            raise InvalidTransfer("Account is not active.")
        if src.currency != dst.currency:
            raise InvalidTransfer("Currency mismatch.")

        # Authorization: only owner can initiate outgoing transfer from the account.
        if src.owner_id != created_by.id:
            raise InvalidTransfer("Cannot transfer from account not owned by user.")

        if src.balance_minor < amount_minor:
            raise InsufficientFunds("Insufficient funds.")

        operation = Operation.objects.create(
            kind=kind,
            status=Operation.Status.COMPLETED,
            currency=src.currency,
            amount_minor=amount_minor,
            from_account=src,
            to_account=dst,
            description=description,
            created_by=created_by,
            idempotency_key=idempotency_key,
            completed_at=timezone.now(),
        )

        # Update balances using F() to keep DB-side arithmetic.
        Account.objects.filter(id=src.id).update(balance_minor=F("balance_minor") - amount_minor)
        Account.objects.filter(id=dst.id).update(balance_minor=F("balance_minor") + amount_minor)

        src.refresh_from_db(fields=["balance_minor"])
        dst.refresh_from_db(fields=["balance_minor"])

        LedgerEntry.objects.bulk_create(
            [
                LedgerEntry(
                    operation=operation,
                    account=src,
                    amount_minor=-amount_minor,
                    balance_after_minor=src.balance_minor,
                ),
                LedgerEntry(
                    operation=operation,
                    account=dst,
                    amount_minor=amount_minor,
                    balance_after_minor=dst.balance_minor,
                ),
            ]
        )

        return operation

