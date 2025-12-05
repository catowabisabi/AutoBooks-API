"""
Business Data Seeder
====================
Django management command to seed business data for development/testing.

Usage:
    python manage.py seed_business_data
    python manage.py seed_business_data --clear  # Clear existing data first
    python manage.py seed_business_data --count 50  # Generate 50 records per model
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from business.models import (
    Company,
    AuditProject,
    TaxReturnCase,
    BillableHour,
    Revenue,
    BMIIPOPRRecord,
    AuditStatus,
    TaxReturnStatus,
    EmployeeRole,
    RevenueStatus,
    BMIStage,
    BMIStatus,
)
from users.models import User


class Command(BaseCommand):
    help = 'Seed business data with fake records for development/testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing business data before seeding',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of records to generate per model (default: 30)',
        )

    def handle(self, *args, **options):
        clear = options['clear']
        count = options['count']

        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing business data...'))
            self._clear_data()

        self.stdout.write(self.style.NOTICE(f'Seeding business data with {count} records per model...'))

        with transaction.atomic():
            # Create test users first
            users = self._ensure_users()
            
            # Create companies
            companies = self._create_companies(count)
            
            # Create business records
            self._create_audits(companies, users, count)
            self._create_tax_returns(companies, users, count)
            self._create_billable_hours(companies, users, count)
            self._create_revenues(companies, count)
            self._create_bmi_projects(companies, users, min(count // 3, 10))

        self.stdout.write(self.style.SUCCESS('✅ Business data seeding completed!'))
        self._print_summary()

    def _clear_data(self):
        """Clear existing business data"""
        BMIIPOPRRecord.objects.all().delete()
        Revenue.objects.all().delete()
        BillableHour.objects.all().delete()
        TaxReturnCase.objects.all().delete()
        AuditProject.objects.all().delete()
        Company.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared all business data'))

    def _ensure_users(self):
        """Ensure test users exist"""
        user_data = [
            {'email': 'manager@wisematic.com', 'full_name': '張經理', 'role': 'manager'},
            {'email': 'accountant1@wisematic.com', 'full_name': '李會計', 'role': 'accountant'},
            {'email': 'accountant2@wisematic.com', 'full_name': '王會計', 'role': 'accountant'},
            {'email': 'clerk1@wisematic.com', 'full_name': '陳文員', 'role': 'clerk'},
            {'email': 'director@wisematic.com', 'full_name': '劉總監', 'role': 'director'},
            {'email': 'partner@wisematic.com', 'full_name': '黃合夥人', 'role': 'partner'},
        ]
        
        users = []
        for data in user_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'full_name': data['full_name'],
                    'is_active': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(f'  Created user: {user.email}')
            users.append(user)
        
        return users

    def _create_companies(self, count):
        """Create sample companies"""
        company_names = [
            ('創新科技有限公司', 'Technology'),
            ('永豐貿易有限公司', 'Trading'),
            ('宏達建築工程有限公司', 'Construction'),
            ('環球物流有限公司', 'Logistics'),
            ('優質餐飲集團有限公司', 'Food & Beverage'),
            ('智慧金融服務有限公司', 'Financial Services'),
            ('綠色能源科技有限公司', 'Energy'),
            ('精密製造有限公司', 'Manufacturing'),
            ('數碼媒體有限公司', 'Media'),
            ('醫療保健有限公司', 'Healthcare'),
            ('環球投資有限公司', 'Investment'),
            ('頂尖諮詢有限公司', 'Consulting'),
            ('國際航運有限公司', 'Shipping'),
            ('優質零售有限公司', 'Retail'),
            ('高端地產有限公司', 'Real Estate'),
            ('尊尚酒店管理有限公司', 'Hospitality'),
            ('先進電子有限公司', 'Electronics'),
            ('專業法律服務有限公司', 'Legal Services'),
            ('創意設計有限公司', 'Design'),
            ('教育培訓有限公司', 'Education'),
            ('農業發展有限公司', 'Agriculture'),
            ('環保科技有限公司', 'Environmental'),
            ('軟件開發有限公司', 'Software'),
            ('網絡安全有限公司', 'Cybersecurity'),
            ('電訊服務有限公司', 'Telecommunications'),
            ('保險服務有限公司', 'Insurance'),
            ('生物科技有限公司', 'Biotechnology'),
            ('汽車零件有限公司', 'Automotive'),
            ('紡織服裝有限公司', 'Textiles'),
            ('化工材料有限公司', 'Chemicals'),
        ]
        
        companies = []
        for i, (name, industry) in enumerate(company_names[:count]):
            company, created = Company.objects.get_or_create(
                name=name,
                defaults={
                    'registration_number': f'CR-{2024000 + i}',
                    'tax_id': f'HK{random.randint(10000000, 99999999)}',
                    'address': f'香港九龍{random.choice(["尖沙咀", "旺角", "油麻地", "深水埗"])}{random.randint(1, 999)}號商業大廈{random.randint(1, 30)}樓',
                    'industry': industry,
                    'contact_person': f'{random.choice(["張", "李", "王", "陳", "黃"])}{random.choice(["先生", "小姐", "經理", "總監"])}',
                    'contact_email': f'contact{i}@{name.replace("有限公司", "").replace(" ", "").lower()}.com',
                    'contact_phone': f'+852 {random.randint(2000, 3999)} {random.randint(1000, 9999)}',
                    'notes': f'{industry} 行業客戶',
                }
            )
            if created:
                self.stdout.write(f'  Created company: {company.name}')
            companies.append(company)
        
        return companies

    def _create_audits(self, companies, users, count):
        """Create audit projects"""
        audit_types = ['FINANCIAL', 'TAX', 'INTERNAL', 'COMPLIANCE']
        
        for i in range(count):
            company = random.choice(companies)
            status = random.choice([s.value for s in AuditStatus])
            progress = 100 if status == 'COMPLETED' else random.randint(0, 95)
            
            start_date = date.today() - timedelta(days=random.randint(30, 365))
            deadline = start_date + timedelta(days=random.randint(60, 180))
            
            AuditProject.objects.create(
                company=company,
                fiscal_year=f'{random.choice([2023, 2024])}',
                audit_type=random.choice(audit_types),
                progress=progress,
                status=status,
                start_date=start_date,
                deadline=deadline,
                completion_date=deadline - timedelta(days=random.randint(1, 10)) if status == 'COMPLETED' else None,
                assigned_to=random.choice(users),
                budget_hours=Decimal(random.randint(50, 500)),
                actual_hours=Decimal(random.randint(20, 400)),
                notes=f'{company.name} {random.choice([2023, 2024])} 年度審計項目',
            )
        
        self.stdout.write(f'  Created {count} audit projects')

    def _create_tax_returns(self, companies, users, count):
        """Create tax return cases"""
        tax_types = ['PROFITS_TAX', 'SALARIES_TAX', 'PROPERTY_TAX', 'STAMP_DUTY']
        
        for i in range(count):
            company = random.choice(companies)
            status = random.choice([s.value for s in TaxReturnStatus])
            progress = 100 if status in ['ACCEPTED', 'SUBMITTED'] else random.randint(0, 90)
            
            deadline = date.today() + timedelta(days=random.randint(-60, 120))
            
            TaxReturnCase.objects.create(
                company=company,
                tax_year=f'{random.choice([2022, 2023, 2024])}',
                tax_type=random.choice(tax_types),
                progress=progress,
                status=status,
                deadline=deadline,
                submitted_date=deadline - timedelta(days=random.randint(1, 30)) if status in ['SUBMITTED', 'ACCEPTED'] else None,
                handler=random.choice(users),
                tax_amount=Decimal(random.randint(10000, 5000000)),
                documents_received=random.choice([True, False]),
                notes=f'{company.name} {random.choice([2022, 2023, 2024])} 稅務申報',
            )
        
        self.stdout.write(f'  Created {count} tax return cases')

    def _create_billable_hours(self, companies, users, count):
        """Create billable hour records"""
        descriptions = [
            '審計現場工作',
            '稅務諮詢',
            '財務報表審閱',
            '內部控制評估',
            '合規檢查',
            '客戶會議',
            '報告撰寫',
            '數據分析',
            '文件審核',
            '系統測試',
        ]
        
        for i in range(count):
            employee = random.choice(users)
            role = random.choice([r.value for r in EmployeeRole])
            base_rate = Decimal(random.choice([100, 150, 200, 250, 300]))
            multiplier = EmployeeRole.get_multiplier(role)
            
            BillableHour.objects.create(
                employee=employee,
                company=random.choice(companies),
                project_reference=f'PRJ-{random.randint(1000, 9999)}',
                role=role,
                base_hourly_rate=base_rate,
                hourly_rate_multiplier=multiplier,
                date=date.today() - timedelta(days=random.randint(0, 90)),
                actual_hours=Decimal(random.choice([1, 2, 3, 4, 5, 6, 7, 8])),
                description=random.choice(descriptions),
                is_billable=random.choice([True, True, True, False]),  # 75% billable
                is_invoiced=random.choice([True, False]),
            )
        
        self.stdout.write(f'  Created {count} billable hour records')

    def _create_revenues(self, companies, count):
        """Create revenue records"""
        descriptions = [
            '年度審計服務費',
            '稅務諮詢服務費',
            '財務顧問費',
            '合規審查費',
            '特別項目費',
            '月度記帳服務',
            '公司秘書服務',
            'IPO 諮詢費',
        ]
        
        for i in range(count):
            company = random.choice(companies)
            status = random.choice([s.value for s in RevenueStatus])
            total_amount = Decimal(random.randint(10000, 500000))
            
            if status == 'RECEIVED':
                received = total_amount
            elif status == 'PARTIAL':
                received = total_amount * Decimal(random.uniform(0.3, 0.8))
            else:
                received = Decimal('0.00')
            
            invoice_date = date.today() - timedelta(days=random.randint(0, 180))
            due_date = invoice_date + timedelta(days=30)
            
            Revenue.objects.create(
                company=company,
                invoice_number=f'INV-{2024}-{random.randint(1000, 9999)}',
                description=random.choice(descriptions),
                total_amount=total_amount,
                received_amount=received,
                status=status,
                invoice_date=invoice_date,
                due_date=due_date,
                received_date=due_date - timedelta(days=random.randint(1, 15)) if status == 'RECEIVED' else None,
                contact_name=company.contact_person,
                contact_email=company.contact_email,
                contact_phone=company.contact_phone,
                notes=f'{company.name} 服務收費',
            )
        
        self.stdout.write(f'  Created {count} revenue records')

    def _create_bmi_projects(self, companies, users, count):
        """Create BMI IPO/PR records"""
        project_types = ['IPO', 'PR', 'RIGHTS_ISSUE', 'PLACEMENT']
        
        for i in range(count):
            company = random.choice(companies)
            stage = random.choice([s.value for s in BMIStage])
            status = random.choice([s.value for s in BMIStatus])
            
            progress = 100 if stage == 'POST_IPO' else random.randint(10, 90)
            
            start_date = date.today() - timedelta(days=random.randint(30, 365))
            target_date = start_date + timedelta(days=random.randint(180, 365))
            
            BMIIPOPRRecord.objects.create(
                project_name=f'{company.name} {random.choice(project_types)} 項目',
                company=company,
                stage=stage,
                status=status,
                project_type=random.choice(project_types),
                estimated_value=Decimal(random.randint(10000000, 1000000000)),
                total_cost=Decimal(random.randint(500000, 10000000)),
                start_date=start_date,
                target_completion_date=target_date,
                actual_completion_date=target_date if stage == 'POST_IPO' else None,
                progress=progress,
                lead_manager=random.choice(users),
                notes=f'{company.name} BMI 專案備註',
            )
        
        self.stdout.write(f'  Created {count} BMI IPO/PR projects')

    def _print_summary(self):
        """Print summary of seeded data"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📊 Data Summary:'))
        self.stdout.write(f'   Companies: {Company.objects.count()}')
        self.stdout.write(f'   Audit Projects: {AuditProject.objects.count()}')
        self.stdout.write(f'   Tax Returns: {TaxReturnCase.objects.count()}')
        self.stdout.write(f'   Billable Hours: {BillableHour.objects.count()}')
        self.stdout.write(f'   Revenue Records: {Revenue.objects.count()}')
        self.stdout.write(f'   BMI Projects: {BMIIPOPRRecord.objects.count()}')
        self.stdout.write('')
