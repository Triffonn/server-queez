# Reorder: Round, Question, Answer

## Статус

Шаги 1-3 (пересчёт order при удалении Round/Question/Answer) уже реализованы
в `api/views.py` (`RoundViewSet.perform_destroy`, `QuestionViewSet.perform_destroy`)
и `api/serializers.py` (`QuestionWriteSerializer.update`).

Этот план — следующая задача: дать фронту возможность **перетасовать порядок**
(например, drag-n-drop списка) для раундов, вопросов и ответов.

## Контекст / почему не просто N отдельных PATCH-запросов

- `Round.order` защищён `unique_together = [('game', 'order')]`. Если менять
  порядок последовательными одиночными `PATCH /api/rounds/{uuid}/`, легко
  словить `IntegrityError`: например, чтобы поменять местами раунды с order
  0 и 1, `PATCH round_A {order: 1}` упадёт, пока round_B ещё держит order=1.
- Даже там, где нет unique-constraint (`Question`, `Answer`), N отдельных
  запросов — это N отдельных транзакций: если сеть оборвётся на середине,
  получится частично применённый порядок.
- Поэтому нужен один запрос, который переставляет весь порядок разом, в
  одной транзакции.

Роуты уже зарегистрированы через `DefaultRouter` в `config/urls.py`
(`router.register(r'rounds', RoundViewSet, ...)`, аналогично для `questions`).
DRF `@action` на `ViewSet` автоматически добавляет URL через роутер — трогать
`config/urls.py` не нужно.

---

## Шаг 4: Reorder для Round

### Файл: `api/views.py`

Добавить импорт `action`, если ещё не импортирован (уже есть:
`from rest_framework.decorators import action`).

Добавить метод в `RoundViewSet`:

```python
@action(detail=False, methods=['post'], url_path='reorder')
def reorder(self, request):
    game_uuid = request.query_params.get('game_id')
    if not game_uuid:
        return Response({'error': 'game_id обязателен в query params'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        game = Game.objects.get(uuid=game_uuid)
    except Game.DoesNotExist:
        return Response({'error': f'Игра с uuid {game_uuid} не найдена'}, status=status.HTTP_404_NOT_FOUND)

    new_order = request.data.get('order')
    if not isinstance(new_order, list):
        return Response({'error': 'Ожидается список uuid раундов в поле order'}, status=status.HTTP_400_BAD_REQUEST)

    rounds = {str(r.uuid): r for r in Round.objects.filter(game=game)}
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
```

### Формат запроса

```
POST /api/rounds/reorder/?game_id=<game_uuid>
Content-Type: application/json

{
  "order": ["<round_uuid_1>", "<round_uuid_2>", "<round_uuid_3>"]
}
```
Порядок uuid в списке = новый order (0, 1, 2, ...). Список должен содержать
**все** раунды игры — если прислать неполный список или лишний uuid, вернётся
400 (чтобы случайно не потерять/не забыть раунд).

### Почему два прохода, а не один

Если писать финальный order сразу по одному `.save()` за раз, порядок вызовов
может временно совпасть с ещё не обновлённым соседом и упасть на
`unique_together`. Первый проход сдвигает все order в заведомо свободный
диапазон (`+100000`, поле `PositiveIntegerField`, поэтому не через отрицательные
числа), второй проход расставляет финальные 0..N-1 — на этом этапе коллизий
уже не будет, т.к. временные значения ни с чем не пересекаются.

### Проверка

1. Игра с 3 раундами, order 0,1,2 (uuid A, B, C).
2. `POST /api/rounds/reorder/?game_id=...` с телом `{"order": ["C_uuid","A_uuid","B_uuid"]}`.
3. `GET /api/rounds/?game_id=...` — должно вернуться в порядке C(0), A(1), B(2).

---

## Шаг 5: Reorder для Question

### Файл: `api/views.py`

Добавить метод в `QuestionViewSet` (у `Question` нет `unique_together`, поэтому
без двух проходов — достаточно одного):

```python
@action(detail=False, methods=['post'], url_path='reorder')
def reorder(self, request):
    round_uuid = request.query_params.get('round_id')
    if not round_uuid:
        return Response({'error': 'round_id обязателен в query params'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        round_obj = Round.objects.get(uuid=round_uuid)
    except Round.DoesNotExist:
        return Response({'error': f'Round с uuid {round_uuid} не найден'}, status=status.HTTP_404_NOT_FOUND)

    new_order = request.data.get('order')
    if not isinstance(new_order, list):
        return Response({'error': 'Ожидается список uuid вопросов в поле order'}, status=status.HTTP_400_BAD_REQUEST)

    questions = {str(q.uuid): q for q in Question.objects.filter(round=round_obj)}
    if set(new_order) != set(questions.keys()):
        return Response({'error': 'Список order должен содержать все вопросы раунда без пропусков и дублей'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        for index, uuid_str in enumerate(new_order):
            q = questions[uuid_str]
            if q.order != index:
                q.order = index
                q.save(update_fields=['order'])

    queryset = Question.objects.filter(round=round_obj).order_by('order')
    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)
```

