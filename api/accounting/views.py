from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Sum, Q
from decimal import Decimal
import io

from .models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    JournalEntry, JournalEntryLine, Contact, Invoice, InvoiceLine,
    Payment, PaymentAllocation, Expense, AccountType
)
from .serializers import (
    FiscalYearSerializer, AccountingPeriodSerializer, CurrencySerializer,
    TaxRateSerializer, AccountSerializer, AccountListSerializer,
    JournalEntrySerializer, JournalEntryCreateSerializer,
    ContactSerializer, ContactListSerializer,
    InvoiceSerializer, InvoiceListSerializer, InvoiceLineSerializer,
    PaymentSerializer, PaymentAllocationSerializer,
    ExpenseSerializer, ExpenseListSerializer
)


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
        
        # TODO: Implement PDF generation with reportlab or weasyprint
        # For now, return a simple response
        return Response({'message': 'PDF generation not yet implemented'})
    
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
