from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from apps.open_banking.models import Consent


def _require_scope(consent: Consent, scope: str):
    if scope not in (consent.scopes or []):
        raise PermissionDenied(f"Missing required scope: {scope}")


class IsTPPAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None

