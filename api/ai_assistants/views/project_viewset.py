"""
Accounting Project ViewSet
會計專案視圖

API Endpoints:
- GET /api/v1/accounting-projects/ - List all projects
- POST /api/v1/accounting-projects/ - Create new project
- GET /api/v1/accounting-projects/{id}/ - Get project detail
- PATCH /api/v1/accounting-projects/{id}/ - Update project
- DELETE /api/v1/accounting-projects/{id}/ - Delete project
- GET /api/v1/accounting-projects/{id}/receipts/ - List project receipts
- GET /api/v1/accounting-projects/{id}/unrecognized/ - List unrecognized documents
- POST /api/v1/accounting-projects/{id}/bulk-upload/ - Bulk upload receipts
- GET /api/v1/field-extractions/{receipt_id}/ - Get field extractions for receipt
- POST /api/v1/field-extractions/correct/ - Correct extracted fields
"""

import logging
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated

from ai_assistants.models import (
    AccountingProject, Receipt, FieldExtraction,
    ReceiptStatus, ProjectStatus
)
from ai_assistants.serializers.accounting_serializer import (
    AccountingProjectListSerializer,
    AccountingProjectDetailSerializer,
    AccountingProjectCreateSerializer,
    AccountingProjectUpdateSerializer,
    ReceiptSerializer,
    UnrecognizedReceiptSerializer,
    FieldExtractionSerializer,
    FieldCorrectionSerializer,
    BulkFieldCorrectionSerializer,
    ManualClassificationSerializer,
    BulkStatusUpdateSerializer,
    BulkReceiptUploadSerializer,
)

logger = logging.getLogger(__name__)


