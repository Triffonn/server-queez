from rest_framework import serializers
from api.models import Game

class AdminGameListSerializer(serializers.ModelSerializer):
    """Короткий сериализатор для списка."""
    id = serializers.UUIDField(source="uuid",  read_only=True)

    class Meta:
        model = Game
        fields = ['id','title','creator','description','is_completed','created_at']


class AdminGameDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор для одной игры."""
    id = serializers.UUIDField(source="uuid", read_only=True)
    class Meta:
        model = Game
        fields = ['id','title','creator','description','is_completed','created_at']