from rest_framework import serializers
from .models import Task
from rest_framework.response import Response

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id','title']