from django.db import models

from apps.banking.models import Account


class Card(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"
        EXPIRED = "EXPIRED", "Expired"

    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="cards"
    )
    masked_pan = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    daily_limit_minor = models.BigIntegerField(default=100_000_00)
    created_at = models.DateTimeField(auto_now_add=True)
    blocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["account", "status"])]

    def __str__(self) -> str:
        return f"{self.masked_pan} ({self.status})"
