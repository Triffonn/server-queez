# Поддержка медиа (изображения/аудио/видео) для вопросов, ответов и раундов

## Контекст

В `api/models.py` уже лежат несмигрированные модели `Media`, `MediaType`, `MediaTimeUsing` и `GenericRelation(Media)` на `Round`, `Question`, `Answer` — это черновик, оставшийся с прошлой сессии. Миграций под них нет, `MEDIA_ROOT`/`MEDIA_URL` в `config/settings.py` не заданы, сериализаторов и эндпоинтов для `Media` нет. Нужно довести это до рабочего состояния: клиент должен иметь возможность прикрепить файл к раунду/вопросу/ответу, а при получении данных игры/раунда/вопроса — увидеть прикреплённые медиа с рабочей ссылкой на файл. Хранилище — persistent volume на Railway (контейнер эфемерный, поэтому обычный локальный диск без volume уронит все файлы при редеплое).

Решения, принятые с пользователем:
- **API**: отдельный `MediaViewSet` (`/api/media/`), загрузка через multipart, родитель передаётся query-параметром (`round_id` / `question_id` / `answer_id`) — по аналогии с существующим паттерном `RoundViewSet`/`QuestionViewSet` (`api/views.py:40-94`).
- **MediaType**: `изображение`, `аудио`, `видео`.
- **MediaTimeUsing**: момент показа контента относительно основной сущности — `до`, `во время`, `после`.
- **Railway volume**: ещё не создан, план включает инструкцию по настройке.

## 1. Модели и миграции

Текущий черновик моделей (`api/models.py:1-28`) в целом корректен, требуется одна правка и генерация миграций:

- В `Media.content_type` оставить `on_delete=models.PROTECT` (уже так) — это защищает от случайного удаления `ContentType`.
- Убрать финальный закомментированный блок `"""Classes for future usage..."""` (строки 96-100) — модели уже не "future", а активные.
- Выполнить `python manage.py makemigrations api` — сгенерирует миграцию создания `MediaType`, `MediaTimeUsing`, `Media` и добавления `GenericRelation` полей (сами `GenericRelation` не создают колонку в БД, но Django всё равно фиксирует их в миграции).
- Добавить data-миграцию для сидов, по образцу `api/migrations/0007_seed_question_types.py`:
  - `MediaType`: `изображение`, `аудио`, `видео`
  - `MediaTimeUsing`: `до`, `во время`, `после`
  - Обратная функция (`RunPython` с `reverse_code`) удаляет эти же записи по имени, как в примере.

## 2. Настройки Django (`config/settings.py`)

Добавить после блока `STATIC_ROOT`/`STATICFILES_STORAGE` (строки 157-158):

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', BASE_DIR)) / 'media'

MAX_MEDIA_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 МБ, единый лимит на файл
```

- `RAILWAY_VOLUME_MOUNT_PATH` — переменная, которую Railway автоматически прокидывает в контейнер, когда к сервису подключён Volume (см. раздел 6). Локально (без volume) переменной не будет, и `MEDIA_ROOT` упадёт на `BASE_DIR/media` — рабочий вариант для разработки.
- `requirements.txt`: добавить `Pillow` (нужен `ImageField`/валидация изображений через `PIL`, стандартная зависимость Django для этого).

# ОСТАНОВИЛСЯ ТУТ!!!!!!!!!!!!


## 3. Раздача медиафайлов (`config/urls.py`)

Whitenoise (уже используется для статики) не подходит — он сканирует файлы на старте процесса и не увидит файлы, добавленные после деплоя. Поэтому раздачу медиа делаем через `django.views.static.serve`, подключённую **всегда**, а не только при `DEBUG=True` (обычный хелпер `django.conf.urls.static.static()` игнорируется, если `DEBUG=False`):

```python
from django.conf import settings
from django.urls import re_path
from django.views.static import serve as static_serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
]
```

Для масштаба этого проекта (учебная/квиз-игра, не высоконагруженный сервис) раздача через Django-view приемлема; при росте нагрузки — вынести на nginx или CDN перед контейнером.

## 4. Валидация загружаемых файлов

Новый файл `api/validators.py`:
- Словарь допустимых расширений по имени `MediaType` (`изображение` → `.jpg/.jpeg/.png/.webp/.gif`, `аудио` → `.mp3/.wav/.ogg`, `видео` → `.mp4/.webm/.mov`).
- Функция `validate_media_file(file, media_type)`, проверяющая расширение и `file.size <= settings.MAX_MEDIA_UPLOAD_SIZE`, бросающая `django.core.exceptions.ValidationError`.
- Вызывается из `MediaSerializer.validate()` (см. ниже), а не из `models.Media`, чтобы ошибка красиво возвращалась как 400 через DRF.

## 5. Сериализаторы (`api/serializers.py`)

Добавить:

```python
class MediaSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', read_only=True)
    media_type = serializers.SlugRelatedField(slug_field='name', queryset=MediaType.objects.all())
    media_time_using = serializers.SlugRelatedField(slug_field='name', queryset=MediaTimeUsing.objects.all())

    class Meta:
        model = Media
        fields = ['id', 'media_type', 'media_time_using', 'caption', 'file', 'upload_at']
        read_only_fields = ['upload_at']

    def validate(self, attrs):
        file = attrs.get('file')
        media_type = attrs.get('media_type')
        if file and media_type:
            validate_media_file(file, media_type)
        return attrs
