import random

from django.db import transaction
from django.utils import timezone

from apps.banking.models import Account
from apps.banking.services.exceptions import InvalidTransfer
from apps.cards.models import Card
from apps.notifications.services import emit_event


def _generate_masked_pan() -> str:
    last4 = random.randint(0, 9999)
    return f"4000 **** **** {last4:04d}"


def create_card_for_account(*, user, account_id, daily_limit_minor: int | None = None) -> Card:
    with transaction.atomic():
        account = (
            Account.objects.select_for_update()
            .select_related("owner")
            .filter(id=account_id)
            .first()
        )
        if account is None:
            raise InvalidTransfer("Account not found.")
        if account.owner_id != user.id:
            raise InvalidTransfer("Account not owned by user.")
        if account.status != Account.Status.ACTIVE:
            raise InvalidTransfer("Account is not active.")

        card = Card.objects.create(
            account=account,
            masked_pan=_generate_masked_pan(),
            daily_limit_minor=daily_limit_minor or Card._meta.get_field("daily_limit_minor").default,
        )

        emit_event(
            user=user,
            event_type="cards.created",
            payload={"card_id": card.id, "account_id": str(account.id)},
        )
        return card


def set_card_blocked(*, user, card_id: int, blocked: bool) -> Card:
    with transaction.atomic():
        card = (
            Card.objects.select_for_update()
            .select_related("account", "account__owner")
            .filter(id=card_id)
            .first()
        )
        if card is None:
            raise InvalidTransfer("Card not found.")
        if card.account.owner_id != user.id:
            raise InvalidTransfer("Card not owned by user.")

        if blocked:
            card.status = Card.Status.BLOCKED
            card.blocked_at = timezone.now()
            event = "cards.blocked"
        else:
            card.status = Card.Status.ACTIVE
            card.blocked_at = None
            event = "cards.unblocked"
        card.save(update_fields=["status", "blocked_at"])

        emit_event(
            user=user,
            event_type=event,
            payload={"card_id": card.id, "account_id": str(card.account_id)},
        )
        return card

