#!/usr/bin/env python
"""
Sample Data Generator for Analyst Assistant
生成範例數據以供分析助手使用

Run with: python manage.py shell < scripts/generate_sample_data.py
Or: python scripts/generate_sample_data.py (if Django settings are configured)
"""

import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from accounting.models import (
    Currency, Contact, Invoice, InvoiceLine, Payment, 
    Account, AccountType, AccountSubType, FiscalYear, TaxRate
)

User = get_user_model()

# Sample data configurations
COMPANIES = [
    {"name": "台北科技有限公司", "contact": "王大明", "city": "台北", "country": "Taiwan"},
    {"name": "新竹電子股份有限公司", "contact": "李小華", "city": "新竹", "country": "Taiwan"},
    {"name": "高雄製造公司", "contact": "張志明", "city": "高雄", "country": "Taiwan"},
    {"name": "台中貿易有限公司", "contact": "陳美玲", "city": "台中", "country": "Taiwan"},
    {"name": "桃園物流公司", "contact": "林志偉", "city": "桃園", "country": "Taiwan"},
    {"name": "Tokyo Electronics Co.", "contact": "Tanaka Yuki", "city": "Tokyo", "country": "Japan"},
    {"name": "Singapore Trading Pte", "contact": "Tan Wei Lin", "city": "Singapore", "country": "Singapore"},
    {"name": "Hong Kong Import Ltd", "contact": "Wong Chi Ming", "city": "Hong Kong", "country": "Hong Kong"},
    {"name": "Shanghai Tech Corp", "contact": "Zhang Wei", "city": "Shanghai", "country": "China"},
    {"name": "Osaka Manufacturing", "contact": "Suzuki Ken", "city": "Osaka", "country": "Japan"},
]

PRODUCTS = [
    {"name": "企業軟體授權 - 基礎版", "price": 15000},
    {"name": "企業軟體授權 - 專業版", "price": 35000},
    {"name": "企業軟體授權 - 企業版", "price": 80000},
    {"name": "雲端服務 - 月租方案", "price": 5000},
    {"name": "雲端服務 - 年租方案", "price": 50000},
    {"name": "技術支援服務 - 基礎", "price": 8000},
    {"name": "技術支援服務 - 進階", "price": 20000},
    {"name": "客製化開發服務", "price": 100000},
    {"name": "系統整合服務", "price": 150000},
    {"name": "教育訓練課程", "price": 12000},
    {"name": "硬體設備 - 伺服器", "price": 250000},
    {"name": "硬體設備 - 工作站", "price": 80000},
    {"name": "網路設備 - 路由器", "price": 35000},
    {"name": "資安服務 - 年度方案", "price": 60000},
    {"name": "數據分析服務", "price": 45000},
]

INVOICE_STATUSES = ['PAID', 'PAID', 'PAID', 'SENT', 'PARTIAL', 'DRAFT']  # Weighted towards PAID


def create_base_currency():
    """Create or get base currency"""
    currency, _ = Currency.objects.get_or_create(
        code='TWD',
        defaults={
            'name': 'New Taiwan Dollar',
            'symbol': 'NT$',
            'exchange_rate': Decimal('1.000000'),
            'is_base': True
        }
    )
    return currency


def create_fiscal_year():
    """Create fiscal year for 2025"""
    fy, _ = FiscalYear.objects.get_or_create(
        name='FY 2025',
        defaults={
            'start_date': datetime(2025, 1, 1).date(),
            'end_date': datetime(2025, 12, 31).date(),
            'is_active': True,
            'is_closed': False
        }
    )
    return fy


def create_tax_rate():
    """Create default tax rate"""
    tax, _ = TaxRate.objects.get_or_create(
        name='營業稅 5%',
        defaults={
            'rate': Decimal('5.00'),
            'description': '標準營業稅率',
            'is_active': True
        }
    )
    return tax


def create_accounts():
    """Create basic chart of accounts"""
    accounts = {}
    
    # Sales account
    accounts['sales'], _ = Account.objects.get_or_create(
        code='4100',
        defaults={
            'name': '銷貨收入',
            'account_type': AccountType.REVENUE.value,
            'account_subtype': AccountSubType.SALES.value,
            'is_active': True
        }
    )
    
    # Service revenue
    accounts['service'], _ = Account.objects.get_or_create(
        code='4200',
        defaults={
            'name': '服務收入',
            'account_type': AccountType.REVENUE.value,
            'account_subtype': AccountSubType.SERVICE.value,
            'is_active': True
        }
    )
    
    # Accounts receivable
    accounts['ar'], _ = Account.objects.get_or_create(
        code='1200',
        defaults={
            'name': '應收帳款',
            'account_type': AccountType.ASSET.value,
            'account_subtype': AccountSubType.ACCOUNTS_RECEIVABLE.value,
            'is_active': True
        }
    )
    
    # Bank account
    accounts['bank'], _ = Account.objects.get_or_create(
        code='1100',
        defaults={
            'name': '銀行存款',
            'account_type': AccountType.ASSET.value,
            'account_subtype': AccountSubType.BANK.value,
            'is_active': True
        }
    )
    
    return accounts


def create_customers(currency):
    """Create sample customers"""
    customers = []
    for company in COMPANIES:
        customer, _ = Contact.objects.get_or_create(
            company_name=company['name'],
            defaults={
                'contact_type': 'CUSTOMER',
                'contact_name': company['contact'],
                'email': f"{company['contact'].lower().replace(' ', '.')}@example.com",
                'city': company['city'],
                'country': company['country'],
                'currency': currency,
                'payment_terms': random.choice([15, 30, 45, 60]),
                'credit_limit': Decimal(str(random.randint(100000, 1000000))),
                'is_active': True
            }
        )
        customers.append(customer)
    return customers


