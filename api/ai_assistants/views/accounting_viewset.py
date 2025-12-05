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


class AccountingAssistantViewSet(viewsets.ViewSet):
    """
    Accounting Assistant API ViewSet
    會計助手 API 視圖集
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
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
        Approve a receipt
        核准收據
        """
        try:
            receipt = Receipt.objects.get(pk=pk)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        receipt.status = ReceiptStatus.APPROVED
        receipt.reviewed_by = request.user
        receipt.reviewed_at = timezone.now()
        receipt.notes = request.data.get('notes', '')
        receipt.save()
        
        return Response({
            'status': 'approved',
            'receipt': ReceiptSerializer(receipt).data
        })
    
    @action(detail=True, methods=['post'], url_path='create-journal')
    def create_journal_entry(self, request, pk=None):
        """
        Create journal entry from receipt
        從收據建立會計分錄
        """
        try:
            receipt = Receipt.objects.get(pk=pk, uploaded_by=request.user)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate journal entry if not exists
        if not receipt.journal_entry_data:
            receipt_data = receipt.ai_raw_response or {
                'vendor_name': receipt.vendor_name,
                'receipt_number': receipt.receipt_number,
                'receipt_date': str(receipt.receipt_date) if receipt.receipt_date else None,
                'total_amount': float(receipt.total_amount),
                'tax_amount': float(receipt.tax_amount),
                'payment_method': receipt.payment_method,
                'category_suggestion': receipt.category,
            }
            categorization = categorize_expense(receipt_data)
            journal_entry = generate_double_entry(receipt_data, categorization)
            receipt.journal_entry_data = journal_entry
        
        # Here we would actually create the JournalEntry in accounting module
        # For now, just update the status
        receipt.status = ReceiptStatus.JOURNAL_CREATED
        receipt.save()
        
        return Response({
            'status': 'journal_created',
            'journal_entry': receipt.journal_entry_data,
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
