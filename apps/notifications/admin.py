from django.contrib import admin

from .models import NotificationEvent


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "user", "status", "created_at", "processed_at")
    list_filter = ("event_type", "status")
    search_fields = ("event_type", "user__username", "user__email")
