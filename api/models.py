from django.db import models
import uuid
from django.conf import settings

class Task(models.Model):
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


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