```

`content_type`/`object_id` в сериализаторе намеренно отсутствуют — их проставляет `MediaViewSet.create()` (см. ниже), клиент их не передаёт напрямую (иначе можно приаттачить файл к чужой сущности произвольного типа).

Добавить `media = MediaSerializer(many=True, read_only=True)` в существующие read/write сериализаторы, чтобы медиа отдавались вместе с родительской сущностью:
- `AnswerWriteSerializer` (`api/serializers.py:7-12`) — добавить в `fields`.
- `QuestionWriteSerializer` (`api/serializers.py:14-20`) — добавить в `fields`.
- `RoundWriteSerializer` (`api/serializers.py:58-64`) — добавить в `fields`.
- `RoundSerializer` (`api/serializers.py:106-110`) — добавить в `fields` (используется в `RoundViewSet` для чтения).

Поле read-only — запись медиа идёт только через `MediaViewSet`, не через вложенные `create`/`update` этих сериализаторов (там и так сложная ручная логика upsert, не стоит её усложнять генерик-связью).

## 6. Вьюсет и роутинг

`api/views.py` — добавить `MediaViewSet`, повторяющий паттерн `RoundViewSet`/`QuestionViewSet`:

```python
class MediaViewSet(viewsets.ModelViewSet):
    serializer_class = MediaSerializer
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'uuid'

    PARENT_PARAM_MODELS = {
        'round_id': Round,
        'question_id': Question,
        'answer_id': Answer,
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
```

Примечание: `Answer` не имеет `uuid` (только `id`), поэтому для `answer_id` используется числовой `pk` — как и в остальной части этого плана, стоит проверить с пользователем, не стоит ли также добавить `uuid` в `Answer` для консистентности; в рамках этого плана не трогаем, т.к. не относится к медиа напрямую.

`config/urls.py` — зарегистрировать в роутере:
```python
router.register(r'media', MediaViewSet, basename='media')
```
и добавить `re_path` для раздачи `MEDIA_URL` (см. раздел 3).

## 7. Admin (`api/admin.py`)

Добавить `Media`, `MediaType`, `MediaTimeUsing` в цикл регистрации — сейчас там зарегистрированы только `Game, Round, Question, QuestionType, Answer`.

## 8. Настройка Railway Volume

1. В Railway Dashboard → сервис `server-queez` → вкладка **Volumes** → **New Volume**.
2. Указать mount path, например `/data` (любой путь вне кода приложения).
3. Railway автоматически создаёт переменную окружения `RAILWAY_VOLUME_MOUNT_PATH` со значением этого пути и пробрасывает её в контейнер сервиса — именно её читает `MEDIA_ROOT` в `config/settings.py` (раздел 2).
4. Передеплоить сервис, чтобы переменная подхватилась и volume примонтировался.
5. Важно: volume — это одно хранилище на один сервис/инстанс; если позже появится несколько инстансов (горизонтальное масштабирование), Railway volumes не шардятся между ними — тогда потребуется переход на S3-совместимое хранилище (`django-storages` + `boto3`), сейчас это не требуется.

## Итоговый список файлов

- `api/models.py` — убрать мёртвый комментарий в конце.
- `api/migrations/0008_media_models.py` (авто) + `api/migrations/0009_seed_media_lookups.py` (сиды).
- `config/settings.py` — `MEDIA_URL`, `MEDIA_ROOT`, `MAX_MEDIA_UPLOAD_SIZE`.
- `config/urls.py` — раздача media + роут `media/`.
- `api/validators.py` — новый файл.
- `api/serializers.py` — `MediaSerializer` + поле `media` в 4 существующих сериализаторах.
- `api/views.py` — `MediaViewSet`.
- `api/admin.py` — регистрация 3 моделей.
- `requirements.txt` — `Pillow`.

## Проверка

1. `python manage.py makemigrations api` — убедиться, что сгенерировалась ровно одна миграция для новых моделей (плюс отдельно сид-миграция), применить `python manage.py migrate`.
2. Локально (без Railway volume) поднять сервер, убедиться что `media/` создаётся в корне проекта и файлы реально сохраняются/читаются.
3. Через `POST /api/games/` создать игру с раундом и вопросом (уже есть nested-create), получить `uuid` вопроса.
4. `POST /api/media/?question_id=<uuid>` с multipart-телом (`file`, `media_type=изображение`, `media_time_using=во время`, `caption=...`) — ожидать 201 и рабочий `file` URL вида `/media/media/<filename>`.
5. `GET /api/games/<uuid>/full/` — убедиться, что в ответе у вопроса появился массив `media` с загруженным файлом.
6. Открыть URL из поля `file` в браузере напрямую — убедиться, что `re_path`-раздача в `config/urls.py` реально отдаёт файл (в т.ч. при `DEBUG=False`, чтобы проверить прод-режим).
7. Попробовать загрузить файл с недопустимым расширением/размером — убедиться, что `validate_media_file` возвращает 400, а не 500.
