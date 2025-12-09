"""
Accounting Assistant ViewSet
會計助手視圖

API Endpoints:
- POST /api/v1/accounting-assistant/upload/ - Upload and analyze receipt
- GET /api/v1/accounting-assistant/receipts/ - List all receipts
- GET /api/v1/accounting-assistant/receipts/{id}/ - Get receipt detail
- PATCH /api/v1/accounting-assistant/receipts/{id}/ - Update receipt
- POST /api/v1/accounting-assistant/receipts/{id}/approve/ - Approve receipt
- POST /api/v1/accounting-assistant/receipts/{id}/create-journal/ - Create journal entry
- POST /api/v1/accounting-assistant/compare/ - Compare Excel with database
- POST /api/v1/accounting-assistant/reports/ - Generate expense report
- GET /api/v1/accounting-assistant/reports/ - List reports
- POST /api/v1/accounting-assistant/ai-query/ - AI query about accounting
"""

import base64
import uuid
from datetime import datetime, date
from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from django.db import models
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.core.files.base import ContentFile

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated

from ai_assistants.models import Receipt, ReceiptComparison, ExpenseReport, ReceiptStatus, ExpenseCategory
from ai_assistants.serializers.accounting_serializer import (
    ReceiptUploadSerializer,
    ReceiptSerializer,
    ReceiptUpdateSerializer,
    ReceiptProcessResultSerializer,
    ExcelCompareSerializer,
    ReceiptComparisonSerializer,
    ExpenseReportCreateSerializer,
    ExpenseReportSerializer,
    AIQuerySerializer,
)
from ai_assistants.services.accounting_service import (
    analyze_receipt_image,
    categorize_expense,
    generate_double_entry,
    get_ai_suggestions,
    process_receipt_full,
    generate_expense_report_excel,
    compare_excel_with_database,
    get_comparison_ai_analysis,
)
from ai_assistants.services.journal_entry_service import (
    JournalEntryService,
    create_journal_from_receipt,
    approve_receipt_with_journal,
    batch_create_journals,
)
from ai_assistants.services.anomaly_detection_service import (
    AnomalyDetectionService,
    detect_receipt_anomalies,
    get_anomaly_summary,
)
from ai_assistants.services.vendor_recognition_service import (
    VendorRecognitionService,
    find_or_create_vendor,
    suggest_vendor_category,
    process_vendor_auto,
)
from ai_assistants.services.recurring_expense_service import (
    RecurringExpenseService,
    detect_recurring,
    predict_expenses,
    get_recurring_report,
)


