from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.banking.models import Account, LedgerEntry, Operation
from apps.banking.services.exceptions import InsufficientFunds, InvalidTransfer
from apps.notifications.services import emit_event


def settle_pending_operation(*, operation_id) -> Operation:
    with transaction.atomic():
        op = (
            Operation.objects.select_for_update()
            .select_related("from_account", "to_account", "created_by")
            .filter(id=operation_id)
            .first()
        )
        if op is None:
            raise InvalidTransfer("Operation not found.")
        if op.status != Operation.Status.PENDING:
            return op
        if op.from_account_id is None or op.to_account_id is None:
            raise InvalidTransfer("Operation accounts not set.")

        ids = sorted([op.from_account_id, op.to_account_id])
        locked = {a.id: a for a in Account.objects.select_for_update().filter(id__in=ids)}
        src = locked[op.from_account_id]
        dst = locked[op.to_account_id]

        if src.status != Account.Status.ACTIVE or dst.status != Account.Status.ACTIVE:
            op.status = Operation.Status.FAILED
            op.failure_reason = "Account is not active."
            op.save(update_fields=["status", "failure_reason"])
            return op

        if src.currency != dst.currency or op.currency != src.currency:
            op.status = Operation.Status.FAILED
            op.failure_reason = "Currency mismatch."
            op.save(update_fields=["status", "failure_reason"])
            return op

        if src.balance_minor < op.amount_minor:
            raise InsufficientFunds("Insufficient funds.")

        Account.objects.filter(id=src.id).update(balance_minor=F("balance_minor") - op.amount_minor)
        Account.objects.filter(id=dst.id).update(balance_minor=F("balance_minor") + op.amount_minor)
        src.refresh_from_db(fields=["balance_minor"])
        dst.refresh_from_db(fields=["balance_minor"])

        LedgerEntry.objects.bulk_create(
            [
                LedgerEntry(
                    operation=op,
                    account=src,
                    amount_minor=-op.amount_minor,
                    balance_after_minor=src.balance_minor,
                ),
                LedgerEntry(
                    operation=op,
                    account=dst,
                    amount_minor=op.amount_minor,
                    balance_after_minor=dst.balance_minor,
                ),
            ]
        )

        op.status = Operation.Status.COMPLETED
        op.completed_at = timezone.now()
        op.save(update_fields=["status", "completed_at"])

        emit_event(
            user=op.created_by,
            event_type="banking.operation.settled",
            payload={"operation_id": str(op.id), "kind": op.kind},
        )

        return op

