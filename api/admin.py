
from django.contrib import admin

from api.models import Game,Round,Question,QuestionType,Answer,Media,MediaType,MediaTimeUsing

for model in (Game,
              Round,
              Question,
              QuestionType,
              Answer,
              Media,
              MediaType,
              MediaTimeUsing):
    admin.site.register(model)