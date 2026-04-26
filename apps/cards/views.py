from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import Card
from apps.cards.serializers import CardCreateSerializer, CardSerializer
from apps.cards.services import create_card_for_account, set_card_blocked
from apps.banking.services.exceptions import BankingError


class CardListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CardSerializer

    def get_queryset(self):
        return Card.objects.filter(account__owner=self.request.user).order_by("-created_at")


class CardCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = CardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            card = create_card_for_account(
                user=request.user,
                account_id=data["account_id"],
                daily_limit_minor=data.get("daily_limit_minor"),
            )
        except BankingError as e:
            raise ValidationError({"detail": str(e)})
        return Response(CardSerializer(card).data, status=status.HTTP_201_CREATED)


class CardBlockToggleView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, card_id: int):
        blocked = bool(request.data.get("blocked", True))
        try:
            card = set_card_blocked(user=request.user, card_id=card_id, blocked=blocked)
        except BankingError as e:
            raise ValidationError({"detail": str(e)})
        return Response(CardSerializer(card).data, status=status.HTTP_200_OK)
