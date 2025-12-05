from rest_framework import viewsets, permissions
from .models import Project, TaskBoard, Task, TaskComment
from .serializers import ProjectSerializer, TaskBoardSerializer, TaskSerializer, TaskCommentSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class TaskBoardViewSet(viewsets.ModelViewSet):
    serializer_class = TaskBoardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskBoard.objects.filter(project__tenant=self.request.user.tenant)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(board__project__tenant=self.request.user.tenant)


class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task__board__project__tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
