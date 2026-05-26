
from django.contrib import admin

from api.models import Game,Round,Question,QuestionType,Answer

for model in (Game,Round,Question,QuestionType,Answer):
    admin.site.register(model)