
from rest_framework import serializers
from django.db import transaction
from rest_framework import serializers
from api.models import Game, Round, Question, Answer,QuestionType

class AnswerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id','content','order','is_correct']

class QuestionWriteSerializer(serializers.ModelSerializer):
    answers = AnswerWriteSerializer(many=True, required=False)
    id = serializers.UUIDField(source='uuid', read_only=True)
    class Meta:
        model = Question
        fields = ['id','content','question_type','order','answers']

    def create(self,validated_data):
        answers_data = validated_data.pop('answers',[])
        question_object = Question.objects.create(**validated_data)
        answer_serializer = AnswerWriteSerializer()
        for answer in answers_data:
            answer['question'] = question_object
            answer_serializer.create(answer)
        return question_object

class RoundWriteSerializer(serializers.ModelSerializer):
    questions = QuestionWriteSerializer(many=True, required= False)
    id = serializers.UUIDField(source='uuid',read_only=True)

    class Meta:
        model = Round
        fields = ['id','title','description','order','questions']

    def create(self,validated_data):
        questions_data = validated_data.pop('questions',[])
        round_obj = Round.objects.create(**validated_data)
        q_serializer = QuestionWriteSerializer()
        for question in questions_data:
            question['round'] = round_obj
            q_serializer.create(question)
        return round_obj

class GameSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', read_only=True)
    rounds = RoundWriteSerializer(many=True, required=False)
    class Meta:
        model = Game
        fields = ["id",'title','description','creator','rounds']

    @transaction.atomic
    def create(self,validated_data):
        rounds_data = validated_data.pop('rounds',[])
        game = Game.objects.create(**validated_data)
        round_serializer = RoundWriteSerializer()
        for round_data in rounds_data:
            round_data['game'] = game
            round_serializer.create(round_data)
        return game

class GameListSerializer(serializers.ModelSerializer):
    #class to provide information about all games
    id = serializers.UUIDField(source='uuid', read_only=True)
    rounds_count = serializers.IntegerField(read_only=True)
    questions_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Game
        fields = ['id','title','description','creator','rounds_count','questions_count']

class QuestionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionType
        fields = '__all__'