### Формат запроса

```
POST /api/questions/reorder/?round_id=<round_uuid>
Content-Type: application/json

{
  "order": ["<question_uuid_1>", "<question_uuid_2>", "<question_uuid_3>"]
}
```
Та же логика валидации: список должен содержать все вопросы раунда целиком.

### Проверка

1. Раунд с 3 вопросами, order 0,1,2 (uuid A, B, C).
2. `POST /api/questions/reorder/?round_id=...` с телом `{"order": ["B_uuid","C_uuid","A_uuid"]}`.
3. `GET /api/questions/?round_id=...` — должно вернуться в порядке B(0), C(1), A(2).

---

## Шаг 6: Reorder для Answer — отдельный эндпоинт не нужен

У `Answer` нет своего `AnswerViewSet`/роута (как и с удалением — см. шаг 3),
и `Answer.order` не имеет unique-constraint. Реордер ответов уже полностью
покрывается существующим `PATCH /api/questions/{uuid}/` через
`QuestionWriteSerializer.update()`, которая (после шага 3) сама пересчитывает
order оставшихся ответов и принимает `order` как обычное поле каждого ответа.

### Как фронту реордерить ответы

Прислать `PATCH /api/questions/{uuid}/` с полем `answers`, где перечислены
**все существующие ответы вопроса** (обязательно с их `id`, чтобы они не были
приняты за новые и не задвоились/не потерялись) и новым значением `order` у
каждого:

```
PATCH /api/questions/{question_uuid}/
Content-Type: application/json

{
  "answers": [
    {"id": 5, "order": 0},
    {"id": 3, "order": 1},
    {"id": 7, "order": 2}
  ]
}
```

Важно (текущее поведение `QuestionWriteSerializer.update`, никаких изменений
кода не требуется):
- Нужно передавать **все** существующие ответы вопроса. Любой существующий
  `id`, которого нет в присланном списке, будет удалён —
  `instance.answers.exclude(id__in=seen_ids).delete()` срабатывает при любом
  сохранении с `answers` в теле, не только специально для реордера.
- `order` в каждом объекте не обязан быть строго 0..N-1 без дыр — после
  применения все ответы всё равно пересчитываются финальным проходом
  (`remaining = instance.answers.order_by('order','id')` → `enumerate`),
  так что итоговый порядок будет по возрастанию присланных значений `order`,
  а хранимые значения станут contiguous 0..N-1.
- Других полей (`content`, `is_correct`) можно не передавать при чистом
  реордере, но `content` в `AnswerWriteSerializer` не имеет `required=False`
  по умолчанию у `ModelSerializer` для `blank=True` полей — стоит на практике
  проверить, что partial-объект `{"id":5,"order":0}` проходит валидацию
  сериализатора (тип запроса — `PATCH`, у DRF `partial=True` для отдельных
  полей верхнего уровня объекта Question, но `answers` — вложенный список
  через `AnswerWriteSerializer(many=True)`, который сериализатор validates
  как обычный, не partial, if `content` required — стоит либо всегда
  присылать текущий `content`/`is_correct` вместе с `order`, либо (если
  реордер без остальных полей окажется не проходит валидацию) сделать поля
  `content`/`is_correct` в `AnswerWriteSerializer` `required=False` отдельным
  небольшим фиксом).

### Проверка

1. Вопрос с 3 ответами, order 0,1,2 (id 5,3,7).
2. `PATCH /api/questions/{uuid}/` с `answers: [{"id":7,"order":0},{"id":5,"order":1},{"id":3,"order":2}]`
   (плюс текущие `content`/`is_correct` каждого ответа, если валидация того потребует).
3. `GET /api/questions/{uuid}/` (или через список) — ответы должны идти в
   порядке id=7(0), id=5(1), id=3(2).
4. Если в п.2 отправить неполный список (пропустить один существующий id) —
   убедиться, что пропущенный ответ удалился (ожидаемое поведение, а не баг) —
   и явно предупредить фронтенд-команду об этом нюансе API.

---

## Сводка затрагиваемых файлов
- `api/views.py` — `RoundViewSet.reorder`, `QuestionViewSet.reorder` (новые `@action`)
- `api/serializers.py` — изменений не требуется (шаг 6 использует то, что уже сделано в шаге 3); при необходимости — сделать `content`/`is_correct` в `AnswerWriteSerializer` необязательными для partial-реордера
- `config/urls.py` — без изменений (роуты для `@action` подхватятся автоматически через уже зарегистрированные `router.register(r'rounds', ...)` / `router.register(r'questions', ...)`)
