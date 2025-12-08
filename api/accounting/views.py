from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse
from django.db import models, transaction
from django.db.models import Sum, Q, Count, Min
from django.utils import timezone
from decimal import Decimal
import io
import uuid

# PDF Generation imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense, AccountType,
    Project, ProjectDocument, ProjectStatus,
    Receipt, RecognitionStatus,
    ExtractedField, ExtractedFieldType, FieldCorrectionHistory, ReceiptCorrectionSummary,
    Report, ReportExport, ReportTemplate, ReportSchedule, ReportType, ReportStatus, ExportFormat
)
from .serializers import (
    FiscalYearSerializer, AccountingPeriodSerializer, CurrencySerializer,
    TaxRateSerializer, AccountSerializer, AccountListSerializer,
    JournalEntrySerializer, JournalEntryCreateSerializer,
    ContactSerializer, ContactListSerializer,
    InvoiceSerializer, InvoiceListSerializer, InvoiceLineSerializer,
    PaymentSerializer, PaymentAllocationSerializer,
    ExpenseSerializer, ExpenseListSerializer,
    ProjectSerializer, ProjectListSerializer, ProjectCreateSerializer,
    ProjectUpdateSerializer, ProjectDocumentSerializer, LinkDocumentToProjectSerializer,
    ReceiptSerializer, ReceiptListSerializer, ReceiptUploadSerializer,
    BulkReceiptUploadSerializer, ReceiptClassifySerializer, BulkReceiptClassifySerializer,
    BulkReceiptStatusUpdateSerializer,
    ExtractedFieldSerializer, ExtractedFieldListSerializer, FieldCorrectionHistorySerializer,
    ReceiptCorrectSerializer, ReceiptWithFieldsSerializer, ReceiptCorrectionSummarySerializer,
    # Report serializers
    ReportSerializer, ReportListSerializer, ReportExportSerializer, ReportExportListSerializer,
    ReportTemplateSerializer, ReportScheduleSerializer, ReportFilterSerializer,
    GenerateReportSerializer, ExportReportSerializer, UpdateReportSerializer, ReportDataSerializer
)
from .services import ReportGeneratorService, ReportExporterService, ReportCacheService


class FiscalYearViewSet(viewsets.ModelViewSet):
    queryset = FiscalYear.objects.all()
    serializer_class = FiscalYearSerializer
    permission_classes = [IsAuthenticated]


class AccountingPeriodViewSet(viewsets.ModelViewSet):
    queryset = AccountingPeriod.objects.all()
    serializer_class = AccountingPeriodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        fiscal_year_id = self.request.query_params.get('fiscal_year')
        if fiscal_year_id:
            queryset = queryset.filter(fiscal_year_id=fiscal_year_id)
        return queryset


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]


