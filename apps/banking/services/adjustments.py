from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import InvalidTransfer
from apps.notifications.services import emit_event


def topup_account(
    *,
    created_by,
    account_id,
    amount_minor: int,
    description: str = "Top-up",
) -> Operation:
    if amount_minor <= 0:
        raise InvalidTransfer("Amount must be positive.")

    with transaction.atomic():
        account = (
            Account.objects.select_for_update()
            .select_related("owner")
            .filter(id=account_id)
            .first()
        )
        if account is None:
            raise InvalidTransfer("Account not found.")
        if account.status != Account.Status.ACTIVE:
            raise InvalidTransfer("Account is not active.")

        operation = Operation.objects.create(
            kind=Operation.Kind.ADJUSTMENT,
            status=Operation.Status.COMPLETED,
            currency=account.currency,
            amount_minor=amount_minor,
            from_account=None,
            to_account=account,
            description=description,
            created_by=created_by,
            completed_at=timezone.now(),
        )

        Account.objects.filter(id=account.id).update(
            balance_minor=F("balance_minor") + amount_minor
        )
        account.refresh_from_db(fields=["balance_minor"])

        LedgerEntry.objects.create(
            operation=operation,
            account=account,
            amount_minor=amount_minor,
            balance_after_minor=account.balance_minor,
        )

        emit_event(
            user=account.owner,
            event_type="banking.topup.completed",
            payload={
                "operation_id": str(operation.id),
                "amount_minor": operation.amount_minor,
                "currency": operation.currency,
                "account_id": str(account.id),
            },
        )

        return operation