class AccountingProjectViewSet(viewsets.ModelViewSet):
    """
    Accounting Project API ViewSet
    會計專案 API 視圖集
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """Filter projects by user access"""
        user = self.request.user
        # Users can see projects they own or are team members of
        return AccountingProject.objects.filter(
            Q(owner=user) | Q(team_members=user)
        ).distinct().select_related('company', 'owner').prefetch_related('team_members')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountingProjectListSerializer
        elif self.action == 'retrieve':
            return AccountingProjectDetailSerializer
        elif self.action == 'create':
            return AccountingProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AccountingProjectUpdateSerializer
        return AccountingProjectDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    # =========================================================================
    # Project Receipts / 專案收據
    # =========================================================================
    
    @action(detail=True, methods=['get'], url_path='receipts')
    def list_receipts(self, request, pk=None):
        """
        List all receipts for a project
        列出專案所有收據
        """
        project = self.get_object()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        queryset = project.receipts.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReceiptSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReceiptSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='unrecognized')
    def list_unrecognized(self, request, pk=None):
        """
        List unrecognized/pending review documents for a project
        列出專案中無法識別/待審核的文件
        """
        project = self.get_object()
        
        queryset = project.receipts.filter(
            status__in=[ReceiptStatus.UNRECOGNIZED, ReceiptStatus.PENDING_REVIEW]
        )
        
        serializer = UnrecognizedReceiptSerializer(queryset, many=True)
        return Response({
            'total': queryset.count(),
            'items': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='stats')
    def project_stats(self, request, pk=None):
        """
        Get project statistics
        獲取專案統計
        """
        project = self.get_object()
        
        # Receipt stats by status
        receipt_stats = project.receipts.values('status').annotate(
            count=Count('id')
        )
        
        # Receipt stats by category
        category_stats = project.receipts.exclude(
            status__in=[ReceiptStatus.UNRECOGNIZED, ReceiptStatus.ERROR]
        ).values('category').annotate(
            count=Count('id')
        )
        
        # Total amounts by category
        from django.db.models import Sum
        amount_stats = project.receipts.exclude(
            status__in=[ReceiptStatus.UNRECOGNIZED, ReceiptStatus.ERROR]
        ).values('category').annotate(
            total_amount=Sum('total_amount')
        )
        
        return Response({
            'project_id': project.id,
            'project_name': project.name,
            'total_receipts': project.receipts.count(),
            'status_breakdown': {s['status']: s['count'] for s in receipt_stats},
            'category_breakdown': {c['category']: c['count'] for c in category_stats},
            'amount_by_category': {a['category']: float(a['total_amount'] or 0) for a in amount_stats},
            'progress': project.progress,
            'is_overdue': project.is_overdue,
        })
    
    # =========================================================================
    # Bulk Upload / 批量上傳
    # =========================================================================
    
    @action(detail=True, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request, pk=None):
        """
        Bulk upload receipts to a project
        批量上傳收據到專案
        """
        project = self.get_object()
        serializer = BulkReceiptUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        files = data['files']
        language = data.get('language', 'auto')
        auto_categorize = data.get('auto_categorize', True)
        
        results = []
        errors = []
        
        for file in files:
            try:
                receipt = Receipt.objects.create(
                    project=project,
                    uploaded_by=request.user,
                    original_filename=file.name,
                    image=file,
                    status=ReceiptStatus.UPLOADED
                )
                results.append({
                    'filename': file.name,
                    'receipt_id': str(receipt.id),
                    'status': 'uploaded'
                })
            except Exception as e:
                logger.error(f"Error uploading file {file.name}: {e}")
                errors.append({
                    'filename': file.name,
                    'error': str(e)
                })
        
        return Response({
            'total_files': len(files),
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors,
            'message': f'Successfully uploaded {len(results)} of {len(files)} files'
        })
    
    # =========================================================================
    # Manual Classification / 手動分類
    # =========================================================================
    
    @action(detail=True, methods=['post'], url_path='classify')
    def manual_classify(self, request, pk=None):
        """
        Manually classify an unrecognized document
        手動分類無法識別的文件
        """
        project = self.get_object()
        serializer = ManualClassificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        receipt_id = data['receipt_id']
        
        try:
            receipt = project.receipts.get(id=receipt_id)
        except Receipt.DoesNotExist:
            return Response(
                {'error': 'Receipt not found in this project'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update receipt with manual classification
        if data.get('vendor_name'):
            receipt.vendor_name = data['vendor_name']
        if data.get('receipt_date'):
            receipt.receipt_date = data['receipt_date']
        if data.get('total_amount'):
            receipt.total_amount = data['total_amount']
        if data.get('category'):
            receipt.category = data['category']
        
        receipt.status = data.get('new_status', ReceiptStatus.PENDING_REVIEW)
        receipt.save()
        
        return Response(ReceiptSerializer(receipt).data)
    
    @action(detail=True, methods=['post'], url_path='bulk-status-update')
    def bulk_status_update(self, request, pk=None):
        """
        Bulk update status of receipts
        批量更新收據狀態
        """
        project = self.get_object()
        serializer = BulkStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        receipt_ids = data['receipt_ids']
        new_status = data['new_status']
        notes = data.get('notes', '')
        
        updated_count = project.receipts.filter(id__in=receipt_ids).update(
            status=new_status,
            updated_at=timezone.now()
        )
        
        return Response({
            'updated_count': updated_count,
            'new_status': new_status,
            'message': f'Successfully updated {updated_count} receipts'
        })


class FieldExtractionViewSet(viewsets.GenericViewSet):
    """
    Field Extraction API ViewSet
    欄位提取 API 視圖集
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FieldExtractionSerializer
    
    def get_queryset(self):
        return FieldExtraction.objects.all()
    
    @action(detail=False, methods=['get'], url_path='receipt/(?P<receipt_id>[^/.]+)')
    def by_receipt(self, request, receipt_id=None):
        """
        Get all field extractions for a receipt
        獲取收據的所有欄位提取
        """
        extractions = FieldExtraction.objects.filter(
            receipt_id=receipt_id
        ).order_by('field_name')
        
        serializer = FieldExtractionSerializer(extractions, many=True)
        
        # Calculate summary
        total = extractions.count()
        verified = extractions.filter(is_verified=True).count()
        needs_review = extractions.filter(confidence__lt=0.8, is_verified=False).count()
        
        return Response({
            'receipt_id': receipt_id,
            'total_fields': total,
            'verified_fields': verified,
            'needs_review': needs_review,
            'fields': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='correct')
    def correct_field(self, request):
        """
        Correct a single extracted field
        校正單個提取欄位
        """
        serializer = FieldCorrectionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            extraction = FieldExtraction.objects.get(id=data['field_id'])
        except FieldExtraction.DoesNotExist:
            return Response(
                {'error': 'Field extraction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        extraction.corrected_value = data['corrected_value']
        
        if data.get('mark_verified', True):
            extraction.is_verified = True
            extraction.verified_by = request.user
            extraction.verified_at = timezone.now()
        
        extraction.save()
        
        return Response(FieldExtractionSerializer(extraction).data)
    
    @action(detail=False, methods=['post'], url_path='bulk-correct')
    def bulk_correct(self, request):
        """
        Bulk correct multiple extracted fields
        批量校正多個提取欄位
        """
        serializer = BulkFieldCorrectionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        corrections = serializer.validated_data['corrections']
        results = []
        errors = []
        
        with transaction.atomic():
            for correction in corrections:
                try:
                    extraction = FieldExtraction.objects.get(id=correction['field_id'])
                    extraction.corrected_value = correction['corrected_value']
                    
                    if correction.get('mark_verified', True):
                        extraction.is_verified = True
                        extraction.verified_by = request.user
                        extraction.verified_at = timezone.now()
                    
                    extraction.save()
                    results.append({
                        'field_id': str(correction['field_id']),
                        'status': 'corrected'
                    })
                except FieldExtraction.DoesNotExist:
                    errors.append({
                        'field_id': str(correction['field_id']),
                        'error': 'Not found'
                    })
                except Exception as e:
                    errors.append({
                        'field_id': str(correction['field_id']),
                        'error': str(e)
                    })
        
        return Response({
            'total': len(corrections),
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        })
    
    @action(detail=False, methods=['post'], url_path='verify-all/(?P<receipt_id>[^/.]+)')
    def verify_all(self, request, receipt_id=None):
        """
        Mark all extractions for a receipt as verified
        將收據的所有提取標記為已驗證
        """
        updated_count = FieldExtraction.objects.filter(
            receipt_id=receipt_id,
            is_verified=False
        ).update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        
        return Response({
            'receipt_id': receipt_id,
            'verified_count': updated_count,
            'message': f'Verified {updated_count} field extractions'
        })


class UnrecognizedReceiptsViewSet(viewsets.GenericViewSet):
    """
    Unrecognized Receipts API ViewSet
    無法識別收據 API 視圖集
    
    Handles receipts that couldn't be automatically processed.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UnrecognizedReceiptSerializer
    
    def get_queryset(self):
        """Get unrecognized receipts accessible by user"""
        return Receipt.objects.filter(
            status=ReceiptStatus.UNRECOGNIZED
        ).select_related('project', 'uploaded_by').order_by('-created_at')
    
    def list(self, request):
        """
        List all unrecognized receipts
        列出所有無法識別的收據
        """
        queryset = self.get_queryset()
        
        # Filtering
        project_id = request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        reason = request.query_params.get('reason')
        if reason:
            queryset = queryset.filter(unrecognized_reason__icontains=reason)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UnrecognizedReceiptSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UnrecognizedReceiptSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        Get a single unrecognized receipt
        獲取單個無法識別的收據
        """
        try:
            receipt = Receipt.objects.get(
                id=pk,
                status=ReceiptStatus.UNRECOGNIZED
            )
        except Receipt.DoesNotExist:
            return Response(
                {'error': 'Unrecognized receipt not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UnrecognizedReceiptSerializer(receipt)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reclassify(self, request, pk=None):
        """
        Reclassify/process an unrecognized receipt manually
        手動重新分類無法識別的收據
        """
        try:
            receipt = Receipt.objects.get(
                id=pk,
                status=ReceiptStatus.UNRECOGNIZED
            )
        except Receipt.DoesNotExist:
            return Response(
                {'error': 'Unrecognized receipt not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ManualClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update receipt with manual data
        data = serializer.validated_data
        
        if 'vendor_name' in data:
            receipt.vendor_name = data['vendor_name']
        if 'receipt_date' in data:
            receipt.receipt_date = data['receipt_date']
        if 'total_amount' in data:
            receipt.total_amount = data['total_amount']
        if 'category' in data:
            receipt.category = data['category']
        
        receipt.status = data.get('new_status', ReceiptStatus.PENDING_REVIEW)
        receipt.save()
        
        return Response({
            'message': 'Receipt reclassified successfully',
            'receipt': ReceiptSerializer(receipt).data
        })
    
    @action(detail=False, methods=['post'], url_path='batch-reclassify')
    def batch_reclassify(self, request):
        """
        Batch update status of unrecognized receipts
        批量更新無法識別收據的狀態
        """
        serializer = BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        receipt_ids = serializer.validated_data['receipt_ids']
        new_status = serializer.validated_data['new_status']
        notes = serializer.validated_data.get('notes', '')
        
        with transaction.atomic():
            updated_count = Receipt.objects.filter(
                id__in=receipt_ids,
                status=ReceiptStatus.UNRECOGNIZED
            ).update(
                status=new_status,
                notes=notes
            )
        
        return Response({
            'updated_count': updated_count,
            'new_status': new_status,
            'message': f'Successfully reclassified {updated_count} receipts'
        })
