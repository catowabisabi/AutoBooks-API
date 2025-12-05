"""
Initialize accounting base data (Chart of Accounts, Fiscal Year, Currency, Tax Rates)
Usage: python manage.py init_accounting
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date
from accounting.models import (
    FiscalYear, AccountingPeriod, Currency, TaxRate, Account,
    AccountType, AccountSubType
)


class Command(BaseCommand):
    help = 'Initialize accounting module with base data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-initialization even if data exists',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write('Initializing accounting data...\n')
        
        # 1. Create currencies
        self._create_currencies(force)
        
        # 2. Create tax rates
        self._create_tax_rates(force)
        
        # 3. Create fiscal year and periods
        self._create_fiscal_year(force)
        
        # 4. Create chart of accounts
        self._create_chart_of_accounts(force)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Accounting data initialized successfully!'))
    
    def _create_currencies(self, force):
        self.stdout.write('Creating currencies...')
        
        currencies = [
            {'code': 'HKD', 'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'exchange_rate': Decimal('1.0000'), 'is_base': True},
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'exchange_rate': Decimal('0.1282')},
            {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥', 'exchange_rate': Decimal('0.9231')},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'exchange_rate': Decimal('0.1179')},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£', 'exchange_rate': Decimal('0.1008')},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥', 'exchange_rate': Decimal('19.2308')},
        ]
        
        for curr_data in currencies:
            Currency.objects.update_or_create(
                code=curr_data['code'],
                defaults=curr_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'  Created {len(currencies)} currencies'))
    
    def _create_tax_rates(self, force):
        self.stdout.write('Creating tax rates...')
        
        tax_rates = [
            {'name': 'No Tax', 'rate': Decimal('0.00'), 'description': 'Tax exempt'},
            {'name': 'Standard Rate', 'rate': Decimal('16.50'), 'description': 'HK Standard Profits Tax Rate'},
            {'name': 'SME Rate', 'rate': Decimal('8.25'), 'description': 'HK SME Profits Tax Rate (first HK$2M)'},
            {'name': 'Sales Tax 5%', 'rate': Decimal('5.00'), 'description': 'General sales tax 5%'},
            {'name': 'Sales Tax 10%', 'rate': Decimal('10.00'), 'description': 'General sales tax 10%'},
        ]
        
        for tax_data in tax_rates:
            TaxRate.objects.update_or_create(
                name=tax_data['name'],
                defaults=tax_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'  Created {len(tax_rates)} tax rates'))
    
    def _create_fiscal_year(self, force):
        self.stdout.write('Creating fiscal year...')
        
        today = timezone.now().date()
        year = today.year
        
        # Create fiscal year (April 1 to March 31 for HK)
        fiscal_year, created = FiscalYear.objects.update_or_create(
            name=f'FY{year}-{year+1}',
            defaults={
                'start_date': date(year, 4, 1),
                'end_date': date(year + 1, 3, 31),
                'is_closed': False,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created fiscal year: {fiscal_year.name}'))
        else:
            self.stdout.write(f'  Fiscal year already exists: {fiscal_year.name}')
        
        # Create accounting periods (monthly)
        self.stdout.write('Creating accounting periods...')
        months = [
            (4, year), (5, year), (6, year), (7, year), (8, year), (9, year),
            (10, year), (11, year), (12, year), (1, year+1), (2, year+1), (3, year+1)
        ]
        
        for i, (month, y) in enumerate(months, 1):
            from calendar import monthrange
            _, last_day = monthrange(y, month)
            
            period_name = f'{y}-{month:02d}'
            AccountingPeriod.objects.update_or_create(
                fiscal_year=fiscal_year,
                period_number=i,
                defaults={
                    'name': period_name,
                    'start_date': date(y, month, 1),
                    'end_date': date(y, month, last_day),
                    'is_closed': False,
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'  Created 12 accounting periods'))
    
    def _create_chart_of_accounts(self, force):
        self.stdout.write('Creating chart of accounts...')
        
        # Get base currency
        base_currency = Currency.objects.filter(is_base=True).first()
        
        # Define chart of accounts structure
        # Fields: code, name, account_type, account_subtype, parent_code (optional)
        accounts = [
            # ASSETS (1000-1999)
            {'code': '1000', 'name': 'Assets', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.OTHER_ASSET.value},
            {'code': '1100', 'name': 'Current Assets', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.OTHER_ASSET.value, 'parent_code': '1000'},
            {'code': '1110', 'name': 'Cash on Hand', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.CASH.value, 'parent_code': '1100'},
            {'code': '1120', 'name': 'Bank Account - HKD', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.BANK.value, 'parent_code': '1100'},
            {'code': '1121', 'name': 'Bank Account - USD', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.BANK.value, 'parent_code': '1100'},
            {'code': '1130', 'name': 'Petty Cash', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.CASH.value, 'parent_code': '1100'},
            {'code': '1200', 'name': 'Accounts Receivable', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.ACCOUNTS_RECEIVABLE.value, 'parent_code': '1100'},
            {'code': '1300', 'name': 'Inventory', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.INVENTORY.value, 'parent_code': '1100'},
            {'code': '1400', 'name': 'Prepaid Expenses', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.OTHER_ASSET.value, 'parent_code': '1100'},
            
            {'code': '1500', 'name': 'Fixed Assets', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.FIXED_ASSET.value, 'parent_code': '1000'},
            {'code': '1510', 'name': 'Office Equipment', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.FIXED_ASSET.value, 'parent_code': '1500'},
            {'code': '1520', 'name': 'Computer Equipment', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.FIXED_ASSET.value, 'parent_code': '1500'},
            {'code': '1530', 'name': 'Furniture & Fixtures', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.FIXED_ASSET.value, 'parent_code': '1500'},
            {'code': '1590', 'name': 'Accumulated Depreciation', 'account_type': AccountType.ASSET.value, 'account_subtype': AccountSubType.FIXED_ASSET.value, 'parent_code': '1500'},
            
            # LIABILITIES (2000-2999)
            {'code': '2000', 'name': 'Liabilities', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.OTHER_LIABILITY.value},
            {'code': '2100', 'name': 'Current Liabilities', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.OTHER_LIABILITY.value, 'parent_code': '2000'},
            {'code': '2110', 'name': 'Accounts Payable', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.ACCOUNTS_PAYABLE.value, 'parent_code': '2100'},
            {'code': '2120', 'name': 'Credit Card Payable', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.CREDIT_CARD.value, 'parent_code': '2100'},
            {'code': '2130', 'name': 'Accrued Expenses', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.OTHER_LIABILITY.value, 'parent_code': '2100'},
            {'code': '2140', 'name': 'Salaries Payable', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.OTHER_LIABILITY.value, 'parent_code': '2100'},
            {'code': '2150', 'name': 'Tax Payable', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.TAX_PAYABLE.value, 'parent_code': '2100'},
            {'code': '2160', 'name': 'Unearned Revenue', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.OTHER_LIABILITY.value, 'parent_code': '2100'},
            
            {'code': '2500', 'name': 'Long-term Liabilities', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.LOAN.value, 'parent_code': '2000'},
            {'code': '2510', 'name': 'Bank Loan', 'account_type': AccountType.LIABILITY.value, 'account_subtype': AccountSubType.LOAN.value, 'parent_code': '2500'},
            
            # EQUITY (3000-3999)
            {'code': '3000', 'name': 'Equity', 'account_type': AccountType.EQUITY.value, 'account_subtype': AccountSubType.SHARE_CAPITAL.value},
            {'code': '3100', 'name': 'Share Capital', 'account_type': AccountType.EQUITY.value, 'account_subtype': AccountSubType.SHARE_CAPITAL.value, 'parent_code': '3000'},
            {'code': '3200', 'name': 'Retained Earnings', 'account_type': AccountType.EQUITY.value, 'account_subtype': AccountSubType.RETAINED_EARNINGS.value, 'parent_code': '3000'},
            {'code': '3300', 'name': 'Owner\'s Drawings', 'account_type': AccountType.EQUITY.value, 'account_subtype': AccountSubType.SHARE_CAPITAL.value, 'parent_code': '3000'},
            
            # REVENUE (4000-4999)
            {'code': '4000', 'name': 'Revenue', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.SALES.value},
            {'code': '4100', 'name': 'Sales Revenue', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.SALES.value, 'parent_code': '4000'},
            {'code': '4110', 'name': 'Product Sales', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.SALES.value, 'parent_code': '4100'},
            {'code': '4120', 'name': 'Service Revenue', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.SERVICE.value, 'parent_code': '4100'},
            {'code': '4200', 'name': 'Other Income', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.OTHER_INCOME.value, 'parent_code': '4000'},
            {'code': '4210', 'name': 'Interest Income', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.OTHER_INCOME.value, 'parent_code': '4200'},
            {'code': '4220', 'name': 'Foreign Exchange Gain', 'account_type': AccountType.REVENUE.value, 'account_subtype': AccountSubType.OTHER_INCOME.value, 'parent_code': '4200'},
            
            # EXPENSES (5000-5999)
            {'code': '5000', 'name': 'Expenses', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value},
            {'code': '5100', 'name': 'Cost of Goods Sold', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.COST_OF_GOODS.value, 'parent_code': '5000'},
            {'code': '5200', 'name': 'Operating Expenses', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5000'},
            {'code': '5210', 'name': 'Salaries & Wages', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.PAYROLL.value, 'parent_code': '5200'},
            {'code': '5220', 'name': 'Rent Expense', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.RENT.value, 'parent_code': '5200'},
            {'code': '5230', 'name': 'Utilities', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.UTILITIES.value, 'parent_code': '5200'},
            {'code': '5240', 'name': 'Office Supplies', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5200'},
            {'code': '5250', 'name': 'Marketing & Advertising', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5200'},
            {'code': '5260', 'name': 'Professional Fees', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5200'},
            {'code': '5270', 'name': 'Insurance', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5200'},
            {'code': '5280', 'name': 'Depreciation Expense', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OPERATING.value, 'parent_code': '5200'},
            {'code': '5290', 'name': 'Miscellaneous Expense', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OTHER_EXPENSE.value, 'parent_code': '5200'},
            {'code': '5300', 'name': 'Other Expenses', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OTHER_EXPENSE.value, 'parent_code': '5000'},
            {'code': '5310', 'name': 'Interest Expense', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OTHER_EXPENSE.value, 'parent_code': '5300'},
            {'code': '5320', 'name': 'Bank Charges', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OTHER_EXPENSE.value, 'parent_code': '5300'},
            {'code': '5330', 'name': 'Foreign Exchange Loss', 'account_type': AccountType.EXPENSE.value, 'account_subtype': AccountSubType.OTHER_EXPENSE.value, 'parent_code': '5300'},
        ]
        
        # Create accounts and store parent relationships
        account_map = {}
        parent_map = {}  # Store parent_code for later
        
        for acc_data in accounts:
            parent_code = acc_data.pop('parent_code', None)
            if parent_code:
                parent_map[acc_data['code']] = parent_code
            
            acc_data['currency'] = base_currency
            
            account, created = Account.objects.update_or_create(
                code=acc_data['code'],
                defaults={
                    'name': acc_data['name'],
                    'account_type': acc_data['account_type'],
                    'account_subtype': acc_data['account_subtype'],
                    'currency': acc_data['currency'],
                }
            )
            account_map[acc_data['code']] = account
        
        # Set parent relationships
        for child_code, parent_code in parent_map.items():
            if child_code in account_map and parent_code in account_map:
                child = account_map[child_code]
                child.parent = account_map[parent_code]
                child.save()
        
        self.stdout.write(self.style.SUCCESS(f'  Created {len(accounts)} accounts'))
