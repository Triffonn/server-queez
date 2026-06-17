from django.db.models import Count
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Game, QuestionType, Round
from api.serializers import GameSerializer, GameListSerializer, QuestionTypeSerializer, RoundSerializer


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

class RoundViewSet(viewsets.ModelViewSet):
    serializer_class = RoundSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Round.objects.all()
        game_uuid = self.request.query_params.get('game_id', None)
        if self.action == 'list':
            if not game_uuid:
                return Round.objects.none()
            return queryset.filter(game__uuid=game_uuid)
        return queryset

    def create(self, request, *args, **kwargs):
        # Достаём game_uuid из query params
        game_uuid = request.query_params.get('game_id',None)
        if not game_uuid:
            return Response({'error': 'game_id обязателен в query params'},status=status.HTTP_400_BAD_REQUEST)
        try:
            game = Game.objects.get(uuid=game_uuid)
        except Game.DoesNotExist:
            return Response({'error': f'Игра с uuid {game_uuid} не найдена'},status=status.HTTP_404_NOT_FOUND)
        # Передаём обновленные данные сериализатору
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(game=game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)