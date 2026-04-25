from django.contrib import admin

from .models import Account, LedgerEntry, Operation


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("public_number", "owner", "currency", "status", "balance_minor", "created_at")
    list_filter = ("currency", "status")
    search_fields = ("public_number", "owner__username", "owner__email")


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "status",
        "amount_minor",
        "currency",
        "from_account",
        "to_account",
        "created_by",
        "created_at",
    )
    list_filter = ("kind", "status", "currency")
    search_fields = ("id", "idempotency_key", "created_by__username", "created_by__email")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "operation", "account", "amount_minor", "created_at")
    list_filter = ("created_at",)