def create_invoices(customers, currency, accounts, tax_rate, user):
    """Create sample invoices for the past 12 months"""
    invoices_created = 0
    
    # Generate invoices for each month from Jan 2025 to Dec 2025
    for month in range(1, 13):
        # Create 5-15 invoices per month
        num_invoices = random.randint(5, 15)
        
        for i in range(num_invoices):
            customer = random.choice(customers)
            
            # Random date within the month
            day = random.randint(1, 28)
            issue_date = datetime(2025, month, day).date()
            due_date = issue_date + timedelta(days=customer.payment_terms)
            
            # Generate invoice number
            invoice_number = f"INV-2025{month:02d}-{invoices_created + 1:04d}"
            
            # Check if invoice already exists
            if Invoice.objects.filter(invoice_number=invoice_number).exists():
                continue
            
            # Determine status based on date
            if issue_date < datetime.now().date() - timedelta(days=30):
                status = random.choice(['PAID', 'PAID', 'PAID', 'PARTIAL'])
            else:
                status = random.choice(INVOICE_STATUSES)
            
            # Create invoice
            invoice = Invoice.objects.create(
                invoice_type='SALES',
                invoice_number=invoice_number,
                contact=customer,
                issue_date=issue_date,
                due_date=due_date,
                status=status,
                currency=currency,
                exchange_rate=Decimal('1.000000'),
                created_by=user
            )
            
            # Add 1-5 line items
            num_lines = random.randint(1, 5)
            subtotal = Decimal('0')
            
            for _ in range(num_lines):
                product = random.choice(PRODUCTS)
                quantity = Decimal(str(random.randint(1, 10)))
                unit_price = Decimal(str(product['price']))
                
                # Random discount
                discount_percent = Decimal(str(random.choice([0, 0, 0, 5, 10, 15])))
                line_subtotal = quantity * unit_price
                discount_amount = line_subtotal * discount_percent / 100
                tax_amount = (line_subtotal - discount_amount) * tax_rate.rate / 100
                line_total = line_subtotal - discount_amount + tax_amount
                
                InvoiceLine.objects.create(
                    invoice=invoice,
                    description=product['name'],
                    account=accounts['sales'],
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    discount_percent=discount_percent,
                    discount_amount=discount_amount,
                    line_total=line_total
                )
                
                subtotal += line_subtotal
            
            # Update invoice totals
            total_tax = subtotal * tax_rate.rate / 100
            total_discount = Invoice.objects.get(id=invoice.id).lines.aggregate(
                total=django.db.models.Sum('discount_amount')
            )['total'] or Decimal('0')
            
            invoice.subtotal = subtotal
            invoice.tax_amount = total_tax
            invoice.discount_amount = total_discount
            invoice.total = subtotal - total_discount + total_tax
            
            if status == 'PAID':
                invoice.amount_paid = invoice.total
                invoice.amount_due = Decimal('0')
            elif status == 'PARTIAL':
                partial = invoice.total * Decimal(str(random.uniform(0.3, 0.8)))
                invoice.amount_paid = partial.quantize(Decimal('0.01'))
                invoice.amount_due = invoice.total - invoice.amount_paid
            else:
                invoice.amount_paid = Decimal('0')
                invoice.amount_due = invoice.total
            
            invoice.save()
            invoices_created += 1
    
    return invoices_created


def main():
    print("=" * 60)
    print("範例數據生成器 / Sample Data Generator")
    print("=" * 60)
    
    # Get or create admin user
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    if not user:
        print("❌ 錯誤：找不到用戶。請先創建用戶。")
        print("❌ Error: No user found. Please create a user first.")
        return
    
    print(f"✓ 使用用戶 / Using user: {user.email}")
    
    # Create base data
    print("\n創建基礎數據 / Creating base data...")
    currency = create_base_currency()
    print(f"  ✓ 貨幣 / Currency: {currency.code}")
    
    fiscal_year = create_fiscal_year()
    print(f"  ✓ 財年 / Fiscal Year: {fiscal_year.name}")
    
    tax_rate = create_tax_rate()
    print(f"  ✓ 稅率 / Tax Rate: {tax_rate.name}")
    
    accounts = create_accounts()
    print(f"  ✓ 會計科目 / Accounts: {len(accounts)} created")
    
    # Create customers
    print("\n創建客戶 / Creating customers...")
    customers = create_customers(currency)
    print(f"  ✓ 客戶 / Customers: {len(customers)}")
    
    # Create invoices
    print("\n創建發票 / Creating invoices...")
    num_invoices = create_invoices(customers, currency, accounts, tax_rate, user)
    print(f"  ✓ 發票 / Invoices: {num_invoices}")
    
    # Summary
    print("\n" + "=" * 60)
    print("數據生成完成！/ Data generation complete!")
    print("=" * 60)
    
    # Show statistics
    total_invoices = Invoice.objects.filter(invoice_type='SALES').count()
    total_revenue = Invoice.objects.filter(
        invoice_type='SALES', 
        status='PAID'
    ).aggregate(total=django.db.models.Sum('total'))['total'] or 0
    
    print(f"\n統計 / Statistics:")
    print(f"  • 總發票數 / Total Invoices: {total_invoices}")
    print(f"  • 總營收 / Total Revenue: NT$ {total_revenue:,.2f}")
    print(f"  • 客戶數 / Customers: {Contact.objects.filter(contact_type='CUSTOMER').count()}")
    
    print("\n現在可以使用 Analyst Assistant 分析數據了！")
    print("You can now use the Analyst Assistant to analyze the data!")


if __name__ == '__main__':
    import django.db.models
    main()
