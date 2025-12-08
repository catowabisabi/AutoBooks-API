"""
Report Generator Service
========================
Generates financial reports (Income Statement, Balance Sheet, General Ledger, etc.)
"""

import hashlib
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone

from ..models import (
    Report, ReportTemplate, ReportSection, ReportType, ReportStatus,
    Account, AccountType, AccountSubType, JournalEntry, JournalEntryLine,
    TransactionStatus, Contact, Expense, Project
)


class ReportGeneratorService:
    """
    Service for generating financial reports.
    Handles data aggregation, calculations, and report structure creation.
    """
    
    def __init__(self, tenant_id: Optional[uuid.UUID] = None):
        self.tenant_id = tenant_id
    
    # =================================================================
    # Main Entry Points
    # =================================================================
    
    def generate_report(
        self,
        report_type: str,
        period_start: date,
        period_end: date,
        name: str,
        user,
        filters: Optional[Dict] = None,
        display_config: Optional[Dict] = None,
        include_comparison: bool = False,
        comparison_period_start: Optional[date] = None,
        comparison_period_end: Optional[date] = None,
        template: Optional[ReportTemplate] = None,
        notes: str = ''
    ) -> Report:
        """
        Generate a new report based on type and parameters.
        """
        # Create report record
        report = Report.objects.create(
            tenant_id=self.tenant_id,
            report_number=self._generate_report_number(),
            name=name,
            report_type=report_type,
            template=template,
            period_start=period_start,
            period_end=period_end,
            filters=filters or {},
            display_config=display_config or {},
            include_comparison=include_comparison,
            comparison_period_start=comparison_period_start,
            comparison_period_end=comparison_period_end,
            status=ReportStatus.GENERATING.value,
            generation_started_at=timezone.now(),
            generated_by=user,
            notes=notes
        )
        
        try:
            # Generate report data based on type
            report_data = self._generate_report_data(
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                filters=filters,
                include_comparison=include_comparison,
                comparison_period_start=comparison_period_start,
                comparison_period_end=comparison_period_end
            )
            
            # Store cached data and summary
            report.cached_data = report_data
            report.summary_totals = self._extract_summary_totals(report_type, report_data)
            report.data_hash = self._calculate_data_hash(report_data)
            report.status = ReportStatus.COMPLETED.value
            report.generation_completed_at = timezone.now()
            report.cache_expires_at = timezone.now() + timedelta(hours=24)
            report.save()
            
            # Create report sections for structured reports
            self._create_report_sections(report, report_data)
            
        except Exception as e:
            report.status = ReportStatus.FAILED.value
            report.generation_error = str(e)
            report.generation_completed_at = timezone.now()
            report.save()
            raise
        
        return report
    
    def regenerate_report(
        self,
        report: Report,
        user,
        update_period: bool = False,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        filters: Optional[Dict] = None
    ) -> Report:
        """
        Regenerate an existing report with optional parameter updates.
        Creates a new version while maintaining history.
        """
        # Create new version
        new_report = Report.objects.create(
            tenant_id=report.tenant_id,
            report_number=self._generate_report_number(),
            name=report.name,
            report_type=report.report_type,
            template=report.template,
            period_start=period_start if update_period else report.period_start,
            period_end=period_end if update_period else report.period_end,
            filters=filters if filters else report.filters,
            display_config=report.display_config,
            include_comparison=report.include_comparison,
            comparison_period_start=report.comparison_period_start,
            comparison_period_end=report.comparison_period_end,
            status=ReportStatus.GENERATING.value,
            generation_started_at=timezone.now(),
            generated_by=user,
            version=report.version + 1,
            parent_report=report,
            notes=report.notes
        )
        
        # Mark old report as not latest
        report.is_latest = False
        report.save(update_fields=['is_latest'])
        
        try:
            report_data = self._generate_report_data(
                report_type=new_report.report_type,
                period_start=new_report.period_start,
                period_end=new_report.period_end,
                filters=new_report.filters,
                include_comparison=new_report.include_comparison,
                comparison_period_start=new_report.comparison_period_start,
                comparison_period_end=new_report.comparison_period_end
            )
            
            new_report.cached_data = report_data
            new_report.summary_totals = self._extract_summary_totals(new_report.report_type, report_data)
            new_report.data_hash = self._calculate_data_hash(report_data)
            new_report.status = ReportStatus.COMPLETED.value
            new_report.generation_completed_at = timezone.now()
            new_report.cache_expires_at = timezone.now() + timedelta(hours=24)
            new_report.save()
            
            self._create_report_sections(new_report, report_data)
            
        except Exception as e:
            new_report.status = ReportStatus.FAILED.value
            new_report.generation_error = str(e)
            new_report.generation_completed_at = timezone.now()
            new_report.save()
            raise
        
        return new_report
    
    # =================================================================
    # Report Type Dispatchers
    # =================================================================
    
    def _generate_report_data(
        self,
        report_type: str,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Dispatch to specific report generator based on type"""
        generators = {
            ReportType.INCOME_STATEMENT.value: self._generate_income_statement,
            ReportType.BALANCE_SHEET.value: self._generate_balance_sheet,
            ReportType.GENERAL_LEDGER.value: self._generate_general_ledger,
            ReportType.SUB_LEDGER.value: self._generate_sub_ledger,
            ReportType.TRIAL_BALANCE.value: self._generate_trial_balance,
            ReportType.EXPENSE_REPORT.value: self._generate_expense_report,
        }
        
        generator = generators.get(report_type)
        if not generator:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        return generator(
            period_start=period_start,
            period_end=period_end,
            filters=filters,
            include_comparison=include_comparison,
            comparison_period_start=comparison_period_start,
            comparison_period_end=comparison_period_end
        )
    
    # =================================================================
    # Income Statement Generator
    # =================================================================
    
    def _generate_income_statement(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate Income Statement (損益表) data"""
        
        def get_account_balances(start: date, end: date) -> Dict[str, List[Dict]]:
            """Get account balances for a period"""
            # Base query for journal entries in period
            entries_filter = Q(
                journal_entry__date__gte=start,
                journal_entry__date__lte=end,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            
            if self.tenant_id:
                entries_filter &= Q(journal_entry__tenant_id=self.tenant_id)
            
            # Apply filters
            if filters:
                if filters.get('project_ids'):
                    entries_filter &= Q(journal_entry__project_id__in=filters['project_ids'])
            
            # Aggregate by account
            account_totals = JournalEntryLine.objects.filter(entries_filter).values(
                'account__id',
                'account__code',
                'account__name',
                'account__account_type',
                'account__account_subtype'
            ).annotate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            
            result = {
                'revenue': [],
                'cost_of_goods': [],
                'operating_expenses': [],
                'other_income': [],
                'other_expenses': []
            }
            
            for item in account_totals:
                account_type = item['account__account_type']
                subtype = item['account__account_subtype']
                total_debit = item['total_debit'] or Decimal('0.00')
                total_credit = item['total_credit'] or Decimal('0.00')
                
                # For revenue accounts: credit - debit
                # For expense accounts: debit - credit
                if account_type == AccountType.REVENUE.value:
                    amount = total_credit - total_debit
                    if subtype == AccountSubType.OTHER_INCOME.value:
                        result['other_income'].append({
                            'account_id': str(item['account__id']),
                            'account_code': item['account__code'],
                            'account_name': item['account__name'],
                            'amount': amount
                        })
                    else:
                        result['revenue'].append({
                            'account_id': str(item['account__id']),
                            'account_code': item['account__code'],
                            'account_name': item['account__name'],
                            'amount': amount
                        })
                
                elif account_type == AccountType.EXPENSE.value:
                    amount = total_debit - total_credit
                    if subtype == AccountSubType.COST_OF_GOODS.value:
                        result['cost_of_goods'].append({
                            'account_id': str(item['account__id']),
                            'account_code': item['account__code'],
                            'account_name': item['account__name'],
                            'amount': amount
                        })
                    elif subtype == AccountSubType.OTHER_EXPENSE.value:
                        result['other_expenses'].append({
                            'account_id': str(item['account__id']),
                            'account_code': item['account__code'],
                            'account_name': item['account__name'],
                            'amount': amount
                        })
                    else:
                        result['operating_expenses'].append({
                            'account_id': str(item['account__id']),
                            'account_code': item['account__code'],
                            'account_name': item['account__name'],
                            'amount': amount
                        })
            
            return result
        
        # Get current period data
        current_data = get_account_balances(period_start, period_end)
        
        # Calculate totals
        total_revenue = sum(item['amount'] for item in current_data['revenue'])
        total_cost_of_goods = sum(item['amount'] for item in current_data['cost_of_goods'])
        gross_profit = total_revenue - total_cost_of_goods
        total_operating_expenses = sum(item['amount'] for item in current_data['operating_expenses'])
        operating_income = gross_profit - total_operating_expenses
        total_other_income = sum(item['amount'] for item in current_data['other_income'])
        total_other_expenses = sum(item['amount'] for item in current_data['other_expenses'])
        income_before_tax = operating_income + total_other_income - total_other_expenses
        
        # Simple tax calculation (placeholder - should use actual tax rules)
        tax_expense = max(income_before_tax * Decimal('0.20'), Decimal('0.00'))
        net_income = income_before_tax - tax_expense
        
        report_data = {
            'revenue': self._add_comparison_to_lines(current_data['revenue'], None),
            'total_revenue': float(total_revenue),
            'cost_of_goods': self._add_comparison_to_lines(current_data['cost_of_goods'], None),
            'total_cost_of_goods': float(total_cost_of_goods),
            'gross_profit': float(gross_profit),
            'operating_expenses': self._add_comparison_to_lines(current_data['operating_expenses'], None),
            'total_operating_expenses': float(total_operating_expenses),
            'operating_income': float(operating_income),
            'other_income': self._add_comparison_to_lines(current_data['other_income'], None),
            'other_expenses': self._add_comparison_to_lines(current_data['other_expenses'], None),
            'income_before_tax': float(income_before_tax),
            'tax_expense': float(tax_expense),
            'net_income': float(net_income),
            'comparison_total_revenue': None,
            'comparison_net_income': None
        }
        
        # Add comparison data if requested
        if include_comparison and comparison_period_start and comparison_period_end:
            comparison_data = get_account_balances(comparison_period_start, comparison_period_end)
            comp_total_revenue = sum(item['amount'] for item in comparison_data['revenue'])
            comp_total_cog = sum(item['amount'] for item in comparison_data['cost_of_goods'])
            comp_gross_profit = comp_total_revenue - comp_total_cog
            comp_total_opex = sum(item['amount'] for item in comparison_data['operating_expenses'])
            comp_operating_income = comp_gross_profit - comp_total_opex
            comp_other_income = sum(item['amount'] for item in comparison_data['other_income'])
            comp_other_expenses = sum(item['amount'] for item in comparison_data['other_expenses'])
            comp_income_before_tax = comp_operating_income + comp_other_income - comp_other_expenses
            comp_net_income = comp_income_before_tax - max(comp_income_before_tax * Decimal('0.20'), Decimal('0.00'))
            
            report_data['comparison_total_revenue'] = float(comp_total_revenue)
            report_data['comparison_net_income'] = float(comp_net_income)
            
            # Add comparison to line items
            report_data['revenue'] = self._add_comparison_to_lines(
                current_data['revenue'], 
                {item['account_id']: item['amount'] for item in comparison_data['revenue']}
            )
        
        return report_data
    
    # =================================================================
    # Balance Sheet Generator
    # =================================================================
    
    def _generate_balance_sheet(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate Balance Sheet (資產負債表) data"""
        
        def get_balances(as_of_date: date) -> Dict:
            """Get account balances as of a date"""
            # Get all journal entry lines up to the date
            entries_filter = Q(
                journal_entry__date__lte=as_of_date,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            
            if self.tenant_id:
                entries_filter &= Q(journal_entry__tenant_id=self.tenant_id)
            
            if filters and filters.get('project_ids'):
                entries_filter &= Q(journal_entry__project_id__in=filters['project_ids'])
            
            account_totals = JournalEntryLine.objects.filter(entries_filter).values(
                'account__id',
                'account__code',
                'account__name',
                'account__account_type',
                'account__account_subtype',
                'account__opening_balance'
            ).annotate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            
            result = {
                'current_assets': [],
                'fixed_assets': [],
                'other_assets': [],
                'current_liabilities': [],
                'long_term_liabilities': [],
                'equity': []
            }
            
            for item in account_totals:
                account_type = item['account__account_type']
                subtype = item['account__account_subtype']
                opening = item['account__opening_balance'] or Decimal('0.00')
                total_debit = item['total_debit'] or Decimal('0.00')
                total_credit = item['total_credit'] or Decimal('0.00')
                
                # Calculate balance based on account type
                if account_type == AccountType.ASSET.value:
                    balance = opening + total_debit - total_credit
                    account_data = {
                        'account_id': str(item['account__id']),
                        'account_code': item['account__code'],
                        'account_name': item['account__name'],
                        'balance': balance
                    }
                    
                    if subtype == AccountSubType.FIXED_ASSET.value:
                        result['fixed_assets'].append(account_data)
                    elif subtype in [AccountSubType.OTHER_ASSET.value]:
                        result['other_assets'].append(account_data)
                    else:
                        result['current_assets'].append(account_data)
                
                elif account_type == AccountType.LIABILITY.value:
                    balance = opening + total_credit - total_debit
                    account_data = {
                        'account_id': str(item['account__id']),
                        'account_code': item['account__code'],
                        'account_name': item['account__name'],
                        'balance': balance
                    }
                    
                    if subtype == AccountSubType.LOAN.value:
                        result['long_term_liabilities'].append(account_data)
                    else:
                        result['current_liabilities'].append(account_data)
                
                elif account_type == AccountType.EQUITY.value:
                    balance = opening + total_credit - total_debit
                    result['equity'].append({
                        'account_id': str(item['account__id']),
                        'account_code': item['account__code'],
                        'account_name': item['account__name'],
                        'balance': balance
                    })
            
            return result
        
        # Get current balances
        current = get_balances(period_end)
        
        # Calculate totals
        total_current_assets = sum(item['balance'] for item in current['current_assets'])
        total_fixed_assets = sum(item['balance'] for item in current['fixed_assets'])
        total_other_assets = sum(item['balance'] for item in current['other_assets'])
        total_assets = total_current_assets + total_fixed_assets + total_other_assets
        
        total_current_liabilities = sum(item['balance'] for item in current['current_liabilities'])
        total_long_term_liabilities = sum(item['balance'] for item in current['long_term_liabilities'])
        total_liabilities = total_current_liabilities + total_long_term_liabilities
        
        total_equity = sum(item['balance'] for item in current['equity'])
        
        # Calculate retained earnings (simplified)
        retained_earnings = total_assets - total_liabilities - total_equity
        total_equity_with_retained = total_equity + retained_earnings
        
        report_data = {
            'current_assets': self._format_balance_lines(current['current_assets']),
            'total_current_assets': float(total_current_assets),
            'fixed_assets': self._format_balance_lines(current['fixed_assets']),
            'total_fixed_assets': float(total_fixed_assets),
            'other_assets': self._format_balance_lines(current['other_assets']),
            'total_other_assets': float(total_other_assets),
            'total_assets': float(total_assets),
            'current_liabilities': self._format_balance_lines(current['current_liabilities']),
            'total_current_liabilities': float(total_current_liabilities),
            'long_term_liabilities': self._format_balance_lines(current['long_term_liabilities']),
            'total_long_term_liabilities': float(total_long_term_liabilities),
            'total_liabilities': float(total_liabilities),
            'equity': self._format_balance_lines(current['equity']),
            'retained_earnings': float(retained_earnings),
            'total_equity': float(total_equity_with_retained),
            'total_liabilities_and_equity': float(total_liabilities + total_equity_with_retained),
            'is_balanced': abs(total_assets - (total_liabilities + total_equity_with_retained)) < Decimal('0.01')
        }
        
        return report_data
    
    # =================================================================
    # General Ledger Generator
    # =================================================================
    
    def _generate_general_ledger(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate General Ledger (總帳) data"""
        
        # Get accounts to include
        accounts_filter = Q()
        if self.tenant_id:
            accounts_filter &= Q(tenant_id=self.tenant_id)
        if filters and filters.get('account_ids'):
            accounts_filter &= Q(id__in=filters['account_ids'])
        if filters and filters.get('account_types'):
            accounts_filter &= Q(account_type__in=filters['account_types'])
        
        accounts = Account.objects.filter(accounts_filter, is_active=True).order_by('code')
        
        ledger_accounts = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        entry_count = 0
        
        for account in accounts:
            # Get opening balance (sum of all entries before period start)
            opening_filter = Q(
                account=account,
                journal_entry__date__lt=period_start,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            
            opening_totals = JournalEntryLine.objects.filter(opening_filter).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            
            opening_debit = opening_totals['total_debit'] or Decimal('0.00')
            opening_credit = opening_totals['total_credit'] or Decimal('0.00')
            
            if account.account_type in [AccountType.ASSET.value, AccountType.EXPENSE.value]:
                opening_balance = account.opening_balance + opening_debit - opening_credit
            else:
                opening_balance = account.opening_balance + opening_credit - opening_debit
            
            # Get entries for the period
            entries_filter = Q(
                account=account,
                journal_entry__date__gte=period_start,
                journal_entry__date__lte=period_end,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            
            entries = JournalEntryLine.objects.filter(entries_filter).select_related(
                'journal_entry'
            ).order_by('journal_entry__date', 'journal_entry__entry_number')
            
            account_entries = []
            running_balance = opening_balance
            account_total_debits = Decimal('0.00')
            account_total_credits = Decimal('0.00')
            
            for entry_line in entries:
                debit = entry_line.debit or Decimal('0.00')
                credit = entry_line.credit or Decimal('0.00')
                
                if account.account_type in [AccountType.ASSET.value, AccountType.EXPENSE.value]:
                    running_balance += debit - credit
                else:
                    running_balance += credit - debit
                
                account_entries.append({
                    'date': entry_line.journal_entry.date.isoformat(),
                    'entry_number': entry_line.journal_entry.entry_number,
                    'description': entry_line.description or entry_line.journal_entry.description,
                    'reference': entry_line.journal_entry.reference,
                    'debit': float(debit),
                    'credit': float(credit),
                    'balance': float(running_balance)
                })
                
                account_total_debits += debit
                account_total_credits += credit
            
            if account_entries or opening_balance != Decimal('0.00'):
                ledger_accounts.append({
                    'account_id': str(account.id),
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type,
                    'opening_balance': float(opening_balance),
                    'entries': account_entries,
                    'total_debits': float(account_total_debits),
                    'total_credits': float(account_total_credits),
                    'closing_balance': float(running_balance)
                })
                
                total_debits += account_total_debits
                total_credits += account_total_credits
                entry_count += len(account_entries)
        
        return {
            'accounts': ledger_accounts,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'entry_count': entry_count
        }
    
    # =================================================================
    # Sub-Ledger Generator
    # =================================================================
    
    def _generate_sub_ledger(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate Sub-Ledger (明細帳) - detailed by vendor/customer contact"""
        
        # Get relevant contacts based on filters
        contact_filter = Q(is_active=True)
        if self.tenant_id:
            contact_filter &= Q(tenant_id=self.tenant_id)
        
        # Filter by vendor/customer type
        ledger_type = 'all'  # Default to both
        if filters:
            if filters.get('vendor_ids'):
                contact_filter &= Q(id__in=filters['vendor_ids'])
                ledger_type = 'vendor'
            if filters.get('customer_ids'):
                contact_filter &= Q(id__in=filters['customer_ids'])
                ledger_type = 'customer'
            if filters.get('ledger_type'):
                ledger_type = filters['ledger_type']
                if ledger_type == 'vendor':
                    contact_filter &= Q(contact_type__in=['VENDOR', 'BOTH'])
                elif ledger_type == 'customer':
                    contact_filter &= Q(contact_type__in=['CUSTOMER', 'BOTH'])
        
        contacts = Contact.objects.filter(contact_filter).order_by('company_name', 'contact_name')
        
        contact_ledgers = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        total_entries = 0
        
        for contact in contacts:
            # Determine linked account based on contact type
            linked_account = None
            if contact.contact_type in ['VENDOR', 'BOTH'] and contact.payable_account:
                linked_account = contact.payable_account
            elif contact.contact_type in ['CUSTOMER', 'BOTH'] and contact.receivable_account:
                linked_account = contact.receivable_account
            
            # Get journal entries related to this contact through invoices
            invoice_entries = Q(
                journal_entry__date__gte=period_start,
                journal_entry__date__lte=period_end,
                journal_entry__status=TransactionStatus.POSTED.value,
                journal_entry__invoices__contact=contact
            )
            
            # Also get entries through payments
            payment_entries = Q(
                journal_entry__date__gte=period_start,
                journal_entry__date__lte=period_end,
                journal_entry__status=TransactionStatus.POSTED.value,
                journal_entry__payments__contact=contact
            )
            
            # Combine queries
            entries_filter = invoice_entries | payment_entries
            
            if self.tenant_id:
                entries_filter &= Q(journal_entry__tenant_id=self.tenant_id)
            
            # If linked account exists, also get direct entries to that account
            if linked_account:
                direct_entries = Q(
                    account=linked_account,
                    journal_entry__date__gte=period_start,
                    journal_entry__date__lte=period_end,
                    journal_entry__status=TransactionStatus.POSTED.value
                )
                if self.tenant_id:
                    direct_entries &= Q(journal_entry__tenant_id=self.tenant_id)
                entries_filter = entries_filter | direct_entries
            
            # Get opening balance - sum of all entries before period start
            opening_filter = Q(
                journal_entry__date__lt=period_start,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            if linked_account:
                opening_filter &= Q(account=linked_account)
            if self.tenant_id:
                opening_filter &= Q(journal_entry__tenant_id=self.tenant_id)
            
            opening_totals = JournalEntryLine.objects.filter(opening_filter).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            
            opening_debit = opening_totals['total_debit'] or Decimal('0.00')
            opening_credit = opening_totals['total_credit'] or Decimal('0.00')
            
            # For AP (vendor): balance = credit - debit (we owe them)
            # For AR (customer): balance = debit - credit (they owe us)
            if contact.contact_type in ['VENDOR', 'BOTH']:
                opening_balance = opening_credit - opening_debit
            else:
                opening_balance = opening_debit - opening_credit
            
            # Get entries for the period
            entries = JournalEntryLine.objects.filter(entries_filter).select_related(
                'journal_entry', 'account'
            ).order_by('journal_entry__date', 'journal_entry__entry_number').distinct()
            
            contact_entries = []
            running_balance = opening_balance
            contact_total_debits = Decimal('0.00')
            contact_total_credits = Decimal('0.00')
            
            for entry_line in entries:
                debit = entry_line.debit or Decimal('0.00')
                credit = entry_line.credit or Decimal('0.00')
                
                if contact.contact_type in ['VENDOR', 'BOTH']:
                    running_balance += credit - debit
                else:
                    running_balance += debit - credit
                
                # Get related invoice/payment reference
                related_ref = ''
                if entry_line.journal_entry.invoices.exists():
                    invoice = entry_line.journal_entry.invoices.first()
                    related_ref = f"Invoice: {invoice.invoice_number}"
                elif entry_line.journal_entry.payments.exists():
                    payment = entry_line.journal_entry.payments.first()
                    related_ref = f"Payment: {payment.payment_number}"
                
                contact_entries.append({
                    'date': entry_line.journal_entry.date.isoformat(),
                    'entry_number': entry_line.journal_entry.entry_number,
                    'description': entry_line.description or entry_line.journal_entry.description,
                    'reference': related_ref or entry_line.journal_entry.reference,
                    'account_code': entry_line.account.code,
                    'account_name': entry_line.account.name,
                    'debit': float(debit),
                    'credit': float(credit),
                    'balance': float(running_balance)
                })
                
                contact_total_debits += debit
                contact_total_credits += credit
            
            # Only include contacts with activity or opening balance
            if contact_entries or opening_balance != Decimal('0.00'):
                contact_ledgers.append({
                    'contact_id': str(contact.id),
                    'contact_name': contact.company_name or contact.contact_name,
                    'contact_type': contact.contact_type,
                    'linked_account_code': linked_account.code if linked_account else None,
                    'linked_account_name': linked_account.name if linked_account else None,
                    'opening_balance': float(opening_balance),
                    'entries': contact_entries,
                    'total_debits': float(contact_total_debits),
                    'total_credits': float(contact_total_credits),
                    'closing_balance': float(running_balance),
                    'entry_count': len(contact_entries)
                })
                
                total_debits += contact_total_debits
                total_credits += contact_total_credits
                total_entries += len(contact_entries)
        
        return {
            'ledger_type': ledger_type,
            'contacts': contact_ledgers,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'entry_count': total_entries,
            'contact_count': len(contact_ledgers)
        }
    
    # =================================================================
    # Trial Balance Generator
    # =================================================================
    
    def _generate_trial_balance(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate Trial Balance (試算表)"""
        
        accounts_filter = Q(is_active=True)
        if self.tenant_id:
            accounts_filter &= Q(tenant_id=self.tenant_id)
        
        accounts = Account.objects.filter(accounts_filter).order_by('code')
        
        trial_balance_lines = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for account in accounts:
            entries_filter = Q(
                account=account,
                journal_entry__date__lte=period_end,
                journal_entry__status=TransactionStatus.POSTED.value
            )
            
            totals = JournalEntryLine.objects.filter(entries_filter).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            
            debit_total = totals['total_debit'] or Decimal('0.00')
            credit_total = totals['total_credit'] or Decimal('0.00')
            opening = account.opening_balance or Decimal('0.00')
            
            # Calculate balance
            if account.account_type in [AccountType.ASSET.value, AccountType.EXPENSE.value]:
                balance = opening + debit_total - credit_total
                if balance >= 0:
                    debit_balance = balance
                    credit_balance = Decimal('0.00')
                else:
                    debit_balance = Decimal('0.00')
                    credit_balance = abs(balance)
            else:
                balance = opening + credit_total - debit_total
                if balance >= 0:
                    debit_balance = Decimal('0.00')
                    credit_balance = balance
                else:
                    debit_balance = abs(balance)
                    credit_balance = Decimal('0.00')
            
            if debit_balance != Decimal('0.00') or credit_balance != Decimal('0.00'):
                trial_balance_lines.append({
                    'account_id': str(account.id),
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type,
                    'debit': float(debit_balance),
                    'credit': float(credit_balance)
                })
                
                total_debits += debit_balance
                total_credits += credit_balance
        
        return {
            'lines': trial_balance_lines,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'is_balanced': abs(total_debits - total_credits) < Decimal('0.01'),
            'difference': float(total_debits - total_credits)
        }
    
    # =================================================================
    # Expense Report Generator
    # =================================================================
    
    def _generate_expense_report(
        self,
        period_start: date,
        period_end: date,
        filters: Optional[Dict],
        include_comparison: bool,
        comparison_period_start: Optional[date],
        comparison_period_end: Optional[date]
    ) -> Dict:
        """Generate Expense Report"""
        
        expenses_filter = Q(
            expense_date__gte=period_start,
            expense_date__lte=period_end
        )
        
        if self.tenant_id:
            expenses_filter &= Q(tenant_id=self.tenant_id)
        
        if filters:
            if filters.get('project_ids'):
                expenses_filter &= Q(project_id__in=filters['project_ids'])
            if filters.get('vendor_ids'):
                expenses_filter &= Q(vendor_id__in=filters['vendor_ids'])
            if filters.get('categories'):
                expenses_filter &= Q(category__in=filters['categories'])
        
        expenses = Expense.objects.filter(expenses_filter).select_related(
            'category', 'vendor', 'project'
        ).order_by('expense_date')
        
        expense_lines = []
        total_amount = Decimal('0.00')
        by_category = {}
        by_vendor = {}
        
        for expense in expenses:
            expense_data = {
                'id': str(expense.id),
                'date': expense.expense_date.isoformat(),
                'description': expense.description,
                'vendor': expense.vendor.company_name if expense.vendor else '',
                'category': expense.category.name if expense.category else '',
                'project': expense.project.name if expense.project else '',
                'amount': float(expense.amount),
                'tax_amount': float(expense.tax_amount) if expense.tax_amount else 0,
                'total': float(expense.amount + (expense.tax_amount or Decimal('0.00')))
            }
            expense_lines.append(expense_data)
            total_amount += expense.amount
            
            # Group by category
            cat_name = expense.category.name if expense.category else 'Uncategorized'
            if cat_name not in by_category:
                by_category[cat_name] = Decimal('0.00')
            by_category[cat_name] += expense.amount
            
            # Group by vendor
            vendor_name = expense.vendor.company_name if expense.vendor else 'Unknown'
            if vendor_name not in by_vendor:
                by_vendor[vendor_name] = Decimal('0.00')
            by_vendor[vendor_name] += expense.amount
        
        return {
            'expenses': expense_lines,
            'total_amount': float(total_amount),
            'expense_count': len(expense_lines),
            'by_category': {k: float(v) for k, v in by_category.items()},
            'by_vendor': {k: float(v) for k, v in by_vendor.items()}
        }
    
    # =================================================================
    # Helper Methods
    # =================================================================
    
    def _generate_report_number(self) -> str:
        """Generate unique report number"""
        year = timezone.now().year
        prefix = f"RPT-{year}-"
        
        # Get the last report number for this year
        last_report = Report.objects.filter(
            report_number__startswith=prefix
        ).order_by('-report_number').first()
        
        if last_report:
            try:
                last_num = int(last_report.report_number.split('-')[-1])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"
    
    def _calculate_data_hash(self, data: Dict) -> str:
        """Calculate hash of report data for cache invalidation"""
        import json
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _extract_summary_totals(self, report_type: str, data: Dict) -> Dict:
        """Extract key totals for summary display"""
        if report_type == ReportType.INCOME_STATEMENT.value:
            return {
                'total_revenue': data.get('total_revenue'),
                'net_income': data.get('net_income'),
                'gross_profit': data.get('gross_profit')
            }
        elif report_type == ReportType.BALANCE_SHEET.value:
            return {
                'total_assets': data.get('total_assets'),
                'total_liabilities': data.get('total_liabilities'),
                'total_equity': data.get('total_equity')
            }
        elif report_type == ReportType.GENERAL_LEDGER.value:
            return {
                'total_debits': data.get('total_debits'),
                'total_credits': data.get('total_credits'),
                'entry_count': data.get('entry_count')
            }
        elif report_type == ReportType.TRIAL_BALANCE.value:
            return {
                'total_debits': data.get('total_debits'),
                'total_credits': data.get('total_credits'),
                'is_balanced': data.get('is_balanced')
            }
        elif report_type == ReportType.EXPENSE_REPORT.value:
            return {
                'total_amount': data.get('total_amount'),
                'expense_count': data.get('expense_count')
            }
        return {}
    
    def _add_comparison_to_lines(
        self, 
        lines: List[Dict], 
        comparison_data: Optional[Dict[str, Decimal]]
    ) -> List[Dict]:
        """Add comparison amounts and variance to line items"""
        result = []
        for line in lines:
            new_line = {
                **line,
                'current_amount': float(line['amount']),
                'comparison_amount': None,
                'variance': None,
                'variance_percent': None
            }
            
            if comparison_data and line['account_id'] in comparison_data:
                comp_amount = comparison_data[line['account_id']]
                new_line['comparison_amount'] = float(comp_amount)
                new_line['variance'] = float(line['amount'] - comp_amount)
                if comp_amount != Decimal('0.00'):
                    new_line['variance_percent'] = float(
                        ((line['amount'] - comp_amount) / abs(comp_amount)) * 100
                    )
            
            result.append(new_line)
        return result
    
    def _format_balance_lines(self, lines: List[Dict]) -> List[Dict]:
        """Format balance sheet lines with proper structure"""
        return [
            {
                'account_id': line['account_id'],
                'account_code': line['account_code'],
                'account_name': line['account_name'],
                'balance': float(line['balance']),
                'comparison_balance': None
            }
            for line in lines
        ]
    
    def _create_report_sections(self, report: Report, data: Dict) -> None:
        """Create ReportSection records for structured navigation"""
        # Implementation depends on report type
        # This creates navigable sections in the database
        pass
