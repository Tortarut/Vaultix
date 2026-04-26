from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "masked_pan", "account", "status", "daily_limit_minor", "created_at")
    list_filter = ("status",)
    search_fields = ("masked_pan", "account__public_number")
