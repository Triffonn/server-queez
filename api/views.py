from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Game, QuestionType
from api.serializers import GameSerializer, GameListSerializer, QuestionTypeSerializer


class GameViewSet(viewsets.ModelViewSet):
    serializer_class = GameSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Game.objects.all().order_by('-created_at')
        if self.action == 'list':
            queryset = queryset.annotate(
                rounds_count=Count('rounds', distinct=True),
                questions_count=Count('rounds__questions', distinct=True)
            )
        elif self.action == 'retrieve':
            return queryset.prefetch_related('rounds__questions__question_type')
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'full'):
            return GameSerializer
        else:
            return GameListSerializer

    @action(detail=True,methods=['get'])
    def full(self,request,uuid=None):
        game = self.get_object()
        serializer =self.get_serializer(game)
        return Response(serializer.data)

class QuestionTypeViewSet(viewsets.ModelViewSet):
    queryset = QuestionType.objects.all()
    serializer_class = QuestionTypeSerializer