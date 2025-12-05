from rest_framework import serializers
from .models import Project, TaskBoard, Task, TaskComment


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['id', 'tenant']


class TaskBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskBoard
        fields = '__all__'
        read_only_fields = ['id']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class TaskCommentSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'user', 'user_full_name', 'message', 'created_at']
        read_only_fields = ['id', 'user_full_name', 'created_at']
