"""
Async Task ViewSet
==================
API endpoints for managing async tasks and checking progress.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema, extend_schema_view

from ai_assistants.models_tasks import AsyncTask, TaskStatus, TaskType
from core.schema_serializers import TaskProgressResponseSerializer, AsyncTaskResponseSerializer


class AsyncTaskSerializer:
    """Simple serializer for AsyncTask"""
    
    @staticmethod
    def serialize(task):
        return {
            'id': str(task.id),
            'celery_task_id': task.celery_task_id,
            'task_type': task.task_type,
            'name': task.name,
            'description': task.description,
            'status': task.status,
            'progress': task.progress,
            'progress_message': task.progress_message,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'duration_seconds': task.duration_seconds,
            'result': task.result,
            'error_message': task.error_message,
            'is_complete': task.is_complete,
            'is_running': task.is_running,
            'created_at': task.created_at.isoformat(),
        }


@extend_schema_view(
    list=extend_schema(
        tags=['AI Tasks'],
        summary='列出任務 / List tasks',
        description='獲取用戶的異步任務列表。\n\nGet user\'s async tasks list.'
    ),
    retrieve=extend_schema(
        tags=['AI Tasks'],
        summary='獲取任務詳情 / Get task details',
        description='獲取指定任務的詳細資訊。\n\nGet details of a specific task.'
    ),
    cancel=extend_schema(
        tags=['AI Tasks'],
        summary='取消任務 / Cancel task',
        description='取消正在運行的任務。\n\nCancel a running task.'
    ),
    stats=extend_schema(
        tags=['AI Tasks'],
        summary='任務統計 / Task statistics',
        description='獲取用戶的任務統計資訊。\n\nGet user\'s task statistics.'
    ),
)
class AsyncTaskViewSet(viewsets.ViewSet):
    """
    ViewSet for managing async tasks.
    
    Endpoints:
    - GET /tasks/ - List user's tasks
    - GET /tasks/{id}/ - Get task details
    - POST /tasks/{id}/cancel/ - Cancel a running task
    - GET /tasks/stats/ - Get task statistics
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AsyncTaskResponseSerializer
    
    def list(self, request):
        """List user's tasks"""
        queryset = AsyncTask.objects.filter(user=request.user)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by task type
        task_type = request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by running tasks only
        if request.query_params.get('running') == 'true':
            queryset = queryset.filter(
                status__in=[TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROGRESS]
            )
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        tasks = queryset[start:end]
        
        return Response({
            'count': total,
            'results': [AsyncTaskSerializer.serialize(t) for t in tasks],
        })
    
    def retrieve(self, request, pk=None):
        """Get task details"""
        try:
            task = AsyncTask.objects.get(id=pk, user=request.user)
            return Response(AsyncTaskSerializer.serialize(task))
        except AsyncTask.DoesNotExist:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running task"""
        try:
            task = AsyncTask.objects.get(id=pk, user=request.user)
        except AsyncTask.DoesNotExist:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if task.is_complete:
            return Response(
                {'error': 'Task is already complete'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Revoke the Celery task
        from core.celery import app as celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)
        
        task.mark_revoked()
        
        return Response({
            'message': 'Task cancelled',
            'task': AsyncTaskSerializer.serialize(task),
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get task statistics"""
        queryset = AsyncTask.objects.filter(user=request.user)
        
        # Count by status
        by_status = queryset.values('status').annotate(count=Count('id'))
        
        # Count by type
        by_type = queryset.values('task_type').annotate(count=Count('id'))
        
        # Recent tasks (last 24 hours)
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        recent = queryset.filter(created_at__gte=yesterday)
        
        # Running tasks
        running = queryset.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROGRESS]
        ).count()
        
        return Response({
            'total': queryset.count(),
            'running': running,
            'by_status': list(by_status),
            'by_type': list(by_type),
            'recent_24h': recent.count(),
        })
    
    @action(detail=False, methods=['post'])
    def create_task(self, request):
        """Create and start a new async task"""
        task_type = request.data.get('task_type')
        name = request.data.get('name', 'Untitled Task')
        input_data = request.data.get('input_data', {})
        
        if not task_type:
            return Response(
                {'error': 'task_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start the appropriate Celery task
        from ai_assistants.tasks import (
            process_document_ocr,
            generate_report,
            run_ai_analysis,
        )
        
        task_mapping = {
            TaskType.OCR_PROCESS: process_document_ocr,
            TaskType.REPORT_GENERATION: generate_report,
            TaskType.AI_ANALYSIS: run_ai_analysis,
        }
        
        celery_task_func = task_mapping.get(task_type)
        if not celery_task_func:
            return Response(
                {'error': f'Unknown task type: {task_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start the Celery task
        celery_result = celery_task_func.delay(
            **input_data,
            user_id=request.user.id,
        )
        
        # Create the AsyncTask record
        async_task = AsyncTask.objects.create(
            celery_task_id=celery_result.id,
            user=request.user,
            task_type=task_type,
            name=name,
            input_data=input_data,
        )
        
        return Response(
            AsyncTaskSerializer.serialize(async_task),
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=['AI Tasks'],
    summary='查看任務進度 / Check task progress',
    description='通過 Celery 任務 ID 查看任務進度。\n\nCheck task progress by Celery task ID.'
)
class TaskProgressView(APIView):
    """
    Simple endpoint to check task progress by Celery task ID.
    
    GET /api/ai/task-status/<task_id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskProgressResponseSerializer
    
    def get(self, request, task_id):
        """Get task progress by Celery task ID"""
        try:
            # First check our database
            task = AsyncTask.objects.get(
                celery_task_id=task_id,
                user=request.user
            )
            return Response(AsyncTaskSerializer.serialize(task))
        except AsyncTask.DoesNotExist:
            # Fallback to Celery result backend
            result = AsyncResult(task_id)
            return Response({
                'celery_task_id': task_id,
                'status': result.status,
                'ready': result.ready(),
                'successful': result.successful() if result.ready() else None,
                'result': result.result if result.ready() and result.successful() else None,
                'error': str(result.result) if result.ready() and not result.successful() else None,
            })
