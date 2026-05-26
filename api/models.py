from django.db import models
import uuid
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

class Game(models.Model):
    uuid = models.UUIDField(default =uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    creator = models.CharField(max_length=255,blank=True)
    description = models.TextField(blank = True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Round(models.Model):
    uuid = models.UUIDField(default =uuid.uuid4, editable=False, unique=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True, related_name='rounds')
    title = models.CharField(max_length=255)
    description = models.TextField(blank = True)
    created_at = models.DateTimeField(auto_now_add=True)
    #media = GenericRelation(Media)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = [('game', 'order')]

    def __str__(self):
        return self.title

class QuestionType(models.Model):
    #тип вопроса - Аукцион, Ассоциация, Варианты ответов, Вопрос открытый
    type = models.CharField(max_length=255,unique=True)

    def __str__(self):
        return self.type

class Question(models.Model):
    uuid = models.UUIDField(default =uuid.uuid4, editable=False, unique=True)
    round = models.ForeignKey(Round,related_name='questions',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField(blank=True)
    #media = GenericRelation(Media)
    question_type = models.ForeignKey(QuestionType, on_delete=models.DO_NOTHING,related_name='questions')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.content

class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    #media = GenericRelation(Media)
    order = models.PositiveIntegerField(default=0)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.content

"""
Classes for future usage - while media will actual

class MediaType(models.Model):
    #Словарь для хранения типов медиа
    name = models.CharField(max_length=255,unique=True)

class Media(models.Model):
    #Хранит медиа данные, которые могут быть у каждого объекта - можно добавлять к одной сущности много разного
    uuid = models.UUIDField(default =uuid.uuid4, editable=False, unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    media_type = models.ForeignKey(MediaType, on_delete=models.PROTECT)
    caption = models.TextField(blank = True)
    file = models.FileField(upload_to='media/')
    upload_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Медиа к  {self.content_object}'
"""