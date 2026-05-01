from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, UserSerializer
from .serializers_extra import ChangePasswordSerializer


@extend_schema(tags=["Users"])
class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


@extend_schema(tags=["Users"])
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Users"])
class ChangePasswordView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not request.user.check_password(old_password):
            raise ValidationError({"old_password": "Invalid password."})

        try:
            password_validation.validate_password(new_password, user=request.user)
        except DjangoValidationError as e:
            raise ValidationError({"new_password": e.messages})

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
