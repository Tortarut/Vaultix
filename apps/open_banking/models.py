import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.banking.models import Account


class TPPClient(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        REVOKED = "REVOKED", "Revoked"

    id = models.BigAutoField(primary_key=True)
    client_id = models.CharField(max_length=64, unique=True)
    client_secret_hash = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.client_id})"


class Consent(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        REVOKED = "REVOKED", "Revoked"
        EXPIRED = "EXPIRED", "Expired"

    SCOPE_ACCOUNTS_READ = "ACCOUNTS_READ"
    SCOPE_TRANSACTIONS_READ = "TRANSACTIONS_READ"
    SCOPE_PAYMENTS_CREATE = "PAYMENTS_CREATE"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="consents"
    )
    tpp_client = models.ForeignKey(
        TPPClient, on_delete=models.PROTECT, related_name="consents"
    )
    scopes = models.JSONField(default=list)
    accounts = models.ManyToManyField(Account, related_name="consents", blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CREATED
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["tpp_client", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_active(self) -> bool:
        if self.status != Consent.Status.AUTHORIZED:
            return False
        return self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"{self.id} ({self.status})"


class TPPAccessLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tpp_client = models.ForeignKey(TPPClient, on_delete=models.PROTECT)
    consent = models.ForeignKey(Consent, on_delete=models.PROTECT, null=True, blank=True)
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=255)
    ip = models.CharField(max_length=64, blank=True)
    status_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tpp_client", "created_at"])]

    def __str__(self) -> str:
        return f"{self.tpp_client_id} {self.method} {self.path} {self.status_code}"


