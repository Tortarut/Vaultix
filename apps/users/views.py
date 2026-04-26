from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            raise ValidationError({"detail": "old_password and new_password are required."})

        if not request.user.check_password(old_password):
            raise ValidationError({"old_password": "Invalid password."})

        try:
            password_validation.validate_password(new_password, user=request.user)
        except DjangoValidationError as e:
            raise ValidationError({"new_password": e.messages})

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
