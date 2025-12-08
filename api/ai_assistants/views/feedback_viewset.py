"""
AI Feedback API ViewSet
=======================
Handle feedback submissions and result logging.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q, Sum, F
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
import uuid
from datetime import timedelta

from ..models_feedback import (
    AIFeedback, AIResultLog, AIFeedbackType,
    AIRequestLog, VectorSearchLog, KnowledgeGapLog, AIUsageSummary
)
from ..serializers.feedback_serializers import (
    AIFeedbackSerializer,
    AIFeedbackCreateSerializer,
    AIResultLogSerializer,
    AIResultLogCreateSerializer,
    AIRequestLogSerializer,
    AIRequestLogCreateSerializer,
    VectorSearchLogSerializer,
    VectorSearchLogCreateSerializer,
    KnowledgeGapLogSerializer,
    KnowledgeGapCreateSerializer,
    KnowledgeGapResolveSerializer,
    AIUsageSummarySerializer,
    RAGObservabilityDashboardSerializer,
)


class AIFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI Feedback
    
    Endpoints:
    - POST /feedback/ - Submit feedback
    - GET /feedback/ - List user's feedback
    - GET /feedback/stats/ - Get feedback statistics
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['result_id', 'field_name', 'comment']
    ordering_fields = ['created_at', 'feedback_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AIFeedback.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIFeedbackCreateSerializer
        return AIFeedbackSerializer
    
    def perform_create(self, serializer):
        # Generate result_id if not provided
        result_id = self.request.data.get('result_id') or str(uuid.uuid4())
        
        serializer.save(
            user=self.request.user,
            result_id=result_id,
        )
        
        # Update feedback counts on related AIResultLog if exists
        try:
            result_log = AIResultLog.objects.get(result_id=result_id)
            result_log.update_feedback_counts()
        except AIResultLog.DoesNotExist:
            pass
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get feedback statistics"""
        qs = self.get_queryset()
        
        # Overall stats
        total = qs.count()
        by_type = qs.values('feedback_type').annotate(count=Count('id'))
        by_result_type = qs.values('result_type').annotate(count=Count('id'))
        
        # Recent stats (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent = qs.filter(created_at__gte=thirty_days_ago)
        
        return Response({
            'total': total,
            'by_type': list(by_type),
            'by_result_type': list(by_result_type),
            'recent_count': recent.count(),
            'recent_by_type': list(recent.values('feedback_type').annotate(count=Count('id'))),
        })
    
    @action(detail=False, methods=['post'])
    def bulk_submit(self, request):
        """Submit multiple feedback items at once"""
        feedbacks = request.data.get('feedbacks', [])
        if not feedbacks:
            return Response(
                {'error': 'No feedbacks provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created = []
        errors = []
        
        for i, feedback_data in enumerate(feedbacks):
            serializer = AIFeedbackCreateSerializer(data=feedback_data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                created.append(serializer.data)
            else:
                errors.append({'index': i, 'errors': serializer.errors})
        
        return Response({
            'created': len(created),
            'errors': errors,
            'feedbacks': created,
        })


class AIResultLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI Result Logs
    
    Endpoints:
    - POST /results/ - Log a new AI result
    - GET /results/ - List results
    - GET /results/{id}/feedbacks/ - Get feedbacks for a result
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['result_id', 'result_type']
    ordering_fields = ['created_at', 'overall_confidence']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AIResultLog.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIResultLogCreateSerializer
        return AIResultLogSerializer
    
    def perform_create(self, serializer):
        # Generate unique result_id
        result_id = self.request.data.get('result_id') or str(uuid.uuid4())
        serializer.save(
            user=self.request.user,
            result_id=result_id,
        )
    
    @action(detail=True, methods=['get'])
    def feedbacks(self, request, pk=None):
        """Get all feedbacks for this result"""
        result = self.get_object()
        feedbacks = AIFeedback.objects.filter(result_id=result.result_id)
        serializer = AIFeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def accuracy_report(self, request):
        """Get accuracy report based on feedback"""
        qs = self.get_queryset()
        
        # Calculate accuracy metrics
        total_with_feedback = qs.filter(feedback_count__gt=0).count()
        
        results_with_positive = qs.filter(positive_feedback_count__gt=0).count()
        results_with_negative = qs.filter(negative_feedback_count__gt=0).count()
        
        # Average confidence by feedback type
        avg_confidence = qs.aggregate(
            overall_avg=Avg('overall_confidence'),
        )
        
        # By result type
        by_type = qs.values('result_type').annotate(
            count=Count('id'),
            avg_confidence=Avg('overall_confidence'),
            feedback_count=Count('id', filter=Q(feedback_count__gt=0)),
        )
        
        return Response({
            'total_results': qs.count(),
            'results_with_feedback': total_with_feedback,
            'results_with_positive_feedback': results_with_positive,
            'results_with_negative_feedback': results_with_negative,
            'average_confidence': avg_confidence['overall_avg'],
            'by_result_type': list(by_type),
        })
    
    @action(detail=True, methods=['post'])
    def add_reasoning(self, request, pk=None):
        """Add or update reasoning for a result"""
        result = self.get_object()
        
        reasoning = request.data.get('reasoning', {})
        classification_factors = request.data.get('classification_factors', [])
        alternatives = request.data.get('alternatives_considered', {})
        
        if reasoning:
            result.reasoning.update(reasoning)
        if classification_factors:
            result.classification_factors = classification_factors
        if alternatives:
            result.alternatives_considered.update(alternatives)
        
        result.save()
        
        return Response(AIResultLogSerializer(result).data)
