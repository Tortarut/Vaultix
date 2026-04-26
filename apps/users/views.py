from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

from django.shortcuts import render

# Create your views here.
