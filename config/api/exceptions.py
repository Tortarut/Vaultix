from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """
    Unified API error shape.

    Success responses stay DRF-native; errors follow:
    {
      "error": {
        "code": "...",
        "detail": "...",
        "fields": {...}  # optional
      }
    }
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return Response(
            {"error": {"code": "server_error", "detail": "Internal server error."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = "Request failed."
    fields: Any | None = None

    if isinstance(response.data, dict):
        if "detail" in response.data:
            detail = str(response.data["detail"])
        else:
            fields = response.data
            detail = "Validation error."
    else:
        detail = str(response.data)

    code = "validation_error" if response.status_code == 400 else "api_error"
    payload: dict[str, Any] = {"error": {"code": code, "detail": detail}}
    if fields is not None:
        payload["error"]["fields"] = fields

    response.data = payload
    return response

