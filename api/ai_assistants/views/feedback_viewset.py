"""
AI Feedback API ViewSet
=======================
Handle feedback submissions and result logging.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.db.models import Count, Avg, Q, Sum, F, Max
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


# =================================================================
# RAG Observability ViewSets
# =================================================================

class AIRequestLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI Request Logs - Token usage, latency tracking
    
    Endpoints:
    - POST /ai-requests/ - Log a new AI request
    - GET /ai-requests/ - List requests with filters
    - GET /ai-requests/stats/ - Get request statistics
    - GET /ai-requests/cost-breakdown/ - Get cost breakdown by model/provider
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['request_id', 'provider', 'model', 'assistant_type']
    ordering_fields = ['created_at', 'latency_ms', 'total_tokens', 'estimated_cost_cents']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = AIRequestLog.objects.all()
        
        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Optional filters
        provider = self.request.query_params.get('provider')
        model = self.request.query_params.get('model')
        request_type = self.request.query_params.get('request_type')
        status_filter = self.request.query_params.get('status')
        assistant_type = self.request.query_params.get('assistant_type')
        days = self.request.query_params.get('days', 7)
        
        if provider:
            queryset = queryset.filter(provider=provider)
        if model:
            queryset = queryset.filter(model=model)
        if request_type:
            queryset = queryset.filter(request_type=request_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if assistant_type:
            queryset = queryset.filter(assistant_type=assistant_type)
        
        # Date filter
        try:
            days = int(days)
            if days > 0:
                since = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=since)
        except ValueError:
            pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIRequestLogCreateSerializer
        return AIRequestLogSerializer
    
    def perform_create(self, serializer):
        request_id = self.request.data.get('request_id') or str(uuid.uuid4())
        serializer.save(
            user=self.request.user,
            request_id=request_id,
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get request statistics for the filtered period"""
        qs = self.get_queryset()
        
        stats = qs.aggregate(
            total_requests=Count('id'),
            successful_requests=Count('id', filter=Q(status='SUCCESS')),
            failed_requests=Count('id', filter=Q(status='FAILED')),
            total_tokens=Sum('total_tokens'),
            total_prompt_tokens=Sum('prompt_tokens'),
            total_completion_tokens=Sum('completion_tokens'),
            total_cost_cents=Sum('estimated_cost_cents'),
            avg_latency=Avg('latency_ms'),
            avg_tokens=Avg('total_tokens'),
        )
        
        # Calculate success rate
        if stats['total_requests']:
            stats['success_rate'] = round(
                stats['successful_requests'] / stats['total_requests'] * 100, 2
            )
        else:
            stats['success_rate'] = 0
        
        # Convert cost to USD
        stats['total_cost_usd'] = stats['total_cost_cents'] / 100 if stats['total_cost_cents'] else 0
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def cost_breakdown(self, request):
        """Get cost breakdown by provider and model"""
        qs = self.get_queryset()
        
        by_provider = list(qs.values('provider').annotate(
            request_count=Count('id'),
            total_tokens=Sum('total_tokens'),
            total_cost_cents=Sum('estimated_cost_cents'),
        ).order_by('-total_cost_cents'))
        
        by_model = list(qs.values('provider', 'model').annotate(
            request_count=Count('id'),
            total_tokens=Sum('total_tokens'),
            total_cost_cents=Sum('estimated_cost_cents'),
            avg_latency=Avg('latency_ms'),
        ).order_by('-total_cost_cents')[:10])
        
        by_type = list(qs.values('request_type').annotate(
            request_count=Count('id'),
            total_tokens=Sum('total_tokens'),
            total_cost_cents=Sum('estimated_cost_cents'),
        ).order_by('-request_count'))
        
        return Response({
            'by_provider': by_provider,
            'by_model': by_model,
            'by_type': by_type,
        })
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get daily trends for requests, tokens, and cost"""
        qs = self.get_queryset()
        
        daily_stats = list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                requests=Count('id'),
                tokens=Sum('total_tokens'),
                cost_cents=Sum('estimated_cost_cents'),
                avg_latency=Avg('latency_ms'),
                success_count=Count('id', filter=Q(status='SUCCESS')),
            )
            .order_by('date')
        )
        
        return Response(daily_stats)


class VectorSearchLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vector Search Logs - RAG search performance
    
    Endpoints:
    - POST /vector-searches/ - Log a vector search
    - GET /vector-searches/ - List searches with filters
    - GET /vector-searches/quality-stats/ - Get quality metrics
    - GET /vector-searches/failing-queries/ - Get queries with poor results
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['query_text', 'collection_name']
    ordering_fields = ['created_at', 'results_count', 'avg_similarity_score', 'total_latency_ms']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = VectorSearchLog.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Optional filters
        collection = self.request.query_params.get('collection')
        min_similarity = self.request.query_params.get('min_similarity')
        max_similarity = self.request.query_params.get('max_similarity')
        empty_only = self.request.query_params.get('empty_only')
        days = self.request.query_params.get('days', 7)
        
        if collection:
            queryset = queryset.filter(collection_name=collection)
        if min_similarity:
            queryset = queryset.filter(avg_similarity_score__gte=float(min_similarity))
        if max_similarity:
            queryset = queryset.filter(avg_similarity_score__lte=float(max_similarity))
        if empty_only and empty_only.lower() == 'true':
            queryset = queryset.filter(results_count=0)
        
        try:
            days = int(days)
            if days > 0:
                since = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=since)
        except ValueError:
            pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VectorSearchLogCreateSerializer
        return VectorSearchLogSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def quality_stats(self, request):
        """Get quality statistics for vector searches"""
        qs = self.get_queryset()
        
        stats = qs.aggregate(
            total_searches=Count('id'),
            empty_searches=Count('id', filter=Q(results_count=0)),
            avg_results=Avg('results_count'),
            avg_similarity=Avg('avg_similarity_score'),
            avg_latency=Avg('total_latency_ms'),
            good_quality=Count('id', filter=Q(avg_similarity_score__gte=0.8)),
            fair_quality=Count('id', filter=Q(avg_similarity_score__gte=0.6, avg_similarity_score__lt=0.8)),
            poor_quality=Count('id', filter=Q(avg_similarity_score__lt=0.6, avg_similarity_score__isnull=False)),
        )
        
        # Calculate percentages
        total = stats['total_searches'] or 1
        stats['empty_rate'] = round(stats['empty_searches'] / total * 100, 2)
        stats['good_rate'] = round(stats['good_quality'] / total * 100, 2)
        stats['fair_rate'] = round(stats['fair_quality'] / total * 100, 2)
        stats['poor_rate'] = round(stats['poor_quality'] / total * 100, 2)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def failing_queries(self, request):
        """Get queries with poor or no results"""
        qs = self.get_queryset().filter(
            Q(results_count=0) | Q(avg_similarity_score__lt=0.6)
        )
        
        # Group by query text and count occurrences
        failing = list(
            qs.values('query_text')
            .annotate(
                failure_count=Count('id'),
                avg_similarity=Avg('avg_similarity_score'),
                last_occurred=models.Max('created_at'),
            )
            .order_by('-failure_count')[:20]
        )
        
        return Response(failing)
    
    @action(detail=False, methods=['get'])
    def collection_stats(self, request):
        """Get stats by collection"""
        qs = self.get_queryset()
        
        by_collection = list(
            qs.values('collection_name')
            .annotate(
                search_count=Count('id'),
                avg_results=Avg('results_count'),
                avg_similarity=Avg('avg_similarity_score'),
                avg_latency=Avg('total_latency_ms'),
                empty_count=Count('id', filter=Q(results_count=0)),
            )
            .order_by('-search_count')
        )
        
        return Response(by_collection)


class KnowledgeGapLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Knowledge Gap Logs
    
    Endpoints:
    - POST /knowledge-gaps/ - Log a knowledge gap
    - GET /knowledge-gaps/ - List gaps with filters
    - POST /knowledge-gaps/{id}/resolve/ - Mark gap as resolved
    - GET /knowledge-gaps/summary/ - Get gap summary by type
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['query_text', 'expected_topic']
    ordering_fields = ['created_at', 'occurrence_count', 'priority']
    ordering = ['-occurrence_count', '-created_at']
    
    def get_queryset(self):
        queryset = KnowledgeGapLog.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Optional filters
        gap_type = self.request.query_params.get('gap_type')
        priority = self.request.query_params.get('priority')
        is_resolved = self.request.query_params.get('is_resolved')
        
        if gap_type:
            queryset = queryset.filter(gap_type=gap_type)
        if priority:
            queryset = queryset.filter(priority=priority)
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KnowledgeGapCreateSerializer
        if self.action == 'resolve':
            return KnowledgeGapResolveSerializer
        return KnowledgeGapLogSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark a knowledge gap as resolved"""
        gap = self.get_object()
        serializer = KnowledgeGapResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        gap.is_resolved = serializer.validated_data.get('is_resolved', True)
        gap.resolution_notes = serializer.validated_data['resolution_notes']
        gap.resolved_by = request.user
        gap.resolved_at = timezone.now()
        gap.save()
        
        return Response(KnowledgeGapLogSerializer(gap).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of knowledge gaps"""
        qs = self.get_queryset()
        
        summary = {
            'total': qs.count(),
            'unresolved': qs.filter(is_resolved=False).count(),
            'by_type': list(
                qs.values('gap_type')
                .annotate(count=Count('id'), total_occurrences=Sum('occurrence_count'))
                .order_by('-count')
            ),
            'by_priority': list(
                qs.filter(is_resolved=False)
                .values('priority')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'top_gaps': list(
                qs.filter(is_resolved=False)
                .order_by('-occurrence_count')[:10]
                .values('id', 'query_text', 'gap_type', 'priority', 'occurrence_count')
            ),
        }
        
        return Response(summary)


class AIUsageSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AI Usage Summaries (read-only)
    
    Endpoints:
    - GET /usage-summary/ - List usage summaries
    - GET /usage-summary/{date}/ - Get summary for specific date
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AIUsageSummarySerializer
    ordering = ['-date']
    
    def get_queryset(self):
        queryset = AIUsageSummary.objects.all()
        
        # Filter by period type
        period_type = self.request.query_params.get('period_type', 'DAILY')
        queryset = queryset.filter(period_type=period_type)
        
        # Date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset


class RAGObservabilityDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for RAG Observability Dashboard
    
    Endpoints:
    - GET /rag-dashboard/ - Get comprehensive dashboard data
    - GET /rag-dashboard/realtime/ - Get real-time metrics
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RAGObservabilityDashboardSerializer
    
    @action(detail=False, methods=['get'])
    def index(self, request):
        """Get comprehensive RAG observability dashboard data"""
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        
        # AI Request stats
        request_stats = AIRequestLog.objects.filter(created_at__gte=since).aggregate(
            total_requests=Count('id'),
            successful=Count('id', filter=Q(status='SUCCESS')),
            total_tokens=Sum('total_tokens'),
            total_cost_cents=Sum('estimated_cost_cents'),
            avg_latency=Avg('latency_ms'),
        )
        
        # Vector search stats
        search_stats = VectorSearchLog.objects.filter(created_at__gte=since).aggregate(
            total_searches=Count('id'),
            avg_similarity=Avg('avg_similarity_score'),
            empty_searches=Count('id', filter=Q(results_count=0)),
        )
        
        # Knowledge gaps
        gap_stats = KnowledgeGapLog.objects.filter(created_at__gte=since).aggregate(
            total_gaps=Count('id'),
            unresolved=Count('id', filter=Q(is_resolved=False)),
        )
        
        # Trends
        requests_trend = list(
            AIRequestLog.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(value=Count('id'))
            .order_by('date')
        )
        
        tokens_trend = list(
            AIRequestLog.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(value=Sum('total_tokens'))
            .order_by('date')
        )
        
        # Top failing queries
        top_failing = list(
            VectorSearchLog.objects.filter(
                created_at__gte=since,
                avg_similarity_score__lt=0.6
            )
            .values('query_text')
            .annotate(count=Count('id'), avg_sim=Avg('avg_similarity_score'))
            .order_by('-count')[:5]
        )
        
        # Top knowledge gaps
        top_gaps = list(
            KnowledgeGapLog.objects.filter(is_resolved=False)
            .order_by('-occurrence_count')[:5]
            .values('query_text', 'gap_type', 'occurrence_count')
        )
        
        # Usage by model
        usage_by_model = dict(
            AIRequestLog.objects.filter(created_at__gte=since)
            .values('model')
            .annotate(count=Count('id'))
            .values_list('model', 'count')
        )
        
        # Usage by assistant
        usage_by_assistant = dict(
            AIRequestLog.objects.filter(created_at__gte=since, assistant_type__isnull=False)
            .exclude(assistant_type='')
            .values('assistant_type')
            .annotate(count=Count('id'))
            .values_list('assistant_type', 'count')
        )
        
        success_rate = 0
        if request_stats['total_requests']:
            success_rate = round(
                request_stats['successful'] / request_stats['total_requests'] * 100, 2
            )
        
        return Response({
            'total_requests': request_stats['total_requests'] or 0,
            'total_tokens': request_stats['total_tokens'] or 0,
            'total_cost_usd': (request_stats['total_cost_cents'] or 0) / 100,
            'avg_latency_ms': int(request_stats['avg_latency'] or 0),
            'success_rate': success_rate,
            'total_vector_searches': search_stats['total_searches'] or 0,
            'avg_similarity_score': round(search_stats['avg_similarity'] or 0, 3),
            'knowledge_gaps_count': gap_stats['total_gaps'] or 0,
            'unresolved_gaps_count': gap_stats['unresolved'] or 0,
            'requests_trend': requests_trend,
            'tokens_trend': tokens_trend,
            'latency_trend': [],  # Simplified
            'cost_trend': [],  # Simplified
            'top_failing_queries': top_failing,
            'top_knowledge_gaps': top_gaps,
            'usage_by_model': usage_by_model,
            'usage_by_assistant': usage_by_assistant,
        })