class AccountingAssistantViewSet(viewsets.ViewSet):
    """
    Accounting Assistant API ViewSet
    會計助手 API 視圖集
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ReceiptUploadSerializer
    
    # =========================================================================
    # Receipt Upload and Analysis / 收據上傳和分析
    # =========================================================================
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_receipt(self, request):
        """
        Upload and analyze a receipt image
        上傳並分析收據圖片
        """
        serializer = ReceiptUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        language = data.get('language', 'auto')
        auto_categorize = data.get('auto_categorize', True)
        auto_journal = data.get('auto_journal', False)
        
        # Get image as base64
        if data.get('image'):
            image_file = data['image']
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            image_file.seek(0)  # Reset file pointer
            original_filename = image_file.name
        else:
            image_base64 = data['image_base64']
            original_filename = 'uploaded_image.jpg'
        
        # Create receipt record
        receipt = Receipt.objects.create(
            uploaded_by=request.user,
            original_filename=original_filename,
            image_base64=image_base64,
            status=ReceiptStatus.ANALYZING,
        )
        
        # Save image file if provided
        if data.get('image'):
            receipt.image = data['image']
            receipt.save()
        
        try:
            # Process receipt
            result = process_receipt_full(image_base64, language, auto_save=False)
            
            if result.get('status') == 'error':
                receipt.status = ReceiptStatus.ERROR
                receipt.ai_raw_response = result
                receipt.save()
                return Response({
                    'receipt_id': str(receipt.id),
                    'status': 'error',
                    'error': result.get('error'),
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update receipt with extracted data
            receipt_data = result.get('receipt_data', {})
            
            receipt.vendor_name = receipt_data.get('vendor_name')
            receipt.vendor_address = receipt_data.get('vendor_address')
            receipt.vendor_phone = receipt_data.get('vendor_phone')
            receipt.vendor_tax_id = receipt_data.get('vendor_tax_id')
            receipt.receipt_number = receipt_data.get('receipt_number')
            
            if receipt_data.get('receipt_date'):
                try:
                    receipt.receipt_date = datetime.strptime(
                        receipt_data['receipt_date'], '%Y-%m-%d'
                    ).date()
                except (ValueError, TypeError):
                    pass
            
            receipt.currency = receipt_data.get('currency', 'TWD')
            receipt.subtotal = Decimal(str(receipt_data.get('subtotal', 0) or 0))
            receipt.tax_amount = Decimal(str(receipt_data.get('tax_amount', 0) or 0))
            receipt.tax_rate = Decimal(str(receipt_data.get('tax_rate', 5) or 5))
            receipt.discount_amount = Decimal(str(receipt_data.get('discount_amount', 0) or 0))
            receipt.total_amount = Decimal(str(receipt_data.get('total_amount', 0) or 0))
            receipt.payment_method = receipt_data.get('payment_method', 'CASH')
            receipt.items = receipt_data.get('items', [])
            
            receipt.ai_raw_response = receipt_data
            receipt.ai_confidence_score = receipt_data.get('confidence_score', 0)
            receipt.ai_warnings = receipt_data.get('warnings', [])
            receipt.detected_language = receipt_data.get('detected_language', 'auto')
            
            # Categorization
            if auto_categorize:
                categorization = result.get('categorization', {})
                category_suggestion = receipt_data.get('category_suggestion', 'OTHER')
                receipt.category = category_suggestion if category_suggestion in ExpenseCategory.values else ExpenseCategory.OTHER
                receipt.status = ReceiptStatus.CATEGORIZED
            else:
                receipt.status = ReceiptStatus.ANALYZED
            
            # Journal entry
            if auto_journal:
                journal_entry = result.get('journal_entry', {})
                receipt.journal_entry_data = journal_entry
                receipt.status = ReceiptStatus.JOURNAL_CREATED
            
            # AI suggestions
            ai_suggestions = result.get('ai_suggestions', {})
            receipt.ai_suggestions = ai_suggestions.get('suggestions', [])
            
            receipt.save()
            
            return Response({
                'receipt_id': str(receipt.id),
                'status': 'success',
                'receipt': ReceiptSerializer(receipt).data,
                'processing_result': result,
            })
            
        except Exception as e:
            receipt.status = ReceiptStatus.ERROR
            receipt.ai_raw_response = {'error': str(e)}
            receipt.save()
            return Response({
                'receipt_id': str(receipt.id),
                'status': 'error',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='receipts')
    def list_receipts(self, request):
        """
        List all receipts
        列出所有收據
        """
        queryset = Receipt.objects.filter(uploaded_by=request.user)
        
        # Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category_filter = request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(receipt_date__gte=date_from)
        
        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(receipt_date__lte=date_to)
        
        serializer = ReceiptSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='receipt')
    def get_receipt(self, request, pk=None):
        """
        Get receipt detail
        獲取收據詳情
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReceiptSerializer(receipt)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], url_path='update-receipt')
    def update_receipt(self, request, pk=None):
        """
        Update receipt data
        更新收據資料
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReceiptUpdateSerializer(receipt, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ReceiptSerializer(receipt).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_receipt(self, request, pk=None):
        """
        Approve a receipt and optionally create journal entry
        核准收據並可選擇自動建立分錄
        """
        try:
            receipt = Receipt.objects.get(pk=pk)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Options from request
        auto_journal = request.data.get('auto_journal', True)  # Default to auto create journal
        auto_post = request.data.get('auto_post', False)
        notes = request.data.get('notes', '')
        
        if auto_journal:
            # Use new service to approve and create journal entry
            journal_entry, error = approve_receipt_with_journal(
                receipt=receipt,
                user=request.user,
                notes=notes,
                auto_post=auto_post
            )
            
            if error:
                return Response({
                    'status': 'error',
                    'error': error,
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'status': 'approved',
                'journal_created': True,
                'journal_entry': {
                    'id': str(journal_entry.id),
                    'entry_number': journal_entry.entry_number,
                    'date': str(journal_entry.date),
                    'total_debit': float(journal_entry.total_debit),
                    'total_credit': float(journal_entry.total_credit),
                    'status': journal_entry.status,
                },
                'receipt': ReceiptSerializer(receipt).data
            })
        else:
            # Just approve without creating journal
            receipt.status = ReceiptStatus.APPROVED
            receipt.reviewed_by = request.user
            receipt.reviewed_at = timezone.now()
            receipt.notes = notes
            receipt.save()
            
            return Response({
                'status': 'approved',
                'journal_created': False,
                'receipt': ReceiptSerializer(receipt).data
            })
    
    @action(detail=True, methods=['post'], url_path='create-journal')
    def create_journal_entry(self, request, pk=None):
        """
        Create journal entry from receipt (writes to actual accounting.JournalEntry)
        從收據建立會計分錄（寫入實際的 accounting.JournalEntry）
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if journal already exists
        if receipt.journal_entry:
            return Response({
                'status': 'exists',
                'message': 'Journal entry already exists for this receipt',
                'journal_entry': {
                    'id': str(receipt.journal_entry.id),
                    'entry_number': receipt.journal_entry.entry_number,
                },
                'receipt': ReceiptSerializer(receipt).data
            })
        
        # Options
        auto_post = request.data.get('auto_post', False)
        
        # Create actual journal entry using new service
        journal_entry, error = create_journal_from_receipt(
            receipt=receipt,
            user=request.user,
            auto_post=auto_post
        )
        
        if error:
            return Response({
                'status': 'error',
                'error': error,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'journal_created',
            'journal_entry': {
                'id': str(journal_entry.id),
                'entry_number': journal_entry.entry_number,
                'date': str(journal_entry.date),
                'description': journal_entry.description,
                'total_debit': float(journal_entry.total_debit),
                'total_credit': float(journal_entry.total_credit),
                'status': journal_entry.status,
                'lines': [
                    {
                        'account_code': line.account.code,
                        'account_name': line.account.name,
                        'debit': float(line.debit),
                        'credit': float(line.credit),
                    }
                    for line in journal_entry.lines.all()
                ]
            },
            'receipt': ReceiptSerializer(receipt).data
        })
    
    @action(detail=True, methods=['post'], url_path='ai-review')
    def ai_review_receipt(self, request, pk=None):
        """
        Get AI review and suggestions for a receipt
        獲取收據的AI審核和建議
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        receipt_data = receipt.ai_raw_response or {
            'vendor_name': receipt.vendor_name,
            'receipt_number': receipt.receipt_number,
            'receipt_date': str(receipt.receipt_date) if receipt.receipt_date else None,
            'total_amount': float(receipt.total_amount),
            'tax_amount': float(receipt.tax_amount),
            'category_suggestion': receipt.category,
        }
        
        journal_entry = receipt.journal_entry_data or {}
        
        ai_review = get_ai_suggestions(receipt_data, journal_entry)
        
        # Update receipt with new suggestions
        receipt.ai_suggestions = ai_review.get('suggestions', [])
        receipt.save()
        
        return Response({
            'ai_review': ai_review,
            'receipt': ReceiptSerializer(receipt).data
        })
    
    # =========================================================================
    # Batch Processing / 批量處理
    # =========================================================================
    
    @action(detail=False, methods=['post'], url_path='batch-create-journals')
    def batch_create_journals(self, request):
        """
        Create journal entries for multiple receipts
        批量建立分錄
        """
        receipt_ids = request.data.get('receipt_ids', [])
        auto_post = request.data.get('auto_post', False)
        
        if not receipt_ids:
            return Response({
                'status': 'error',
                'error': 'No receipt IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get receipts
        receipts = Receipt.objects.filter(
            id__in=receipt_ids,
            uploaded_by=request.user,
            journal_entry__isnull=True  # Only receipts without journal entry
        )
        
        if not receipts.exists():
            return Response({
                'status': 'error',
                'error': 'No valid receipts found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Batch create
        results = batch_create_journals(
            receipts=list(receipts),
            user=request.user,
            auto_post=auto_post
        )
        
        return Response({
            'status': 'completed',
            'results': results
        })
    
    @action(detail=False, methods=['post'], url_path='batch-approve')
    def batch_approve(self, request):
        """
        Approve multiple receipts and create journal entries
        批量核准收據並建立分錄
        """
        receipt_ids = request.data.get('receipt_ids', [])
        auto_journal = request.data.get('auto_journal', True)
        auto_post = request.data.get('auto_post', False)
        
        if not receipt_ids:
            return Response({
                'status': 'error',
                'error': 'No receipt IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        receipts = Receipt.objects.filter(
            id__in=receipt_ids,
            uploaded_by=request.user
        )
        
        results = {
            'success': [],
            'failed': [],
            'total': receipts.count()
        }
        
        for receipt in receipts:
            try:
                if auto_journal:
                    journal_entry, error = approve_receipt_with_journal(
                        receipt=receipt,
                        user=request.user,
                        auto_post=auto_post
                    )
                    if error:
                        results['failed'].append({
                            'receipt_id': str(receipt.id),
                            'error': error
                        })
                    else:
                        results['success'].append({
                            'receipt_id': str(receipt.id),
                            'journal_entry_id': str(journal_entry.id),
                            'entry_number': journal_entry.entry_number
                        })
                else:
                    receipt.status = ReceiptStatus.APPROVED
                    receipt.reviewed_by = request.user
                    receipt.reviewed_at = timezone.now()
                    receipt.save()
                    results['success'].append({
                        'receipt_id': str(receipt.id),
                        'journal_entry_id': None
                    })
            except Exception as e:
                results['failed'].append({
                    'receipt_id': str(receipt.id),
                    'error': str(e)
                })
        
        results['success_count'] = len(results['success'])
        results['failed_count'] = len(results['failed'])
        
        return Response({
            'status': 'completed',
            'results': results
        })
    
    @action(detail=True, methods=['post'], url_path='post-journal')
    def post_journal_entry(self, request, pk=None):
        """
        Post a journal entry (update account balances)
        過帳分錄（更新科目餘額）
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not receipt.journal_entry:
            return Response({
                'status': 'error',
                'error': 'No journal entry exists for this receipt'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = JournalEntryService(user=request.user)
        success, error = service.post_journal_entry(receipt.journal_entry, request.user)
        
        if not success:
            return Response({
                'status': 'error',
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        receipt.refresh_from_db()
        
        return Response({
            'status': 'posted',
            'journal_entry': {
                'id': str(receipt.journal_entry.id),
                'entry_number': receipt.journal_entry.entry_number,
                'status': receipt.journal_entry.status,
            },
            'receipt': ReceiptSerializer(receipt).data
        })
    
    @action(detail=True, methods=['post'], url_path='void-journal')
    def void_journal_entry(self, request, pk=None):
        """
        Void a journal entry
        作廢分錄
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not receipt.journal_entry:
            return Response({
                'status': 'error',
                'error': 'No journal entry exists for this receipt'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', '')
        
        service = JournalEntryService(user=request.user)
        success, error = service.void_journal_entry(receipt.journal_entry, request.user, reason)
        
        if not success:
            return Response({
                'status': 'error',
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        receipt.refresh_from_db()
        
        return Response({
            'status': 'voided',
            'receipt': ReceiptSerializer(receipt).data
        })
    
    # =========================================================================
    # Anomaly Detection / 異常檢測
    # =========================================================================
    
    @action(detail=True, methods=['get'], url_path='detect-anomalies')
    def detect_anomalies(self, request, pk=None):
        """
        Detect anomalies in a receipt
        檢測收據異常
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        anomalies = detect_receipt_anomalies(receipt, user=request.user)
        
        # Optional AI analysis
        include_ai = request.query_params.get('include_ai', 'false').lower() == 'true'
        ai_analysis = None
        
        if include_ai and anomalies:
            service = AnomalyDetectionService(user=request.user)
            ai_analysis = service.ai_analyze_anomalies(receipt, anomalies)
        
        return Response({
            'receipt_id': str(receipt.id),
            'anomalies_count': len(anomalies),
            'anomalies': anomalies,
            'ai_analysis': ai_analysis
        })
    
    @action(detail=False, methods=['get'], url_path='anomaly-summary')
    def get_anomaly_summary(self, request):
        """
        Get anomaly summary for user
        獲取用戶異常摘要
        """
        days = int(request.query_params.get('days', 30))
        summary = get_anomaly_summary(request.user, days)
        
        return Response(summary)
    
    # =========================================================================
    # Vendor Recognition / 供應商辨識
    # =========================================================================
    
    @action(detail=True, methods=['post'], url_path='process-vendor')
    def process_vendor(self, request, pk=None):
        """
        Auto-process vendor from receipt
        自動處理收據的供應商
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        result = process_vendor_auto(receipt)
        
        return Response({
            'receipt_id': str(receipt.id),
            'vendor_result': result
        })
    
    @action(detail=False, methods=['post'], url_path='find-vendor')
    def find_vendor(self, request):
        """
        Find matching vendor from database
        從資料庫找尋配對供應商
        """
        vendor_name = request.data.get('vendor_name', '')
        tax_id = request.data.get('tax_id', '')
        
        service = VendorRecognitionService(user=request.user)
        
        # Find exact match
        contact = service.find_matching_contact(vendor_name, tax_id)
        
        if contact:
            return Response({
                'found': True,
                'contact': {
                    'id': str(contact.id),
                    'company_name': contact.company_name,
                    'contact_name': contact.contact_name,
                    'tax_number': contact.tax_number,
                    'contact_type': contact.contact_type
                }
            })
        
        # Get suggestions
        suggestions = service.suggest_matching_contacts(vendor_name)
        
        return Response({
            'found': False,
            'suggestions': suggestions
        })
    
    @action(detail=False, methods=['get'], url_path='suggest-category')
    def suggest_category(self, request):
        """
        Suggest category based on vendor history
        根據供應商歷史建議分類
        """
        vendor_name = request.query_params.get('vendor_name', '')
        
        if not vendor_name:
            return Response({'error': 'vendor_name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        category = suggest_vendor_category(vendor_name)
        
        service = VendorRecognitionService()
        stats = service.get_vendor_statistics(vendor_name=vendor_name)
        
        return Response({
            'vendor_name': vendor_name,
            'suggested_category': category,
            'vendor_stats': {
                'total_transactions': stats.get('total_transactions', 0),
                'total_amount': float(stats.get('total_amount', 0) or 0),
                'category_breakdown': stats.get('category_breakdown', [])
            }
        })
    
    # =========================================================================
    # Recurring Expenses / 重複費用
    # =========================================================================
    
    @action(detail=False, methods=['get'], url_path='recurring-expenses')
    def get_recurring_expenses(self, request):
        """
        Detect and list recurring expenses
        檢測並列出重複費用
        """
        months = int(request.query_params.get('months', 12))
        
        recurring = detect_recurring(request.user, months)
        
        return Response({
            'recurring_count': len(recurring),
            'recurring_expenses': recurring,
            'analysis_period_months': months
        })
    
    @action(detail=False, methods=['get'], url_path='recurring-summary')
    def get_recurring_summary(self, request):
        """
        Get recurring expense summary
        獲取重複費用摘要
        """
        months = int(request.query_params.get('months', 12))
        
        summary = get_recurring_report(request.user, months)
        
        return Response(summary)
    
    @action(detail=False, methods=['get'], url_path='predict-expenses')
    def predict_future_expenses(self, request):
        """
        Predict future expenses based on recurring patterns
        根據重複模式預測未來費用
        """
        months_ahead = int(request.query_params.get('months', 3))
        
        predictions = predict_expenses(request.user, months_ahead)
        
        return Response(predictions)
    
    @action(detail=False, methods=['get'], url_path='recurring-analysis')
    def ai_recurring_analysis(self, request):
        """
        AI analysis of recurring expenses
        AI分析重複費用
        """
        months = int(request.query_params.get('months', 12))
        
        service = RecurringExpenseService(user=request.user)
        analysis = service.ai_analyze_recurring(request.user, months)
        
        return Response(analysis)
    
    # =========================================================================
    # Excel Comparison / Excel 對比
    # =========================================================================
    
    @action(detail=False, methods=['post'], url_path='compare')
    def compare_excel(self, request):
        """
        Compare uploaded Excel with database records
        比對上傳的Excel和資料庫記錄
        """
        serializer = ExcelCompareSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        excel_file = serializer.validated_data['excel_file']
        date_from = serializer.validated_data.get('date_from')
        date_to = serializer.validated_data.get('date_to')
        
        # Get database records
        queryset = Receipt.objects.filter(uploaded_by=request.user)
        if date_from:
            queryset = queryset.filter(receipt_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(receipt_date__lte=date_to)
        
        db_records = list(queryset.values(
            'receipt_number', 'vendor_name', 'receipt_date',
            'total_amount', 'tax_amount', 'category'
        ))
        
        # Read Excel file
        excel_content = excel_file.read()
        
        # Compare
        try:
            comparison_result = compare_excel_with_database(excel_content, db_records)
            ai_analysis = get_comparison_ai_analysis(comparison_result)
        except Exception as e:
            return Response({
                'error': f'Failed to compare: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save comparison record
        comparison = ReceiptComparison.objects.create(
            created_by=request.user,
            excel_filename=excel_file.name,
            total_excel_records=comparison_result.get('total_excel_records', 0),
            total_db_records=comparison_result.get('total_db_records', 0),
            matched_count=comparison_result.get('matched_count', 0),
            missing_in_db_count=comparison_result.get('missing_in_db_count', 0),
            missing_in_excel_count=comparison_result.get('missing_in_excel_count', 0),
            amount_mismatch_count=comparison_result.get('amount_mismatch_count', 0),
            comparison_details=comparison_result.get('differences', {}),
            ai_analysis=ai_analysis,
            health_score=ai_analysis.get('overall_health_score', 0),
            status='COMPLETED',
        )
        comparison.excel_file.save(excel_file.name, ContentFile(excel_content))
        
        return Response({
            'comparison_id': str(comparison.id),
            'summary': comparison_result,
            'ai_analysis': ai_analysis,
            'comparison': ReceiptComparisonSerializer(comparison).data
        })
    
    @action(detail=False, methods=['get'], url_path='comparisons')
    def list_comparisons(self, request):
        """
        List all comparison records
        列出所有比對記錄
        """
        queryset = ReceiptComparison.objects.filter(created_by=request.user)
        serializer = ReceiptComparisonSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    # =========================================================================
    # Expense Reports / 費用報表
    # =========================================================================
    
    @action(detail=False, methods=['post'], url_path='reports/create')
    def create_report(self, request):
        """
        Generate expense report
        生成費用報表
        """
        serializer = ExpenseReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Get receipts
        if data.get('include_all'):
            receipts = Receipt.objects.filter(
                uploaded_by=request.user,
                receipt_date__gte=data['period_start'],
                receipt_date__lte=data['period_end'],
                status__in=[ReceiptStatus.APPROVED, ReceiptStatus.CATEGORIZED, ReceiptStatus.JOURNAL_CREATED]
            )
        elif data.get('receipt_ids'):
            receipts = Receipt.objects.filter(
                id__in=data['receipt_ids'],
                uploaded_by=request.user
            )
        else:
            return Response({
                'error': 'Either include_all or receipt_ids is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not receipts.exists():
            return Response({
                'error': 'No receipts found for the specified criteria'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate totals
        totals = receipts.aggregate(
            total_amount=Sum('total_amount'),
            total_tax=Sum('tax_amount'),
        )
        
        # Create report
        report_number = f"EXP-RPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        report = ExpenseReport.objects.create(
            report_number=report_number,
            title=data['title'],
            created_by=request.user,
            period_start=data['period_start'],
            period_end=data['period_end'],
            total_amount=totals['total_amount'] or 0,
            total_tax=totals['total_tax'] or 0,
            total_count=receipts.count(),
            status='DRAFT',
        )
        report.receipts.set(receipts)
        
        # Generate Excel
        expense_data = list(receipts.values(
            'receipt_number', 'vendor_name', 'receipt_date',
            'category', 'description', 'subtotal', 'tax_amount', 'total_amount'
        ))
        
        # Convert date to string
        for item in expense_data:
            if item.get('receipt_date'):
                item['date'] = str(item['receipt_date'])
        
        try:
            excel_content = generate_expense_report_excel(expense_data)
            report.excel_file.save(
                f"{report_number}.xlsx",
                ContentFile(excel_content)
            )
        except Exception as e:
            # Report created but Excel generation failed
            pass
        
        return Response({
            'report': ExpenseReportSerializer(report).data,
            'receipts_included': receipts.count()
        })
    
    @action(detail=False, methods=['get'], url_path='reports')
    def list_reports(self, request):
        """
        List expense reports
        列出費用報表
        """
        queryset = ExpenseReport.objects.filter(created_by=request.user)
        serializer = ExpenseReportSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='reports/download')
    def download_report(self, request, pk=None):
        """
        Download expense report Excel
        下載費用報表Excel
        """
        try:
            report = ExpenseReport.objects.get(pk=pk, created_by=request.user)
        except ExpenseReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not report.excel_file:
            return Response({'error': 'Excel file not available'}, status=status.HTTP_404_NOT_FOUND)
        
        response = HttpResponse(
            report.excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{report.report_number}.xlsx"'
        return response
    
    @action(detail=True, methods=['post'], url_path='reports/approve')
    def approve_report(self, request, pk=None):
        """
        Approve expense report
        核准費用報表
        """
        try:
            report = ExpenseReport.objects.get(pk=pk)
        except ExpenseReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
        
        report.status = 'APPROVED'
        report.approved_by = request.user
        report.approved_at = timezone.now()
        report.approval_notes = request.data.get('notes', '')
        report.save()
        
        return Response({
            'status': 'approved',
            'report': ExpenseReportSerializer(report).data
        })
    
    # =========================================================================
    # AI Query / AI 查詢
    # =========================================================================
    
    @action(detail=False, methods=['post'], url_path='ai-query')
    def ai_query(self, request):
        """
        Ask AI about accounting/receipts
        詢問AI有關會計/收據的問題
        """
        serializer = AIQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        receipt_id = serializer.validated_data.get('receipt_id')
        
        context = ""
        
        # Get receipt context if provided
        if receipt_id:
            try:
                receipt = Receipt.objects.get(pk=receipt_id, uploaded_by=request.user)
                context = f"""
Receipt Information:
- Vendor: {receipt.vendor_name}
- Date: {receipt.receipt_date}
- Amount: {receipt.total_amount} {receipt.currency}
- Category: {receipt.category}
- Status: {receipt.status}
"""
            except Receipt.DoesNotExist:
                pass
        
        # Get recent receipts summary for context
        recent_receipts = Receipt.objects.filter(uploaded_by=request.user).order_by('-created_at')[:10]
        if recent_receipts.exists():
            totals = recent_receipts.aggregate(
                total=Sum('total_amount'),
                count=models.Count('id')
            )
            context += f"\nRecent Activity: {totals['count']} receipts, Total: {totals['total']}"
        
        from openai import OpenAI
        from django.conf import settings
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        prompt = f"""You are an expert accounting assistant. Help the user with their question.
Provide answers in both English and Traditional Chinese (繁體中文).

Context:
{context}

User Question: {query}

Please provide:
1. Direct answer to the question
2. Any relevant accounting advice
3. Suggestions for improvement if applicable

Format your response as JSON:
{{
    "answer": {{
        "en": "English answer",
        "zh": "中文回答"
    }},
    "advice": {{
        "en": "English advice",
        "zh": "中文建議"
    }},
    "suggestions": [
        {{
            "title": "Suggestion title",
            "description": "Description"
        }}
    ]
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            
            try:
                import json
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].split("```")[0]
                else:
                    json_str = result_text
                
                result = json.loads(json_str.strip())
            except:
                result = {"answer": {"en": result_text, "zh": result_text}}
            
            return Response(result)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # =========================================================================
    # Statistics / 統計
    # =========================================================================
    
    @action(detail=False, methods=['get'], url_path='stats')
    def get_stats(self, request):
        """
        Get accounting assistant statistics
        獲取會計助手統計數據
        """
        receipts = Receipt.objects.filter(uploaded_by=request.user)
        
        # Overall stats
        total_receipts = receipts.count()
        total_amount = receipts.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # By status
        status_counts = {}
        for status_choice in ReceiptStatus.choices:
            count = receipts.filter(status=status_choice[0]).count()
            status_counts[status_choice[0]] = count
        
        # By category
        category_amounts = {}
        for category in ExpenseCategory.choices:
            amount = receipts.filter(category=category[0]).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            category_amounts[category[0]] = float(amount)
        
        # Recent activity
        recent_count = receipts.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        return Response({
            'total_receipts': total_receipts,
            'total_amount': float(total_amount),
            'status_breakdown': status_counts,
            'category_breakdown': category_amounts,
            'recent_30_days': recent_count,
            'pending_approval': status_counts.get(ReceiptStatus.CATEGORIZED, 0) + 
                               status_counts.get(ReceiptStatus.JOURNAL_CREATED, 0),
        })
