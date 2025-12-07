"""
Journal Entry Service
自動分錄服務

Features / 功能:
- Auto-create JournalEntry from Receipt / 從收據自動建立分錄
- Smart account mapping / 智能科目對應
- Batch processing / 批量處理
- Approval workflow / 審批流程
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from accounting.models import (
    Account, 
    JournalEntry, 
    JournalEntryLine,
    FiscalYear,
    AccountingPeriod,
    TransactionStatus,
    AccountType,
    AccountSubType,
    Contact,
    Expense,
)
from ai_assistants.models import Receipt, ReceiptStatus, ExpenseCategory


# =============================================================================
# Account Mapping Configuration
# =============================================================================

# Default expense category to account code mapping
EXPENSE_CATEGORY_ACCOUNT_MAP = {
    'MEALS': '6300',
    'TRANSPORTATION': '6200',
    'OFFICE_SUPPLIES': '6100',
    'UTILITIES': '6400',
    'ENTERTAINMENT': '6500',
    'RENT': '6600',
    'TELEPHONE': '6700',
    'INSURANCE': '6800',
    'MAINTENANCE': '6900',
    'TRAVEL': '6210',
    'TRAINING': '6350',
    'OTHER': '6999',
}

# Payment method to account code mapping
PAYMENT_ACCOUNT_MAP = {
    'CASH': '1000',
    'BANK_TRANSFER': '1100',
    'CREDIT_CARD': '2100',
    'DEBIT_CARD': '1100',
    'CHECK': '1100',
    'PAYPAL': '1100',
    'OTHER': '1100',
}


class JournalEntryService:
    """
    Service for creating and managing journal entries from receipts
    從收據建立和管理分錄的服務
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def get_or_create_account(self, code: str, name: str, account_type: str, 
                             subtype: str = None) -> Optional[Account]:
        """
        Get existing account or create if not exists
        獲取現有科目或建立新科目
        """
        try:
            account = Account.objects.filter(code=code).first()
            if account:
                return account
            
            # Create new account
            account = Account.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                account_subtype=subtype or '',
                is_active=True,
                is_system=False,
            )
            return account
        except Exception as e:
            print(f"Error getting/creating account: {e}")
            return None
    
    def get_expense_account(self, category: str) -> Optional[Account]:
        """
        Get expense account based on category
        根據分類獲取費用科目
        """
        code = EXPENSE_CATEGORY_ACCOUNT_MAP.get(category, '6999')
        
        # Try to get existing account
        account = Account.objects.filter(code=code, account_type=AccountType.EXPENSE.value).first()
        
        if account:
            return account
        
        # Create default expense account
        category_names = {
            'MEALS': '伙食費 / Meals',
            'TRANSPORTATION': '交通費 / Transportation',
            'OFFICE_SUPPLIES': '辦公用品 / Office Supplies',
            'UTILITIES': '水電費 / Utilities',
            'ENTERTAINMENT': '交際費 / Entertainment',
            'RENT': '租金 / Rent',
            'TELEPHONE': '電話費 / Telephone',
            'INSURANCE': '保險費 / Insurance',
            'MAINTENANCE': '維修費 / Maintenance',
            'TRAVEL': '差旅費 / Travel',
            'TRAINING': '培訓費 / Training',
            'OTHER': '其他費用 / Other Expenses',
        }
        
        return self.get_or_create_account(
            code=code,
            name=category_names.get(category, '其他費用 / Other Expenses'),
            account_type=AccountType.EXPENSE.value,
            subtype=AccountSubType.OPERATING.value,
        )
    
    def get_payment_account(self, payment_method: str) -> Optional[Account]:
        """
        Get payment account (Cash/Bank/Credit Card)
        獲取付款科目
        """
        code = PAYMENT_ACCOUNT_MAP.get(payment_method, '1100')
        
        account = Account.objects.filter(code=code).first()
        
        if account:
            return account
        
        # Create default accounts
        if payment_method == 'CASH':
            return self.get_or_create_account(
                code='1000',
                name='現金 / Cash',
                account_type=AccountType.ASSET.value,
                subtype=AccountSubType.CASH.value,
            )
        elif payment_method == 'CREDIT_CARD':
            return self.get_or_create_account(
                code='2100',
                name='應付帳款-信用卡 / Credit Card Payable',
                account_type=AccountType.LIABILITY.value,
                subtype=AccountSubType.CREDIT_CARD.value,
            )
        else:
            return self.get_or_create_account(
                code='1100',
                name='銀行存款 / Bank',
                account_type=AccountType.ASSET.value,
                subtype=AccountSubType.BANK.value,
            )
    
    def get_tax_account(self) -> Optional[Account]:
        """
        Get input VAT account
        獲取進項稅額科目
        """
        return self.get_or_create_account(
            code='1150',
            name='進項稅額 / Input VAT',
            account_type=AccountType.ASSET.value,
            subtype=AccountSubType.OTHER_ASSET.value,
        )
    
    def get_current_fiscal_year(self) -> Optional[FiscalYear]:
        """
        Get current active fiscal year
        獲取當前會計年度
        """
        today = timezone.now().date()
        fiscal_year = FiscalYear.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            is_active=True
        ).first()
        
        if fiscal_year:
            return fiscal_year
        
        # Create default fiscal year for current year
        year = today.year
        fiscal_year = FiscalYear.objects.create(
            name=f"FY {year}",
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
            is_active=True,
            is_closed=False,
        )
        return fiscal_year
    
    def get_accounting_period(self, entry_date: date) -> Optional[AccountingPeriod]:
        """
        Get accounting period for the given date
        獲取指定日期的會計期間
        """
        fiscal_year = self.get_current_fiscal_year()
        if not fiscal_year:
            return None
        
        period = AccountingPeriod.objects.filter(
            fiscal_year=fiscal_year,
            start_date__lte=entry_date,
            end_date__gte=entry_date,
            is_closed=False
        ).first()
        
        if period:
            return period
        
        # Create period for the month
        month = entry_date.month
        from calendar import monthrange
        last_day = monthrange(entry_date.year, month)[1]
        
        period = AccountingPeriod.objects.create(
            fiscal_year=fiscal_year,
            name=entry_date.strftime('%B %Y'),
            period_number=month,
            start_date=date(entry_date.year, month, 1),
            end_date=date(entry_date.year, month, last_day),
            is_closed=False,
        )
        return period
    
    def generate_entry_number(self) -> str:
        """
        Generate unique journal entry number
        生成唯一分錄編號
        """
        today = datetime.now()
        prefix = f"JE-{today.strftime('%Y%m%d')}"
        
        # Get today's count
        count = JournalEntry.objects.filter(
            entry_number__startswith=prefix
        ).count()
        
        return f"{prefix}-{(count + 1):04d}"
    
    @transaction.atomic
    def create_journal_entry_from_receipt(
        self, 
        receipt: Receipt,
        auto_post: bool = False
    ) -> Tuple[Optional[JournalEntry], Optional[str]]:
        """
        Create actual JournalEntry from Receipt
        從收據建立實際的分錄
        
        Args:
            receipt: Receipt instance
            auto_post: Whether to auto-post the entry
            
        Returns:
            Tuple of (JournalEntry, error_message)
        """
        try:
            # Validate receipt
            if not receipt.total_amount or receipt.total_amount <= 0:
                return None, "Receipt total amount is invalid"
            
            # Get accounts
            expense_account = self.get_expense_account(receipt.category)
            payment_account = self.get_payment_account(receipt.payment_method)
            
            if not expense_account:
                return None, f"Could not find/create expense account for category: {receipt.category}"
            if not payment_account:
                return None, f"Could not find/create payment account for method: {receipt.payment_method}"
            
            # Get fiscal period
            entry_date = receipt.receipt_date or timezone.now().date()
            fiscal_year = self.get_current_fiscal_year()
            period = self.get_accounting_period(entry_date)
            
            # Calculate amounts
            total_amount = Decimal(str(receipt.total_amount))
            tax_amount = Decimal(str(receipt.tax_amount or 0))
            net_amount = total_amount - tax_amount
            
            # Create Journal Entry
            entry_number = self.generate_entry_number()
            description = f"費用 - {receipt.vendor_name or 'Unknown'} / Expense - {receipt.vendor_name or 'Unknown'}"
            
            journal_entry = JournalEntry.objects.create(
                entry_number=entry_number,
                date=entry_date,
                description=description,
                reference=receipt.receipt_number or str(receipt.id),
                fiscal_year=fiscal_year,
                period=period,
                status=TransactionStatus.DRAFT.value,
                created_by=self.user or receipt.uploaded_by,
                total_debit=total_amount,
                total_credit=total_amount,
            )
            
            # Create Journal Entry Lines
            
            # Line 1: Debit Expense Account
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=expense_account,
                description=f"{receipt.vendor_name or 'Unknown'} - {receipt.category}",
                debit=net_amount,
                credit=Decimal('0.00'),
            )
            
            # Line 2: Debit Input VAT (if applicable)
            if tax_amount > 0:
                tax_account = self.get_tax_account()
                if tax_account:
                    JournalEntryLine.objects.create(
                        journal_entry=journal_entry,
                        account=tax_account,
                        description=f"VAT on {receipt.vendor_name or 'Unknown'}",
                        debit=tax_amount,
                        credit=Decimal('0.00'),
                    )
            
            # Line 3: Credit Payment Account
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=payment_account,
                description=f"Payment to {receipt.vendor_name or 'Unknown'}",
                debit=Decimal('0.00'),
                credit=total_amount,
            )
            
            # Link receipt to journal entry
            receipt.journal_entry = journal_entry
            receipt.status = ReceiptStatus.JOURNAL_CREATED
            
            # Update journal_entry_data with actual IDs
            receipt.journal_entry_data = {
                'journal_entry_id': str(journal_entry.id),
                'entry_number': journal_entry.entry_number,
                'date': str(journal_entry.date),
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
            }
            receipt.save()
            
            # Auto-post if requested
            if auto_post:
                journal_entry.status = TransactionStatus.POSTED.value
                journal_entry.posted_at = timezone.now()
                journal_entry.save()
                
                receipt.status = ReceiptStatus.POSTED
                receipt.save()
                
                # Update account balances
                self._update_account_balances(journal_entry)
            
            return journal_entry, None
            
        except Exception as e:
            return None, str(e)
    
    def _update_account_balances(self, journal_entry: JournalEntry):
        """
        Update account current balances after posting
        過帳後更新科目餘額
        """
        for line in journal_entry.lines.all():
            account = line.account
            
            # Assets and Expenses increase with debits
            if account.is_debit_positive:
                account.current_balance += line.debit - line.credit
            else:
                # Liabilities, Equity, Revenue increase with credits
                account.current_balance += line.credit - line.debit
            
            account.save()
    
    @transaction.atomic
    def approve_and_create_journal(
        self, 
        receipt: Receipt, 
        user,
        notes: str = '',
        auto_post: bool = False
    ) -> Tuple[Optional[JournalEntry], Optional[str]]:
        """
        Approve receipt and automatically create journal entry
        核准收據並自動建立分錄
        """
        self.user = user
        
        # Create journal entry
        journal_entry, error = self.create_journal_entry_from_receipt(receipt, auto_post)
        
        if error:
            return None, error
        
        # Update receipt status
        receipt.status = ReceiptStatus.APPROVED if not auto_post else ReceiptStatus.POSTED
        receipt.reviewed_by = user
        receipt.reviewed_at = timezone.now()
        receipt.notes = notes
        receipt.save()
        
        return journal_entry, None
    
    @transaction.atomic
    def batch_create_journal_entries(
        self, 
        receipts: List[Receipt],
        auto_post: bool = False
    ) -> Dict[str, Any]:
        """
        Create journal entries for multiple receipts
        批量建立分錄
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(receipts),
        }
        
        for receipt in receipts:
            journal_entry, error = self.create_journal_entry_from_receipt(receipt, auto_post)
            
            if journal_entry:
                results['success'].append({
                    'receipt_id': str(receipt.id),
                    'journal_entry_id': str(journal_entry.id),
                    'entry_number': journal_entry.entry_number,
                })
            else:
                results['failed'].append({
                    'receipt_id': str(receipt.id),
                    'error': error,
                })
        
        results['success_count'] = len(results['success'])
        results['failed_count'] = len(results['failed'])
        
        return results
    
    @transaction.atomic
    def post_journal_entry(self, journal_entry: JournalEntry, user) -> Tuple[bool, Optional[str]]:
        """
        Post a journal entry
        過帳分錄
        """
        try:
            # Validate entry is balanced
            if not journal_entry.is_balanced:
                return False, "Journal entry is not balanced"
            
            # Check if already posted
            if journal_entry.status == TransactionStatus.POSTED.value:
                return False, "Journal entry is already posted"
            
            # Update status
            journal_entry.status = TransactionStatus.POSTED.value
            journal_entry.approved_by = user
            journal_entry.approved_at = timezone.now()
            journal_entry.posted_at = timezone.now()
            journal_entry.save()
            
            # Update account balances
            self._update_account_balances(journal_entry)
            
            # Update linked receipt if exists
            linked_receipts = Receipt.objects.filter(journal_entry=journal_entry)
            linked_receipts.update(status=ReceiptStatus.POSTED)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @transaction.atomic
    def void_journal_entry(self, journal_entry: JournalEntry, user, reason: str = '') -> Tuple[bool, Optional[str]]:
        """
        Void a journal entry (reverse balances if posted)
        作廢分錄
        """
        try:
            # If posted, reverse the account balances
            if journal_entry.status == TransactionStatus.POSTED.value:
                for line in journal_entry.lines.all():
                    account = line.account
                    
                    # Reverse the balance update
                    if account.is_debit_positive:
                        account.current_balance -= line.debit - line.credit
                    else:
                        account.current_balance -= line.credit - line.debit
                    
                    account.save()
            
            # Update status
            journal_entry.status = TransactionStatus.VOIDED.value
            journal_entry.save()
            
            # Update linked receipt
            linked_receipts = Receipt.objects.filter(journal_entry=journal_entry)
            linked_receipts.update(status=ReceiptStatus.CATEGORIZED)
            
            return True, None
            
        except Exception as e:
            return False, str(e)


# Convenience functions
def create_journal_from_receipt(receipt: Receipt, user=None, auto_post: bool = False) -> Tuple[Optional[JournalEntry], Optional[str]]:
    """
    Convenience function to create journal entry from receipt
    """
    service = JournalEntryService(user=user or receipt.uploaded_by)
    return service.create_journal_entry_from_receipt(receipt, auto_post)


def approve_receipt_with_journal(receipt: Receipt, user, notes: str = '', auto_post: bool = False) -> Tuple[Optional[JournalEntry], Optional[str]]:
    """
    Convenience function to approve receipt and create journal entry
    """
    service = JournalEntryService(user=user)
    return service.approve_and_create_journal(receipt, user, notes, auto_post)


def batch_create_journals(receipts: List[Receipt], user=None, auto_post: bool = False) -> Dict[str, Any]:
    """
    Convenience function for batch journal creation
    """
    service = JournalEntryService(user=user)
    return service.batch_create_journal_entries(receipts, auto_post)
