from django.db.models import Count, F
from django.db import transaction
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.contenttypes.models import ContentType
from api.models import Game, Question, QuestionType, Round,Answer,Media,MediaType,MediaTimeUsing
from api.serializers import GameSerializer, GameListSerializer, MediaSerializer, MediaTimeUsingSerializer, MediaTypeSerializer, QuestionWriteSerializer, RoundSerializer,QuestionTypeSerializer


class GameViewSet(viewsets.ModelViewSet):
    serializer_class = GameSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Game.objects.all().order_by('-created_at')
        if self.action == 'list':
            is_complited = self.request.query_params.get('is_completed', None)
            if is_complited is not None:
                queryset = queryset.filter(is_completed=is_complited.lower() == 'true')
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

class MediaTimeUsingViewSet(viewsets.ModelViewSet):
    queryset = MediaTimeUsing.objects.all()
    serializer_class = MediaTimeUsingSerializer

class MediaTypeViewSet(viewsets.ModelViewSet):
    queryset = MediaType.objects.all()
    serializer_class = MediaTypeSerializer

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

    def perform_destroy(self, instance):
        with transaction.atomic():
            game = instance.game
            order = instance.order
            instance.delete()
            Round.objects.filter(game=game, order__gt=order).update(order=F('order') - 1)

    @action(detail=False, methods=['post'],url_path='reorder')
    def reorder(self, request):
        game_uuid = request.query_params.get('game_id', None)
        if not game_uuid:
            return Response({'error': 'game_id обязателен в query params'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game = Game.objects.get(uuid=game_uuid)
        except Game.DoesNotExist:
            return Response({'error': f'Игра с uuid {game_uuid} не найдена'}, status=status.HTTP_404_NOT_FOUND)

        new_order = request.data.get('order')
        if not isinstance(new_order, list):
            return Response({'error': 'Ожидается список uuid раундов в поле order'}, status=status.HTTP_400_BAD_REQUEST)

        rounds =  {str(r.uuid): r for r in Round.objects.filter(game=game)}
        if set(new_order) != set(rounds.keys()):
            return Response({'error': 'Список order должен содержать все раунды игры без пропусков и дублей'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # проход 1: временные значения, чтобы не столкнуться с unique_together('game','order')
            for r in rounds.values():
                r.order = r.order + 100000
                r.save(update_fields=['order'])
            # проход 2: финальные значения по присланному порядку
            for index, uuid_str in enumerate(new_order):
                r = rounds[uuid_str]
                r.order = index
                r.save(update_fields=['order'])
        queryset = Round.objects.filter(game=game).order_by('order')
        serializer = RoundSerializer(queryset, many=True)
        return Response(serializer.data)

class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionWriteSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Question.objects.all()
        round_uuid = self.request.query_params.get('round_id', None)
        if self.action == 'list':
            if not round_uuid:
                return Question.objects.none()
            return queryset.filter(round__uuid=round_uuid)
        return queryset
    
    def create(self, request, *args, **kwargs):
        # Достаём game_uuid из query params
        round_uuid = request.query_params.get('round_id',None)
        if not round_uuid:
            return Response({'error': 'round_id обязателен в query params'},status=status.HTTP_400_BAD_REQUEST)
        try:
            round = Round.objects.get(uuid=round_uuid)
        except Round.DoesNotExist:
            return Response({'error': f'Round с uuid {round_uuid} не найден'},status=status.HTTP_404_NOT_FOUND)
        # Передаём обновленные данные сериализатору
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(round=round)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        with transaction.atomic():
            round_obj = instance.round
            order = instance.order
            instance.delete()
            Question.objects.filter(round=round_obj, order__gt=order).update(order=F('order') - 1)

class MediaViewSet(viewsets.ModelViewSet):
    serializer_class = MediaSerializer
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'uuid'

    PARENT_PARAM_MODELS = {
        'round_id': Round,
        'question_id': Question,
        'answer_id': Answer,
        'game_id': Game,
    }

    def _resolve_parent(self):
        matches = [(p, m) for p, m in self.PARENT_PARAM_MODELS.items() if self.request.query_params.get(p)]
        if len(matches) != 1:
            return None, None
        param, model = matches[0]
        value = self.request.query_params.get(param)
        lookup = {'uuid': value} if model is not Answer else {'pk': value}
        try:
            return model, model.objects.get(**lookup)
        except model.DoesNotExist:
            return model, None

    def get_queryset(self):
        if self.action != 'list':
            return Media.objects.all()
        model, obj = self._resolve_parent()
        if not model or not obj:
            return Media.objects.none()
        ct = ContentType.objects.get_for_model(model)
        return Media.objects.filter(content_type=ct, object_id=obj.pk)

    def create(self, request, *args, **kwargs):
        model, obj = self._resolve_parent()
        if not model:
            return Response({'error': 'Нужен ровно один из query params: round_id, question_id, answer_id'}, status=status.HTTP_400_BAD_REQUEST)
        if not obj:
            return Response({'error': 'Родительский объект не найден'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(content_type=ContentType.objects.get_for_model(model), object_id=obj.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
