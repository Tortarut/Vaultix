from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("id",)
    list_display = ("username", "email", "kyc_status", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (_("Banking"), {"fields": ("kyc_status",)}),
    )