class TaxRateViewSet(viewsets.ModelViewSet):
    queryset = TaxRate.objects.filter(is_active=True)
    serializer_class = TaxRateSerializer
    permission_classes = [IsAuthenticated]


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountListSerializer
        return AccountSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by account type
        account_type = self.request.query_params.get('type')
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        
        # Filter by active status
        is_active = self.request.query_params.get('active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def chart_of_accounts(self, request):
        """Get hierarchical chart of accounts"""
        accounts = Account.objects.filter(parent__isnull=True, is_active=True)
        
        def build_tree(account):
            children = account.children.filter(is_active=True)
            return {
                'id': str(account.id),
                'code': account.code,
                'name': account.name,
                'type': account.account_type,
                'balance': float(account.current_balance),
                'children': [build_tree(child) for child in children]
            }
        
        tree = [build_tree(acc) for acc in accounts]
        return Response(tree)


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JournalEntryCreateSerializer
        return JournalEntrySerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        """Post a journal entry (make it final)"""
        entry = self.get_object()
        
        if not entry.is_balanced:
            return Response(
                {'error': 'Journal entry is not balanced'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if entry.status != 'DRAFT':
            return Response(
                {'error': 'Only draft entries can be posted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update account balances
        for line in entry.lines.all():
            account = line.account
            if account.is_debit_positive:
                account.current_balance += line.debit - line.credit
            else:
                account.current_balance += line.credit - line.debit
            account.save()
        
        entry.status = 'POSTED'
        from django.utils import timezone
        entry.posted_at = timezone.now()
        entry.save()
        
        return Response({'status': 'posted'})
    
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void a posted journal entry"""
        entry = self.get_object()
        
        if entry.status != 'POSTED':
            return Response(
                {'error': 'Only posted entries can be voided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reverse account balances
        for line in entry.lines.all():
            account = line.account
            if account.is_debit_positive:
                account.current_balance -= line.debit - line.credit
            else:
                account.current_balance -= line.credit - line.debit
            account.save()
        
        entry.status = 'VOIDED'
        entry.save()
        
        return Response({'status': 'voided'})


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        contact_type = self.request.query_params.get('type')
        if contact_type:
            queryset = queryset.filter(
                Q(contact_type=contact_type) | Q(contact_type='BOTH')
            )
        
        return queryset


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        invoice_type = self.request.query_params.get('type')
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate PDF for invoice"""
        invoice = self.get_object()
        
        # Create the HttpResponse object with PDF headers
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center
        )
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12
        )
        normal_style = styles['Normal']
        
        # Build the PDF content
        elements = []
        
        # Header - Invoice Title
        invoice_type_label = "SALES INVOICE" if invoice.invoice_type == 'SALES' else "PURCHASE INVOICE"
        elements.append(Paragraph(invoice_type_label, title_style))
        elements.append(Spacer(1, 10))
        
        # Invoice Info Table
        invoice_info = [
            ['Invoice Number:', invoice.invoice_number, 'Date:', str(invoice.issue_date)],
            ['Reference:', invoice.reference or '-', 'Due Date:', str(invoice.due_date)],
            ['Status:', invoice.status, 'Currency:', invoice.currency.code if invoice.currency else 'TWD'],
        ]
        
        info_table = Table(invoice_info, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Contact Info
        contact = invoice.contact
        elements.append(Paragraph("Bill To:", heading_style))
        contact_info = f"""
        {contact.name}<br/>
        {contact.company_name or ''}<br/>
        {contact.address or ''}<br/>
        {contact.email or ''}
        """
        elements.append(Paragraph(contact_info.strip(), normal_style))
        elements.append(Spacer(1, 20))
        
        # Invoice Lines Table
        elements.append(Paragraph("Invoice Items:", heading_style))
        
        # Table header
        line_data = [['Description', 'Qty', 'Unit Price', 'Tax', 'Total']]
        
        # Add invoice lines
        for line in invoice.lines.all():
            line_data.append([
                line.description,
                str(line.quantity),
                f"${line.unit_price:,.2f}",
                f"${line.tax_amount:,.2f}",
                f"${line.line_total:,.2f}",
            ])
        
        # Create line items table
        line_table = Table(line_data, colWidths=[8*cm, 2*cm, 3*cm, 2*cm, 3*cm])
        line_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            # Body styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            # Alignment
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"${invoice.subtotal:,.2f}"],
            ['Tax:', f"${invoice.tax_amount:,.2f}"],
            ['Discount:', f"-${invoice.discount_amount:,.2f}"],
            ['Total:', f"${invoice.total:,.2f}"],
            ['Amount Paid:', f"${invoice.amount_paid:,.2f}"],
            ['Balance Due:', f"${invoice.amount_due:,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[12*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))
        
        # Notes
        if invoice.notes:
            elements.append(Paragraph("Notes:", heading_style))
            elements.append(Paragraph(invoice.notes, normal_style))
            elements.append(Spacer(1, 10))
        
        # Terms
        if invoice.terms:
            elements.append(Paragraph("Terms & Conditions:", heading_style))
            elements.append(Paragraph(invoice.terms, normal_style))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF content
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue invoices"""
        from django.utils import timezone
        today = timezone.now().date()
        
        invoices = Invoice.objects.filter(
            due_date__lt=today,
            status__in=['SENT', 'VIEWED', 'PARTIAL']
        )
        
        serializer = InvoiceListSerializer(invoices, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        payment_type = self.request.query_params.get('type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """Allocate payment to invoices"""
        payment = self.get_object()
        allocations = request.data.get('allocations', [])
        
        for allocation in allocations:
            invoice_id = allocation.get('invoice_id')
            amount = Decimal(str(allocation.get('amount', 0)))
            
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                PaymentAllocation.objects.create(
                    payment=payment,
                    invoice=invoice,
                    amount=amount
                )
                
                # Update invoice
                invoice.amount_paid += amount
                invoice.amount_due -= amount
                
                if invoice.amount_due <= 0:
                    invoice.status = 'PAID'
                else:
                    invoice.status = 'PARTIAL'
                
                invoice.save()
            except Invoice.DoesNotExist:
                pass
        
        return Response({'status': 'allocated'})


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseListSerializer
        return ExpenseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Non-admin users only see their own expenses
        if not self.request.user.is_staff:
            queryset = queryset.filter(employee=self.request.user)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense"""
        expense = self.get_object()
        
        if expense.status != 'PENDING':
            return Response(
                {'error': 'Only pending expenses can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        expense.status = 'APPROVED'
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save()
        
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense"""
        expense = self.get_object()
        
        if expense.status != 'PENDING':
            return Response(
                {'error': 'Only pending expenses can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'VOIDED'
        expense.save()
        
        return Response({'status': 'rejected'})


class ReportViewSet(viewsets.ViewSet):
    """Financial reports generation"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """Generate trial balance"""
        accounts = Account.objects.filter(is_active=True).exclude(current_balance=0)
        
        data = []
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for account in accounts:
            balance = account.current_balance
            debit = balance if account.is_debit_positive and balance > 0 else Decimal('0')
            credit = abs(balance) if not account.is_debit_positive and balance > 0 else Decimal('0')
            
            if balance < 0:
                if account.is_debit_positive:
                    credit = abs(balance)
                else:
                    debit = abs(balance)
            
            total_debit += debit
            total_credit += credit
            
            data.append({
                'code': account.code,
                'name': account.name,
                'type': account.account_type,
                'debit': float(debit),
                'credit': float(credit)
            })
        
        return Response({
            'accounts': data,
            'totals': {
                'debit': float(total_debit),
                'credit': float(total_credit),
                'is_balanced': total_debit == total_credit
            }
        })
    
    @action(detail=False, methods=['get'])
    def balance_sheet(self, request):
        """Generate balance sheet"""
        as_of_date = request.query_params.get('date')
        
        assets = Account.objects.filter(
            account_type=AccountType.ASSET.value,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        liabilities = Account.objects.filter(
            account_type=AccountType.LIABILITY.value,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        equity = Account.objects.filter(
            account_type=AccountType.EQUITY.value,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        return Response({
            'as_of_date': as_of_date,
            'assets': float(assets),
            'liabilities': float(liabilities),
            'equity': float(equity),
            'total_liabilities_equity': float(liabilities + equity),
            'is_balanced': assets == (liabilities + equity)
        })
    
    @action(detail=False, methods=['get'])
    def income_statement(self, request):
        """Generate income statement"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        revenue = Account.objects.filter(
            account_type=AccountType.REVENUE.value,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        expenses = Account.objects.filter(
            account_type=AccountType.EXPENSE.value,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        net_income = revenue - expenses
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'revenue': float(revenue),
            'expenses': float(expenses),
            'net_income': float(net_income)
        })
    
    @action(detail=False, methods=['get'])
    def accounts_receivable_aging(self, request):
        """Accounts receivable aging report"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        
        invoices = Invoice.objects.filter(
            invoice_type='SALES',
            status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
        )
        
        aging = {
            'current': Decimal('0'),
            '1_30': Decimal('0'),
            '31_60': Decimal('0'),
            '61_90': Decimal('0'),
            'over_90': Decimal('0')
        }
        
        for invoice in invoices:
            days_overdue = (today - invoice.due_date).days
            amount_due = invoice.amount_due
            
            if days_overdue <= 0:
                aging['current'] += amount_due
            elif days_overdue <= 30:
                aging['1_30'] += amount_due
            elif days_overdue <= 60:
                aging['31_60'] += amount_due
            elif days_overdue <= 90:
                aging['61_90'] += amount_due
            else:
                aging['over_90'] += amount_due
        
        return Response({
            'current': float(aging['current']),
            '1_30_days': float(aging['1_30']),
            '31_60_days': float(aging['31_60']),
            '61_90_days': float(aging['61_90']),
            'over_90_days': float(aging['over_90']),
            'total': float(sum(aging.values()))
        })


# =================================================================
# Project Management ViewSet
# =================================================================

class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing accounting projects.
    
    Provides CRUD operations and additional actions for:
    - Linking/unlinking expenses, invoices, journal entries
    - Managing project documents
    - Project statistics and summaries
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Project.objects.all()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by client
        client_id = self.request.query_params.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Filter by manager
        manager_id = self.request.query_params.get('manager')
        if manager_id:
            queryset = queryset.filter(manager_id=manager_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by name or code
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('created_by', 'manager', 'client', 'currency')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProjectUpdateSerializer
        elif self.action == 'link_documents':
            return LinkDocumentToProjectSerializer
        return ProjectSerializer
    
    def perform_create(self, serializer):
        """Set created_by and tenant on create"""
        serializer.save(
            created_by=self.request.user,
            tenant=getattr(self.request, 'tenant', None)
        )
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get project summary with all linked documents"""
        project = self.get_object()
        
        # Get linked expenses
        expenses = Expense.objects.filter(project=project).values(
            'id', 'expense_number', 'date', 'description', 'amount', 'status'
        )
        
        # Get linked invoices
        invoices = Invoice.objects.filter(project=project).values(
            'id', 'invoice_number', 'invoice_type', 'issue_date', 'total', 'status'
        )
        
        # Get linked journal entries
        journal_entries = JournalEntry.objects.filter(project=project).values(
            'id', 'entry_number', 'date', 'description', 'status', 'total_debit'
        )
        
        # Get project documents
        documents = ProjectDocument.objects.filter(project=project).values(
            'id', 'document_type', 'title', 'file_name', 'created_at'
        )
        
        return Response({
            'project': ProjectSerializer(project).data,
            'expenses': list(expenses),
            'invoices': list(invoices),
            'journal_entries': list(journal_entries),
            'documents': list(documents),
            'totals': {
                'expense_count': len(expenses),
                'invoice_count': len(invoices),
                'journal_entry_count': len(journal_entries),
                'document_count': len(documents),
                'total_expenses': float(project.total_expenses),
                'total_invoiced': float(project.total_invoiced),
                'budget_remaining': float(project.budget_remaining),
                'budget_utilization': float(project.budget_utilization_percent)
            }
        })
    
    @action(detail=True, methods=['post'])
    def link_documents(self, request, pk=None):
        """Link expenses, invoices, or journal entries to this project"""
        project = self.get_object()
        serializer = LinkDocumentToProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        document_type = serializer.validated_data['document_type']
        document_ids = serializer.validated_data['document_ids']
        
        # Update documents to link to this project
        if document_type == 'expense':
            updated = Expense.objects.filter(id__in=document_ids).update(project=project)
        elif document_type == 'invoice':
            updated = Invoice.objects.filter(id__in=document_ids).update(project=project)
        elif document_type == 'journal_entry':
            updated = JournalEntry.objects.filter(id__in=document_ids).update(project=project)
        
        return Response({
            'message': f'Successfully linked {updated} {document_type}(s) to project',
            'linked_count': updated
        })
    
    @action(detail=True, methods=['post'])
    def unlink_documents(self, request, pk=None):
        """Unlink expenses, invoices, or journal entries from this project"""
        project = self.get_object()
        serializer = LinkDocumentToProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        document_type = serializer.validated_data['document_type']
        document_ids = serializer.validated_data['document_ids']
        
        # Update documents to remove project link
        if document_type == 'expense':
            updated = Expense.objects.filter(id__in=document_ids, project=project).update(project=None)
        elif document_type == 'invoice':
            updated = Invoice.objects.filter(id__in=document_ids, project=project).update(project=None)
        elif document_type == 'journal_entry':
            updated = JournalEntry.objects.filter(id__in=document_ids, project=project).update(project=None)
        
        return Response({
            'message': f'Successfully unlinked {updated} {document_type}(s) from project',
            'unlinked_count': updated
        })
    
    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        """Get all expenses linked to this project"""
        project = self.get_object()
        expenses = Expense.objects.filter(project=project)
        
        # Pagination
        page = self.paginate_queryset(expenses)
        if page is not None:
            serializer = ExpenseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ExpenseListSerializer(expenses, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """Get all invoices linked to this project"""
        project = self.get_object()
        invoices = Invoice.objects.filter(project=project)
        
        # Pagination
        page = self.paginate_queryset(invoices)
        if page is not None:
            serializer = InvoiceListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = InvoiceListSerializer(invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def journal_entries(self, request, pk=None):
        """Get all journal entries linked to this project"""
        project = self.get_object()
        entries = JournalEntry.objects.filter(project=project)
        
        # Pagination
        page = self.paginate_queryset(entries)
        if page is not None:
            serializer = JournalEntrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = JournalEntrySerializer(entries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall project statistics"""
        projects = self.get_queryset()
        
        total_count = projects.count()
        active_count = projects.filter(status=ProjectStatus.ACTIVE.value).count()
        completed_count = projects.filter(status=ProjectStatus.COMPLETED.value).count()
        on_hold_count = projects.filter(status=ProjectStatus.ON_HOLD.value).count()
        
        total_budget = projects.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        
        return Response({
            'total_projects': total_count,
            'by_status': {
                'active': active_count,
                'completed': completed_count,
                'on_hold': on_hold_count,
                'cancelled': projects.filter(status=ProjectStatus.CANCELLED.value).count(),
                'archived': projects.filter(status=ProjectStatus.ARCHIVED.value).count()
            },
            'total_budget': float(total_budget)
        })
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of unique project categories"""
        categories = Project.objects.values_list('category', flat=True).distinct()
        return Response({
            'categories': [c for c in categories if c]
        })


class ProjectDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project documents"""
    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ProjectDocument.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by document type
        doc_type = self.request.query_params.get('document_type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        
        return queryset.select_related('project', 'uploaded_by')
    
    def perform_create(self, serializer):
        """Set uploaded_by and tenant on create"""
        serializer.save(
            uploaded_by=self.request.user,
            tenant=getattr(self.request, 'tenant', None)
        )


# =================================================================
# Receipt ViewSet with Bulk Upload & Classification
# =================================================================

class ReceiptViewSet(viewsets.ModelViewSet):
    """
    ViewSet for receipt management with bulk upload and classification features.
    
    Endpoints:
    - GET /receipts/ - List all receipts (with filtering)
    - POST /receipts/ - Single file upload
    - GET /receipts/{id}/ - Get receipt details
    - PATCH /receipts/{id}/ - Update receipt
    - DELETE /receipts/{id}/ - Delete receipt
    - POST /receipts/bulk_upload/ - Bulk file upload
    - GET /receipts/unrecognized/ - List unrecognized receipts
    - POST /receipts/{id}/classify/ - Manual classification
    - POST /receipts/bulk_classify/ - Batch classification
    - POST /receipts/bulk_status_update/ - Batch status update
    - GET /receipts/statistics/ - Get receipt statistics
    - GET /receipts/batches/ - List upload batches
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReceiptListSerializer
        if self.action == 'bulk_upload':
            return BulkReceiptUploadSerializer
        if self.action == 'classify':
            return ReceiptClassifySerializer
        if self.action == 'bulk_classify':
            return BulkReceiptClassifySerializer
        if self.action == 'bulk_status_update':
            return BulkReceiptStatusUpdateSerializer
        return ReceiptSerializer
    
    def get_queryset(self):
        queryset = Receipt.objects.all()
        
        # Filter by recognition status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(recognition_status=status_filter)
        
        # Filter by project
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by batch
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Filter unclassified only
        unclassified = self.request.query_params.get('unclassified')
        if unclassified and unclassified.lower() == 'true':
            queryset = queryset.filter(manual_category__isnull=True)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(original_filename__icontains=search) |
                Q(vendor_name__icontains=search) |
                Q(manual_vendor__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related(
            'uploaded_by', 'classified_by', 'project', 'manual_category', 'expense'
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Single file upload endpoint"""
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        project_id = serializer.validated_data.get('project_id')
        auto_process = serializer.validated_data.get('auto_process', True)
        confidence_threshold = serializer.validated_data.get('confidence_threshold', Decimal('0.7000'))
        tags = serializer.validated_data.get('tags', [])
        
        # Create receipt record
        receipt = Receipt.objects.create(
            tenant=getattr(request, 'tenant', None),
            file=file,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            project_id=project_id,
            confidence_threshold=confidence_threshold,
            tags=tags,
            uploaded_by=request.user,
            batch_id=uuid.uuid4()  # Single upload gets its own batch
        )
        
        # Process OCR if auto_process is enabled
        if auto_process:
            self._process_receipt(receipt)
        
        return Response(
            ReceiptSerializer(receipt, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """
        Bulk upload endpoint with progress tracking.
        Returns batch_id and processing results for each file.
        """
        serializer = BulkReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        files = serializer.validated_data['files']
        project_id = serializer.validated_data.get('project_id')
        auto_process = serializer.validated_data.get('auto_process', True)
        confidence_threshold = serializer.validated_data.get('confidence_threshold', Decimal('0.7000'))
        tags = serializer.validated_data.get('tags', [])
        
        # Generate batch ID for this upload
        batch_id = uuid.uuid4()
        
        results = []
        recognized_count = 0
        unrecognized_count = 0
        failed_count = 0
        
        for file in files:
            try:
                # Create receipt record
                receipt = Receipt.objects.create(
                    tenant=getattr(request, 'tenant', None),
                    file=file,
                    original_filename=file.name,
                    file_size=file.size,
                    mime_type=file.content_type,
                    project_id=project_id,
                    confidence_threshold=confidence_threshold,
                    tags=tags,
                    uploaded_by=request.user,
                    batch_id=batch_id
                )
                
                # Process OCR if auto_process is enabled
                if auto_process:
                    self._process_receipt(receipt)
                
                # Track results
                if receipt.recognition_status == RecognitionStatus.RECOGNIZED.value:
                    recognized_count += 1
                elif receipt.recognition_status == RecognitionStatus.UNRECOGNIZED.value:
                    unrecognized_count += 1
                
                results.append({
                    'id': str(receipt.id),
                    'original_filename': receipt.original_filename,
                    'recognition_status': receipt.recognition_status,
                    'confidence_score': receipt.confidence_score,
                    'vendor_name': receipt.vendor_name or '',
                    'total_amount': receipt.total_amount,
                    'receipt_date': receipt.receipt_date,
                    'error': receipt.processing_error or ''
                })
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'id': None,
                    'original_filename': file.name,
                    'recognition_status': 'FAILED',
                    'confidence_score': None,
                    'vendor_name': '',
                    'total_amount': None,
                    'receipt_date': None,
                    'error': str(e)
                })
        
        return Response({
            'batch_id': str(batch_id),
            'total_files': len(files),
            'processed': len(results),
            'recognized': recognized_count,
            'unrecognized': unrecognized_count,
            'failed': failed_count,
            'results': results
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def unrecognized(self, request):
        """Get all unrecognized receipts that need manual classification"""
        queryset = self.get_queryset().filter(
            recognition_status=RecognitionStatus.UNRECOGNIZED.value
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReceiptListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ReceiptListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def classify(self, request, pk=None):
        """Manual classification for a single receipt"""
        receipt = self.get_object()
        serializer = ReceiptClassifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update manual classification fields
        category_id = serializer.validated_data.get('category_id')
        if category_id:
            receipt.manual_category_id = category_id
        
        vendor = serializer.validated_data.get('vendor')
        if vendor:
            receipt.manual_vendor = vendor
        
        amount = serializer.validated_data.get('amount')
        if amount is not None:
            receipt.manual_amount = amount
        
        date = serializer.validated_data.get('date')
        if date:
            receipt.manual_date = date
        
        notes = serializer.validated_data.get('notes')
        if notes:
            receipt.classification_notes = notes
        
        tags = serializer.validated_data.get('tags')
        if tags:
            receipt.tags = tags
        
        # Update status and classification metadata
        receipt.recognition_status = RecognitionStatus.MANUALLY_CLASSIFIED.value
        receipt.classified_by = request.user
        receipt.classified_at = timezone.now()
        receipt.save()
        
        return Response({
            'message': 'Receipt classified successfully',
            'receipt': ReceiptSerializer(receipt, context={'request': request}).data
        })
    
    @action(detail=False, methods=['post'])
    def bulk_classify(self, request):
        """Batch classification for multiple receipts"""
        serializer = BulkReceiptClassifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        receipt_ids = serializer.validated_data['receipt_ids']
        category_id = serializer.validated_data.get('category_id')
        project_id = serializer.validated_data.get('project_id')
        tags = serializer.validated_data.get('tags', [])
        notes = serializer.validated_data.get('notes', '')
        
        # Build update fields
        update_fields = {
            'recognition_status': RecognitionStatus.MANUALLY_CLASSIFIED.value,
            'classified_by': request.user,
            'classified_at': timezone.now()
        }
        
        if category_id:
            update_fields['manual_category_id'] = category_id
        if project_id:
            update_fields['project_id'] = project_id
        if notes:
            update_fields['classification_notes'] = notes
        
        # Update receipts
        updated_count = Receipt.objects.filter(id__in=receipt_ids).update(**update_fields)
        
        # Update tags separately (JSONField requires individual updates for append)
        if tags:
            for receipt in Receipt.objects.filter(id__in=receipt_ids):
                existing_tags = receipt.tags or []
                receipt.tags = list(set(existing_tags + tags))
                receipt.save(update_fields=['tags'])
        
        return Response({
            'message': f'Successfully classified {updated_count} receipts',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_status_update(self, request):
        """Batch status update for multiple receipts"""
        serializer = BulkReceiptStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        receipt_ids = serializer.validated_data['receipt_ids']
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        
        update_fields = {'recognition_status': new_status}
        
        if new_status == RecognitionStatus.MANUALLY_CLASSIFIED.value:
            update_fields['classified_by'] = request.user
            update_fields['classified_at'] = timezone.now()
        
        if notes:
            update_fields['classification_notes'] = notes
        
        updated_count = Receipt.objects.filter(id__in=receipt_ids).update(**update_fields)
        
        return Response({
            'message': f'Successfully updated {updated_count} receipts',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get receipt statistics"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        by_status = queryset.values('recognition_status').annotate(count=Count('id'))
        
        # Calculate amounts
        total_recognized_amount = queryset.filter(
            recognition_status__in=[
                RecognitionStatus.RECOGNIZED.value,
                RecognitionStatus.MANUALLY_CLASSIFIED.value
            ]
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        # Recent batches
        recent_batches = queryset.exclude(batch_id__isnull=True).values(
            'batch_id'
        ).annotate(
            count=Count('id'),
            recognized=Count('id', filter=Q(recognition_status=RecognitionStatus.RECOGNIZED.value)),
            unrecognized=Count('id', filter=Q(recognition_status=RecognitionStatus.UNRECOGNIZED.value))
        ).order_by('-batch_id')[:10]
        
        return Response({
            'total_receipts': total,
            'by_status': {item['recognition_status']: item['count'] for item in by_status},
            'total_recognized_amount': float(total_recognized_amount),
            'needs_review': queryset.filter(
                recognition_status=RecognitionStatus.UNRECOGNIZED.value
            ).count(),
            'recent_batches': list(recent_batches)
        })
    
    @action(detail=False, methods=['get'])
    def batches(self, request):
        """List all upload batches with summary"""
        queryset = self.get_queryset().exclude(batch_id__isnull=True)
        
        batches = queryset.values('batch_id').annotate(
            total=Count('id'),
            recognized=Count('id', filter=Q(recognition_status=RecognitionStatus.RECOGNIZED.value)),
            unrecognized=Count('id', filter=Q(recognition_status=RecognitionStatus.UNRECOGNIZED.value)),
            manually_classified=Count('id', filter=Q(recognition_status=RecognitionStatus.MANUALLY_CLASSIFIED.value)),
            first_upload=models.Min('created_at')
        ).order_by('-first_upload')
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page_num = int(request.query_params.get('page', 1))
        
        start = (page_num - 1) * page_size
        end = start + page_size
        
        return Response({
            'count': len(batches),
            'results': list(batches[start:end])
        })
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Re-process OCR for a receipt"""
        receipt = self.get_object()
        
        if receipt.retry_count >= 3:
            return Response(
                {'error': 'Maximum retry attempts reached'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        receipt.retry_count += 1
        receipt.recognition_status = RecognitionStatus.PENDING.value
        receipt.processing_error = ''
        receipt.save()
        
        # Re-process
        self._process_receipt(receipt)
        
        return Response({
            'message': 'Receipt reprocessed',
            'receipt': ReceiptSerializer(receipt, context={'request': request}).data
        })
    
    def _process_receipt(self, receipt):
        """
        Process receipt with OCR/AI extraction.
        This is a placeholder - integrate with actual OCR service.
        """
        try:
            receipt.processing_started_at = timezone.now()
            receipt.save(update_fields=['processing_started_at'])
            
            # TODO: Integrate with actual OCR service (e.g., Google Vision, AWS Textract, etc.)
            # For now, simulate processing based on file presence
            
            # Simulated extraction result
            # In production, call OCR API here
            extracted_data = self._extract_receipt_data(receipt)
            
            if extracted_data:
                receipt.extracted_data = extracted_data
                receipt.vendor_name = extracted_data.get('vendor', '')
                receipt.total_amount = extracted_data.get('total')
                receipt.receipt_date = extracted_data.get('date')
                receipt.tax_amount = extracted_data.get('tax')
                receipt.currency_code = extracted_data.get('currency', 'TWD')
                receipt.description = extracted_data.get('description', '')
                receipt.confidence_score = Decimal(str(extracted_data.get('confidence', 0)))
                
                # Determine recognition status based on confidence
                if receipt.confidence_score >= receipt.confidence_threshold:
                    receipt.recognition_status = RecognitionStatus.RECOGNIZED.value
                else:
                    receipt.recognition_status = RecognitionStatus.UNRECOGNIZED.value
                    receipt.processing_error = f"Low confidence ({receipt.confidence_score}) below threshold ({receipt.confidence_threshold})"
            else:
                receipt.recognition_status = RecognitionStatus.UNRECOGNIZED.value
                receipt.processing_error = "Failed to extract data from receipt"
            
            receipt.processing_completed_at = timezone.now()
            receipt.save()
            
        except Exception as e:
            receipt.recognition_status = RecognitionStatus.UNRECOGNIZED.value
            receipt.processing_error = str(e)
            receipt.processing_completed_at = timezone.now()
            receipt.save()
    
    def _extract_receipt_data(self, receipt):
        """
        Placeholder for OCR extraction.
        Replace with actual OCR service integration.
        """
        # This is a mock implementation
        # In production, integrate with:
        # - Google Cloud Vision API
        # - AWS Textract
        # - Azure Form Recognizer
        # - Custom OCR service
        
        import random
        
        # Simulate random extraction results for demo
        # In production, this would call the actual OCR API
        confidence = random.uniform(0.5, 0.95)
        
        if confidence > 0.6:
            return {
                'vendor': f'Vendor_{random.randint(1, 100)}',
                'total': Decimal(str(round(random.uniform(10, 1000), 2))),
                'date': timezone.now().date(),
                'tax': Decimal(str(round(random.uniform(1, 100), 2))),
                'currency': 'TWD',
                'description': 'Auto-extracted receipt',
                'confidence': confidence
            }
        return None

    # ============================================
    # Field Extraction & Correction Endpoints
    # ============================================
    
    @action(detail=True, methods=['get'])
    def fields(self, request, pk=None):
        """
        Get all extracted fields for a receipt with bounding boxes.
        Returns fields grouped by type with visual coordinates for UI highlighting.
        """
        receipt = self.get_object()
        fields = ExtractedField.objects.filter(receipt=receipt).order_by(
            'page_number', 'field_type', 'created_at'
        )
        
        serializer = ExtractedFieldSerializer(fields, many=True)
        
        # Group by field type for easier UI consumption
        grouped = {}
        for field in serializer.data:
            field_type = field['field_type']
            if field_type not in grouped:
                grouped[field_type] = []
            grouped[field_type].append(field)
        
        return Response({
            'receipt_id': str(receipt.id),
            'total_fields': fields.count(),
            'fields': serializer.data,
            'fields_by_type': grouped,
            'correction_summary': self._get_correction_summary(receipt)
        })
    
    @action(detail=True, methods=['put'])
    def correct(self, request, pk=None):
        """
        Correct extracted fields with bounding box overrides.
        Creates version history for audit trail.
        
        Request body:
        {
            "fields": [
                {
                    "field_id": "uuid",  // existing field to correct
                    "value": "corrected value",
                    "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.3},
                    "correction_reason": "OCR error"
                },
                {
                    "field_type": "VENDOR",  // new field to create
                    "field_name": "vendor_name",
                    "value": "ABC Corp",
                    "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.3},
                    "page_number": 1
                }
            ],
            "correction_source": "UI",
            "notes": "Manual correction by user"
        }
        """
        from django.db import transaction
        
        receipt = self.get_object()
        serializer = ReceiptCorrectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fields_data = serializer.validated_data['fields']
        correction_source = serializer.validated_data.get('correction_source', 'UI')
        notes = serializer.validated_data.get('notes', '')
        
        corrected_fields = []
        created_fields = []
        errors = []
        
        with transaction.atomic():
            for field_data in fields_data:
                try:
                    field_id = field_data.get('field_id')
                    
                    if field_id:
                        # Correct existing field
                        result = self._correct_existing_field(
                            receipt, field_id, field_data, request.user, 
                            correction_source, notes
                        )
                        if result:
                            corrected_fields.append(result)
                    else:
                        # Create new field
                        result = self._create_new_field(
                            receipt, field_data, request.user
                        )
                        if result:
                            created_fields.append(result)
                            
                except Exception as e:
                    errors.append({
                        'field_id': str(field_data.get('field_id', 'new')),
                        'field_type': field_data.get('field_type'),
                        'error': str(e)
                    })
            
            # Update or create correction summary
            self._update_correction_summary(receipt, request.user)
        
        return Response({
            'message': 'Fields corrected successfully',
            'receipt_id': str(receipt.id),
            'corrected_count': len(corrected_fields),
            'created_count': len(created_fields),
            'corrected_fields': ExtractedFieldSerializer(corrected_fields, many=True).data,
            'created_fields': ExtractedFieldSerializer(created_fields, many=True).data,
            'errors': errors if errors else None,
            'correction_summary': self._get_correction_summary(receipt)
        })
    
    @action(detail=True, methods=['get'])
    def correction_history(self, request, pk=None):
        """
        Get full correction history for a receipt's fields.
        Supports filtering by field_id and date range.
        """
        receipt = self.get_object()
        
        # Get history for all fields of this receipt
        field_ids = ExtractedField.objects.filter(receipt=receipt).values_list('id', flat=True)
        history = FieldCorrectionHistory.objects.filter(
            field_id__in=field_ids
        ).select_related('corrected_by').order_by('-created_at')
        
        # Filter by specific field if requested
        field_filter = request.query_params.get('field_id')
        if field_filter:
            history = history.filter(field_id=field_filter)
        
        # Filter by date range
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            history = history.filter(created_at__date__gte=date_from)
        if date_to:
            history = history.filter(created_at__date__lte=date_to)
        
        serializer = FieldCorrectionHistorySerializer(history, many=True)
        
        return Response({
            'receipt_id': str(receipt.id),
            'total_corrections': history.count(),
            'history': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='fields/bulk-create')
    def bulk_create_fields(self, request, pk=None):
        """
        Bulk create extracted fields from OCR processing.
        Used by OCR integration to populate fields after processing.
        """
        receipt = self.get_object()
        serializer = ExtractedFieldListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fields_data = serializer.validated_data['fields']
        created_fields = []
        
        for field_data in fields_data:
            field = ExtractedField.objects.create(
                receipt=receipt,
                field_type=field_data['field_type'],
                field_name=field_data.get('field_name', ''),
                raw_value=field_data.get('raw_value', ''),
                normalized_value=field_data.get('normalized_value', ''),
                confidence_score=field_data.get('confidence_score'),
                bbox_x1=field_data.get('bbox_x1'),
                bbox_y1=field_data.get('bbox_y1'),
                bbox_x2=field_data.get('bbox_x2'),
                bbox_y2=field_data.get('bbox_y2'),
                bbox_unit=field_data.get('bbox_unit', 'ratio'),
                page_number=field_data.get('page_number', 1),
            )
            created_fields.append(field)
        
        # Create initial correction summary
        self._update_correction_summary(receipt, None)
        
        return Response({
            'message': f'Created {len(created_fields)} fields',
            'receipt_id': str(receipt.id),
            'fields': ExtractedFieldSerializer(created_fields, many=True).data
        }, status=status.HTTP_201_CREATED)
    
    def _correct_existing_field(self, receipt, field_id, field_data, user, correction_source, notes):
        """Correct an existing extracted field and create history entry."""
        try:
            field = ExtractedField.objects.get(id=field_id, receipt=receipt)
        except ExtractedField.DoesNotExist:
            raise ValueError(f"Field {field_id} not found for this receipt")
        
        # Store previous values for history
        prev_value = field.corrected_value if field.is_corrected else field.raw_value
        prev_bbox = {
            'x1': field.corrected_bbox_x1 or field.bbox_x1,
            'y1': field.corrected_bbox_y1 or field.bbox_y1,
            'x2': field.corrected_bbox_x2 or field.bbox_x2,
            'y2': field.corrected_bbox_y2 or field.bbox_y2,
        }
        
        # Create history entry
        FieldCorrectionHistory.objects.create(
            field=field,
            version=field.version,
            previous_value=prev_value,
            new_value=field_data.get('value', ''),
            previous_bbox_x1=prev_bbox['x1'],
            previous_bbox_y1=prev_bbox['y1'],
            previous_bbox_x2=prev_bbox['x2'],
            previous_bbox_y2=prev_bbox['y2'],
            new_bbox_x1=field_data.get('bounding_box', {}).get('x1'),
            new_bbox_y1=field_data.get('bounding_box', {}).get('y1'),
            new_bbox_x2=field_data.get('bounding_box', {}).get('x2'),
            new_bbox_y2=field_data.get('bounding_box', {}).get('y2'),
            correction_reason=field_data.get('correction_reason', ''),
            corrected_by=user,
            correction_source=correction_source,
            notes=notes
        )
        
        # Update field with corrections
        field.is_corrected = True
        field.corrected_value = field_data.get('value', field.corrected_value or field.raw_value)
        field.corrected_by = user
        field.corrected_at = timezone.now()
        field.version += 1
        
        # Update bounding box if provided
        bbox = field_data.get('bounding_box')
        if bbox:
            field.corrected_bbox_x1 = bbox.get('x1')
            field.corrected_bbox_y1 = bbox.get('y1')
            field.corrected_bbox_x2 = bbox.get('x2')
            field.corrected_bbox_y2 = bbox.get('y2')
        
        field.save()
        return field
    
    def _create_new_field(self, receipt, field_data, user):
        """Create a new extracted field from manual entry."""
        bbox = field_data.get('bounding_box', {})
        
        field = ExtractedField.objects.create(
            receipt=receipt,
            field_type=field_data['field_type'],
            field_name=field_data.get('field_name', ''),
            raw_value='',  # No raw value for manually created fields
            normalized_value=field_data.get('value', ''),
            confidence_score=Decimal('1.0'),  # Manual entry = 100% confidence
            bbox_x1=bbox.get('x1'),
            bbox_y1=bbox.get('y1'),
            bbox_x2=bbox.get('x2'),
            bbox_y2=bbox.get('y2'),
            bbox_unit=field_data.get('bbox_unit', 'ratio'),
            page_number=field_data.get('page_number', 1),
            is_corrected=True,
            corrected_value=field_data.get('value', ''),
            corrected_by=user,
            corrected_at=timezone.now(),
        )
        return field
    
    def _update_correction_summary(self, receipt, user):
        """Update or create correction summary for a receipt."""
        total_fields = ExtractedField.objects.filter(receipt=receipt).count()
        corrected_fields = ExtractedField.objects.filter(receipt=receipt, is_corrected=True).count()
        total_corrections = FieldCorrectionHistory.objects.filter(
            field__receipt=receipt
        ).count()
        
        summary, created = ReceiptCorrectionSummary.objects.update_or_create(
            receipt=receipt,
            defaults={
                'total_fields': total_fields,
                'corrected_fields': corrected_fields,
                'total_corrections': total_corrections,
                'last_correction_at': timezone.now() if corrected_fields > 0 else None,
                'last_corrected_by': user,
            }
        )
        return summary
    
    def _get_correction_summary(self, receipt):
        """Get correction summary for a receipt."""
        try:
            summary = ReceiptCorrectionSummary.objects.get(receipt=receipt)
            return ReceiptCorrectionSummarySerializer(summary).data
        except ReceiptCorrectionSummary.DoesNotExist:
            return {
                'total_fields': 0,
                'corrected_fields': 0,
                'total_corrections': 0,
                'correction_rate': 0,
                'last_correction_at': None,
                'last_corrected_by': None
            }


# =================================================================
# Financial Reports ViewSet (New Reporting System)
# =================================================================

class FinancialReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for comprehensive financial report management.
    
    Provides endpoints for:
    - Generating reports (Income Statement, Balance Sheet, General Ledger, Sub-ledger)
    - Export to Word/Excel/CSV
    - Update existing reports with new filters
    - Cache management for large reports
    - Report templates and scheduling
    
    Endpoints:
    - GET /financial-reports/ - List all reports with filters
    - POST /financial-reports/ - Generate a new report
    - GET /financial-reports/{id}/ - Get report with data
    - PUT /financial-reports/{id}/ - Update report and regenerate
    - DELETE /financial-reports/{id}/ - Delete report
    - POST /financial-reports/{id}/export/ - Export to Word/Excel/CSV
    - GET /financial-reports/{id}/exports/ - List exports for a report
    - POST /financial-reports/{id}/refresh/ - Force refresh cached data
    - GET /financial-reports/types/ - Get available report types
    - GET /financial-reports/templates/ - List report templates
    - POST /financial-reports/templates/ - Create template
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Report.objects.all()
        
        # Filter by report type
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range (generated_at)
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(generated_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(generated_at__date__lte=date_to)
        
        # Filter by project in filter_config
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(filter_config__project_id=project_id)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('generated_by').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        if self.action == 'create':
            return GenerateReportSerializer
        if self.action in ['update', 'partial_update']:
            return UpdateReportSerializer
        if self.action == 'export':
            return ExportReportSerializer
        return ReportSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Generate a new financial report.
        
        Request body:
        {
            "report_type": "INCOME_STATEMENT",
            "name": "Q4 2024 Income Statement",
            "description": "Income statement for Q4 2024",
            "filters": {
                "date_from": "2024-10-01",
                "date_to": "2024-12-31",
                "project_id": "uuid",  // optional
                "vendor_id": "uuid",   // optional
                "category": "OPERATING",  // optional
                "account_ids": ["uuid1", "uuid2"],  // optional
                "include_zero_balances": false,
                "comparison_period": "previous_year"  // optional
            }
        }
        """
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create report record
        report = Report.objects.create(
            tenant=getattr(request, 'tenant', None),
            report_type=serializer.validated_data['report_type'],
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            filter_config=serializer.validated_data.get('filters', {}),
            generated_by=request.user,
            status=ReportStatus.GENERATING.value
        )
        
        try:
            # Generate report data
            generator = ReportGeneratorService()
            report_data = generator.generate_report(report)
            
            # Store generated data
            report.cached_data = report_data
            report.status = ReportStatus.COMPLETED.value
            report.generated_at = timezone.now()
            report.save()
            
            return Response(
                ReportSerializer(report).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            report.save()
            
            return Response(
                {'error': str(e), 'report_id': str(report.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Get report with full data."""
        report = self.get_object()
        
        # Check if data needs refresh
        cache_service = ReportCacheService()
        cached_data = cache_service.get(report)
        
        if cached_data is None and report.cached_data:
            # Re-cache from stored data
            cache_service.set(report, report.cached_data)
            cached_data = report.cached_data
        
        serializer = ReportSerializer(report)
        data = serializer.data
        data['report_data'] = cached_data or report.cached_data
        
        return Response(data)
    
    def update(self, request, *args, **kwargs):
        """
        Update report filters and regenerate.
        Increments version number.
        """
        report = self.get_object()
        serializer = UpdateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update report fields
        if 'name' in serializer.validated_data:
            report.name = serializer.validated_data['name']
        if 'description' in serializer.validated_data:
            report.description = serializer.validated_data['description']
        if 'filters' in serializer.validated_data:
            report.filter_config = serializer.validated_data['filters']
        
        # Regenerate
        report.status = ReportStatus.GENERATING.value
        report.version += 1
        report.save()
        
        try:
            generator = ReportGeneratorService()
            report_data = generator.generate_report(report, force_refresh=True)
            
            report.cached_data = report_data
            report.status = ReportStatus.COMPLETED.value
            report.generated_at = timezone.now()
            report.save()
            
            return Response(ReportSerializer(report).data)
            
        except Exception as e:
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            report.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """
        Export report to Word/Excel/CSV.
        
        Request body:
        {
            "format": "EXCEL",  // EXCEL, WORD, CSV
            "filename": "Q4_Income_Statement"  // optional
        }
        """
        report = self.get_object()
        
        if report.status != ReportStatus.COMPLETED.value:
            return Response(
                {'error': 'Report must be completed before export'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExportReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export_format = serializer.validated_data['format']
        filename = serializer.validated_data.get('filename')
        
        try:
            exporter = ReportExporterService()
            export_record = exporter.export_report(report, export_format, filename)
            
            return Response({
                'message': 'Report exported successfully',
                'export': ReportExportSerializer(export_record).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Export failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def exports(self, request, pk=None):
        """List all exports for a report."""
        report = self.get_object()
        exports = ReportExport.objects.filter(report=report).order_by('-created_at')
        
        page = self.paginate_queryset(exports)
        if page is not None:
            serializer = ReportExportListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReportExportListSerializer(exports, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download an export file."""
        report = self.get_object()
        
        export_id = request.query_params.get('export_id')
        if not export_id:
            # Get latest export
            export_record = ReportExport.objects.filter(report=report).order_by('-created_at').first()
        else:
            export_record = ReportExport.objects.filter(id=export_id, report=report).first()
        
        if not export_record or not export_record.file:
            return Response(
                {'error': 'Export file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Increment download count
        export_record.download_count += 1
        export_record.save(update_fields=['download_count'])
        
        # Determine content type
        content_types = {
            ExportFormat.EXCEL.value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ExportFormat.WORD.value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ExportFormat.CSV.value: 'text/csv',
            ExportFormat.PDF.value: 'application/pdf',
        }
        content_type = content_types.get(export_record.export_format, 'application/octet-stream')
        
        response = HttpResponse(export_record.file.read(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{export_record.file_name}"'
        return response
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Force refresh report data (clear cache and regenerate).
        """
        report = self.get_object()
        
        # Clear cache
        cache_service = ReportCacheService()
        cache_service.delete(report)
        
        # Regenerate
        report.status = ReportStatus.GENERATING.value
        report.save()
        
        try:
            generator = ReportGeneratorService()
            report_data = generator.generate_report(report, force_refresh=True)
            
            report.cached_data = report_data
            report.status = ReportStatus.COMPLETED.value
            report.generated_at = timezone.now()
            report.save()
            
            return Response({
                'message': 'Report refreshed successfully',
                'report': ReportSerializer(report).data
            })
            
        except Exception as e:
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            report.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available report types with descriptions."""
        types = []
        for report_type in ReportType:
            types.append({
                'value': report_type.value,
                'label': report_type.value.replace('_', ' ').title(),
                'description': self._get_report_type_description(report_type.value)
            })
        return Response({'report_types': types})
    
    @action(detail=False, methods=['get', 'post'])
    def templates(self, request):
        """List or create report templates."""
        if request.method == 'GET':
            templates = ReportTemplate.objects.filter(is_active=True)
            
            # Filter by report type
            report_type = request.query_params.get('report_type')
            if report_type:
                templates = templates.filter(report_type=report_type)
            
            serializer = ReportTemplateSerializer(templates, many=True)
            return Response({'templates': serializer.data})
        
        elif request.method == 'POST':
            serializer = ReportTemplateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            template = ReportTemplate.objects.create(
                tenant=getattr(request, 'tenant', None),
                report_type=serializer.validated_data['report_type'],
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                template_config=serializer.validated_data.get('template_config', {}),
                column_mappings=serializer.validated_data.get('column_mappings', {}),
                created_by=request.user
            )
            
            return Response(
                ReportTemplateSerializer(template).data,
                status=status.HTTP_201_CREATED
            )
    
    @action(detail=False, methods=['get'])
    def schedules(self, request):
        """List report schedules."""
        schedules = ReportSchedule.objects.filter(is_active=True)
        serializer = ReportScheduleSerializer(schedules, many=True)
        return Response({'schedules': serializer.data})
    
    @action(detail=False, methods=['post'])
    def create_schedule(self, request):
        """Create a new report schedule."""
        serializer = ReportScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        schedule = ReportSchedule.objects.create(
            tenant=getattr(request, 'tenant', None),
            report_type=serializer.validated_data['report_type'],
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            filter_config=serializer.validated_data.get('filter_config', {}),
            schedule_cron=serializer.validated_data['schedule_cron'],
            export_format=serializer.validated_data.get('export_format', ExportFormat.EXCEL.value),
            email_recipients=serializer.validated_data.get('email_recipients', []),
            created_by=request.user
        )
        
        return Response(
            ReportScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get report statistics."""
        queryset = self.get_queryset()
        
        total = queryset.count()
        by_type = queryset.values('report_type').annotate(count=Count('id'))
        by_status = queryset.values('status').annotate(count=Count('id'))
        
        # Recent exports
        recent_exports = ReportExport.objects.order_by('-created_at')[:10]
        
        return Response({
            'total_reports': total,
            'by_type': {item['report_type']: item['count'] for item in by_type},
            'by_status': {item['status']: item['count'] for item in by_status},
            'recent_exports': ReportExportListSerializer(recent_exports, many=True).data
        })
    
    def _get_report_type_description(self, report_type):
        """Get description for report type."""
        descriptions = {
            ReportType.INCOME_STATEMENT.value: 'Shows revenue, expenses, and net income/loss for a period',
            ReportType.BALANCE_SHEET.value: 'Shows assets, liabilities, and equity at a point in time',
            ReportType.GENERAL_LEDGER.value: 'Detailed transactions for all accounts with running balances',
            ReportType.SUB_LEDGER.value: 'Detailed transactions for specific accounts (AR, AP, etc.)',
            ReportType.TRIAL_BALANCE.value: 'Lists all account balances to verify debits equal credits',
            ReportType.CASH_FLOW.value: 'Shows cash inflows and outflows from operations, investing, and financing',
            ReportType.ACCOUNTS_RECEIVABLE.value: 'Aging report of outstanding customer invoices',
            ReportType.ACCOUNTS_PAYABLE.value: 'Aging report of outstanding vendor bills',
            ReportType.EXPENSE_REPORT.value: 'Summary of expenses by category, project, or vendor',
            ReportType.CUSTOM.value: 'Custom report with user-defined parameters',
        }
        return descriptions.get(report_type, 'Financial report')
