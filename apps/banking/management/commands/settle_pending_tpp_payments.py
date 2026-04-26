from django.core.management.base import BaseCommand

from apps.banking.models import Operation
from apps.banking.services.settlement import settle_pending_operation


class Command(BaseCommand):
    help = "Settle all pending TPP payments (demo command)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        limit = options["limit"]
        ops = list(
            Operation.objects.filter(
                kind=Operation.Kind.TPP_PAYMENT, status=Operation.Status.PENDING
            )
            .order_by("created_at")[:limit]
        )
        settled = 0
        for op in ops:
            settle_pending_operation(operation_id=op.id)
            settled += 1
        self.stdout.write(self.style.SUCCESS(f"Settled: {settled}"))

