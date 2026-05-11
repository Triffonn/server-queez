from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import Game
from .serializers import AdminGameListSerializer, AdminGameDetailSerializer


class AdminGameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f-]{36}'
    #permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return AdminGameListSerializer
        return AdminGameDetailSerializer

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        game = self.get_object()
        game.is_completed=True
        game.save()
        return Response({'is_completed': game.is_completed, 'uuid': game.uuid})

    @action(detail=True, methods=['post'])
    def not_completed(self, request, pk=None):
        game = self.get_object()
        game.is_completed = True
        game.save()
        return Response({'is_completed': game.is_completed, 'uuid': game.uuid})
# Create your views here.
