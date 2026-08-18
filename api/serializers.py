
from rest_framework import serializers
from django.db import transaction
from rest_framework import serializers
from api.models import Game, Round, Question, Answer,QuestionType,Media,MediaType,MediaTimeUsing
from api.validators import validate_media_file

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

class AnswerWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    media = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Answer
        fields = ['id','content','order','is_correct',"media"]

class QuestionWriteSerializer(serializers.ModelSerializer):
    answers = AnswerWriteSerializer(many=True, required=False)
    id = serializers.UUIDField(source='uuid', read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = ['id','content','question_type','order','answers','media']

    def create(self,validated_data):
        answers_data = validated_data.pop('answers',[])
        question_object = Question.objects.create(**validated_data)
        answer_serializer = AnswerWriteSerializer()
        for answer in answers_data:
            answer.pop('id', None)  # id от клиента при создании игнорируем
            answer['question'] = question_object
            answer_serializer.create(answer)
        return question_object
    
    def update(self, instance, validated_data):
        answers_data = validated_data.pop('answers', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if answers_data is not None:
            with transaction.atomic():
                existing = {a.id: a for a in instance.answers.all()}
                seen_ids = set()
                for answer_data in answers_data:
                    answer_id = answer_data.pop('id', None)
                    if answer_id is not None:
                        answer = existing.get(answer_id)
                        if answer is None:
                            raise serializers.ValidationError(f'Ответ с id={answer_id} не принадлежит этому вопросу')
                        for attr, value in answer_data.items():
                            setattr(answer, attr, value)
                        answer.save()
                        seen_ids.add(answer_id)
                    else:
                        new_answer = Answer.objects.create(question=instance, **answer_data)
                        seen_ids.add(new_answer.id)
                instance.answers.exclude(id__in=seen_ids).delete()
                remaining = list(instance.answers.order_by('order','id'))
                for index, answer in enumerate(remaining):
                    if answer.order != index:
                        answer.order = index
                        answer.save(update_fields=['order'])
        return instance

class RoundWriteSerializer(serializers.ModelSerializer):
    questions = QuestionWriteSerializer(many=True, required= False)
    id = serializers.UUIDField(source='uuid',read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Round
        fields = ['id','title','description','order','questions','media']

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
    media = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Game
        fields = ["id",'title','description','creator','created_at','is_completed','rounds','media']

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
        fields = ['id','title','description','creator','rounds_count','questions_count','created_at','is_completed']

class QuestionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionType
        fields = '__all__'

class MediaTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaType
        fields = '__all__'

class MediaTimeUsingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaTimeUsing
        fields = '__all__'

class RoundSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Round
        fields = ['id','title','description','created_at','order','media']



