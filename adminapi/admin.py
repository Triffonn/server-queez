from django.contrib  import admin
from api.models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id','uuid','title','creator','description','is_completed','created_at')

# Register your models here.
