import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    'Image': ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
    'Audio': ['.mp3', '.wav', '.ogg'],
    'Video': ['.mp4', '.webm', '.mov'],
}

def validate_media_file(file, media_type):
    media_type_name = getattr(media_type, 'name', media_type)
    allowed_extensions = ALLOWED_EXTENSIONS.get(media_type_name)
    if allowed_extensions is None:
        raise ValidationError(f'Неизвестный тип медиа: {media_type_name}')

    extension = os.path.splitext(file.name)[1].lower()
    if extension not in allowed_extensions:
        raise ValidationError(
            f'Недопустимое расширение "{extension}" для типа "{media_type_name}". '
            f'Разрешены: {", ".join(allowed_extensions)}'
        )

    if file.size > settings.MAX_MEDIA_UPLOAD_SIZE:
        max_mb = settings.MAX_MEDIA_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationError(f'Файл слишком большой. Максимальный размер: {max_mb:.0f} МБ')
