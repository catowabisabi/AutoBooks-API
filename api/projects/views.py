from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Project, TaskBoard, Task, TaskComment
from .serializers import ProjectSerializer, TaskBoardSerializer, TaskSerializer, TaskCommentSerializer


@extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出專案 / List projects',
        description='獲取當前租戶的所有專案列表。\n\nGet all projects for current tenant.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='創建專案 / Create project',
        description='創建新的專案。\n\nCreate a new project.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取專案詳情 / Get project details',
        description='獲取指定專案的詳細資訊。\n\nGet details of a specific project.'
    ),
    update=extend_schema(
        tags=['Projects'],
        summary='更新專案 / Update project',
        description='更新專案資訊。\n\nUpdate project information.'
    ),
    partial_update=extend_schema(
        tags=['Projects'],
        summary='部分更新專案 / Partial update project',
        description='部分更新專案資訊。\n\nPartially update project information.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='刪除專案 / Delete project',
        description='刪除專案。\n\nDelete project.'
    ),
)
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


@extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出任務看板 / List task boards',
        description='獲取專案的所有任務看板。\n\nGet all task boards for projects.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='創建任務看板 / Create task board',
        description='創建新的任務看板。\n\nCreate a new task board.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取任務看板詳情 / Get task board details',
        description='獲取指定任務看板的詳細資訊。\n\nGet details of a specific task board.'
    ),
    update=extend_schema(
        tags=['Projects'],
        summary='更新任務看板 / Update task board',
        description='更新任務看板資訊。\n\nUpdate task board information.'
    ),
    partial_update=extend_schema(
        tags=['Projects'],
        summary='部分更新任務看板 / Partial update task board',
        description='部分更新任務看板資訊。\n\nPartially update task board information.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='刪除任務看板 / Delete task board',
        description='刪除任務看板。\n\nDelete task board.'
    ),
)
class TaskBoardViewSet(viewsets.ModelViewSet):
    serializer_class = TaskBoardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskBoard.objects.filter(project__tenant=self.request.user.tenant)


@extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出任務 / List tasks',
        description='獲取看板的所有任務。\n\nGet all tasks for boards.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='創建任務 / Create task',
        description='創建新的任務。\n\nCreate a new task.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取任務詳情 / Get task details',
        description='獲取指定任務的詳細資訊。\n\nGet details of a specific task.'
    ),
    update=extend_schema(
        tags=['Projects'],
        summary='更新任務 / Update task',
        description='更新任務資訊。\n\nUpdate task information.'
    ),
    partial_update=extend_schema(
        tags=['Projects'],
        summary='部分更新任務 / Partial update task',
        description='部分更新任務資訊。\n\nPartially update task information.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='刪除任務 / Delete task',
        description='刪除任務。\n\nDelete task.'
    ),
)
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(board__project__tenant=self.request.user.tenant)


@extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出任務留言 / List task comments',
        description='獲取任務的所有留言。\n\nGet all comments for tasks.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='創建任務留言 / Create task comment',
        description='為任務添加新留言。\n\nAdd new comment to task.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取任務留言詳情 / Get task comment details',
        description='獲取指定留言的詳細資訊。\n\nGet details of a specific comment.'
    ),
    update=extend_schema(
        tags=['Projects'],
        summary='更新任務留言 / Update task comment',
        description='更新留言內容。\n\nUpdate comment content.'
    ),
    partial_update=extend_schema(
        tags=['Projects'],
        summary='部分更新任務留言 / Partial update task comment',
        description='部分更新留言內容。\n\nPartially update comment content.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='刪除任務留言 / Delete task comment',
        description='刪除留言。\n\nDelete comment.'
    ),
)
class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task__board__project__tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
