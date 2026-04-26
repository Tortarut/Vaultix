import hashlib

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from apps.open_banking.models import TPPClient


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class TPPHeaderAuthentication(authentication.BaseAuthentication):
    """
    Very simplified TPP auth:
    - X-TPP-Client-Id
    - X-TPP-Client-Secret
    """

    def authenticate(self, request):
        client_id = request.headers.get("X-TPP-Client-Id")
        client_secret = request.headers.get("X-TPP-Client-Secret")
        if not client_id or not client_secret:
            return None

        client = TPPClient.objects.filter(client_id=client_id).first()
        if client is None or client.status != TPPClient.Status.ACTIVE:
            raise AuthenticationFailed("Invalid TPP credentials.")

        if client.client_secret_hash != _hash_secret(client_secret):
            raise AuthenticationFailed("Invalid TPP credentials.")

        # user=None; client accessible via request.auth
        return (None, client)

