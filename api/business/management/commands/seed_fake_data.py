"""
Seed Fake Data for ERP System
=============================
Generates comprehensive test data for all modules:
- Business: Companies, Audits, Tax Returns, Billable Hours, Revenue, BMI IPO/PR
- HRMS: Employees, Departments, Designations, Leaves, Payroll
- Analytics: Sales Analytics, KPIs
"""

import random
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

# Import models
from users.models import User
from hrms.models import (
    Department, Designation, Employee, LeaveApplication, LeaveBalance,
    PayrollPeriod, Payroll, Project, Task
)
from business.models import (
    Company, AuditProject, TaxReturnCase, BillableHour, Revenue, BMIIPOPRRecord
)
from analytics.models import AnalyticsSales, KPIMetric, Dashboard, Chart


class Command(BaseCommand):
    help = 'Seed fake data for ERP system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
        parser.add_argument(
            '--module',
            type=str,
            help='Specific module to seed: business, hrms, analytics, all',
            default='all'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🌱 Starting ERP data seeding...'))
        
        module = options.get('module', 'all')
        
        with transaction.atomic():
            if options['clear']:
                self.clear_data(module)
            
            # Always create base users first
            users = self.create_users()
            
            if module in ['all', 'hrms']:
                departments, designations = self.create_hrms_base()
                employees = self.create_employees(users, departments, designations)
                self.create_leaves(employees)
                self.create_payroll(employees)
                self.create_projects(users)
            else:
                employees = list(Employee.objects.all())
            
            if module in ['all', 'business']:
                companies = self.create_companies()
                self.create_audits(companies, users)
                self.create_tax_returns(companies, users)
                self.create_billable_hours(users, companies)
                self.create_revenue(companies)
                self.create_bmi_records(companies, users)
            
            if module in ['all', 'analytics']:
                self.create_analytics()
                self.create_dashboards()
        
        self.stdout.write(self.style.SUCCESS('✅ Data seeding completed successfully!'))

    def clear_data(self, module):
        """Clear existing data"""
        self.stdout.write(self.style.WARNING('🗑️  Clearing existing data...'))
        
        if module in ['all', 'business']:
            BMIIPOPRRecord.objects.all().delete()
            Revenue.objects.all().delete()
            BillableHour.objects.all().delete()
            TaxReturnCase.objects.all().delete()
            AuditProject.objects.all().delete()
            Company.objects.all().delete()
        
        if module in ['all', 'hrms']:
            Task.objects.all().delete()
            Project.objects.all().delete()
            Payroll.objects.all().delete()
            PayrollPeriod.objects.all().delete()
            LeaveBalance.objects.all().delete()
            LeaveApplication.objects.all().delete()
            Employee.objects.all().delete()
            Department.objects.all().delete()
            Designation.objects.all().delete()
        
        if module in ['all', 'analytics']:
            Chart.objects.all().delete()
            Dashboard.objects.all().delete()
            KPIMetric.objects.all().delete()
            AnalyticsSales.objects.all().delete()

    def create_users(self):
        """Create test users"""
        self.stdout.write('👤 Creating users...')
        
        users_data = [
            {'email': 'admin@wisematic.com', 'full_name': 'System Admin', 'role': 'ADMIN', 'is_staff': True, 'is_superuser': True},
            {'email': 'director@wisematic.com', 'full_name': 'John Director', 'role': 'ADMIN'},
            {'email': 'manager1@wisematic.com', 'full_name': 'Sarah Manager', 'role': 'USER'},
            {'email': 'manager2@wisematic.com', 'full_name': 'Mike Manager', 'role': 'USER'},
            {'email': 'accountant1@wisematic.com', 'full_name': 'Emily Chen', 'role': 'USER'},
            {'email': 'accountant2@wisematic.com', 'full_name': 'David Wong', 'role': 'USER'},
            {'email': 'accountant3@wisematic.com', 'full_name': 'Lisa Liu', 'role': 'USER'},
            {'email': 'clerk1@wisematic.com', 'full_name': 'Tom Clerk', 'role': 'USER'},
            {'email': 'clerk2@wisematic.com', 'full_name': 'Amy Assistant', 'role': 'USER'},
            {'email': 'intern@wisematic.com', 'full_name': 'Kevin Intern', 'role': 'USER'},
        ]
        
        users = []
        for data in users_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'full_name': data['full_name'],
                    'role': data['role'],
                    'is_staff': data.get('is_staff', False),
                    'is_superuser': data.get('is_superuser', False),
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        
        self.stdout.write(f'  Created {len(users)} users')
        return users

    def create_hrms_base(self):
        """Create departments and designations"""
        self.stdout.write('🏢 Creating departments and designations...')
        
        # Departments
        dept_data = [
            {'name': 'Executive', 'code': 'EXEC', 'budget': 500000},
            {'name': 'Audit', 'code': 'AUD', 'budget': 800000},
            {'name': 'Tax', 'code': 'TAX', 'budget': 600000},
            {'name': 'Advisory', 'code': 'ADV', 'budget': 700000},
            {'name': 'HR & Admin', 'code': 'HRA', 'budget': 300000},
            {'name': 'Finance', 'code': 'FIN', 'budget': 400000},
        ]
        
        departments = []
        for data in dept_data:
            dept, _ = Department.objects.get_or_create(
                name=data['name'],
                defaults={
                    'code': data['code'],
                    'budget': Decimal(str(data['budget'])),
                    'description': f"{data['name']} Department"
                }
            )
            departments.append(dept)
        
        # Designations
        desig_data = [
            {'name': 'Partner', 'level': 10},
            {'name': 'Director', 'level': 9},
            {'name': 'Senior Manager', 'level': 8},
            {'name': 'Manager', 'level': 7},
            {'name': 'Senior Accountant', 'level': 6},
            {'name': 'Accountant', 'level': 5},
            {'name': 'Junior Accountant', 'level': 4},
            {'name': 'Senior Clerk', 'level': 3},
            {'name': 'Clerk', 'level': 2},
            {'name': 'Intern', 'level': 1},
        ]
        
        designations = []
        for data in desig_data:
            desig, _ = Designation.objects.get_or_create(
                name=data['name'],
                defaults={
                    'level': data['level'],
                    'description': f"{data['name']} position"
                }
            )
            designations.append(desig)
        
        self.stdout.write(f'  Created {len(departments)} departments, {len(designations)} designations')
        return departments, designations

    def create_employees(self, users, departments, designations):
        """Create employee profiles"""
        self.stdout.write('👥 Creating employees...')
        
        employee_configs = [
            {'user_idx': 0, 'emp_id': 'EMP001', 'dept_idx': 0, 'desig_idx': 0, 'salary': 150000},
            {'user_idx': 1, 'emp_id': 'EMP002', 'dept_idx': 0, 'desig_idx': 1, 'salary': 100000},
            {'user_idx': 2, 'emp_id': 'EMP003', 'dept_idx': 1, 'desig_idx': 3, 'salary': 65000},
            {'user_idx': 3, 'emp_id': 'EMP004', 'dept_idx': 2, 'desig_idx': 3, 'salary': 65000},
            {'user_idx': 4, 'emp_id': 'EMP005', 'dept_idx': 1, 'desig_idx': 5, 'salary': 45000},
            {'user_idx': 5, 'emp_id': 'EMP006', 'dept_idx': 2, 'desig_idx': 5, 'salary': 45000},
            {'user_idx': 6, 'emp_id': 'EMP007', 'dept_idx': 3, 'desig_idx': 4, 'salary': 55000},
            {'user_idx': 7, 'emp_id': 'EMP008', 'dept_idx': 4, 'desig_idx': 8, 'salary': 25000},
            {'user_idx': 8, 'emp_id': 'EMP009', 'dept_idx': 5, 'desig_idx': 8, 'salary': 25000},
            {'user_idx': 9, 'emp_id': 'EMP010', 'dept_idx': 1, 'desig_idx': 9, 'salary': 15000},
        ]
        
        employees = []
        for config in employee_configs:
            emp, _ = Employee.objects.get_or_create(
                user=users[config['user_idx']],
                defaults={
                    'employee_id': config['emp_id'],
                    'department': departments[config['dept_idx']],
                    'designation': designations[config['desig_idx']],
                    'base_salary': Decimal(str(config['salary'])),
                    'hire_date': date.today() - timedelta(days=random.randint(100, 1000)),
                    'employment_status': 'ACTIVE',
                    'employment_type': 'FULL_TIME' if config['desig_idx'] < 9 else 'INTERN',
                    'phone': f'+852 {random.randint(9000, 9999)} {random.randint(1000, 9999)}',
                }
            )
            employees.append(emp)
        
        self.stdout.write(f'  Created {len(employees)} employees')
        return employees

    def create_leaves(self, employees):
        """Create leave applications and balances"""
        self.stdout.write('🏖️  Creating leave data...')
        
        leave_types = ['SICK', 'CASUAL', 'EARNED']
        statuses = ['PENDING', 'APPROVED', 'REJECTED']
        
        # Create leave balances for current year
        current_year = date.today().year
        for emp in employees:
            for leave_type in leave_types:
                LeaveBalance.objects.get_or_create(
                    employee=emp,
                    year=current_year,
                    leave_type=leave_type,
                    defaults={
                        'entitled_days': Decimal('14') if leave_type == 'EARNED' else Decimal('10'),
                        'used_days': Decimal(str(random.randint(0, 5))),
                    }
                )
        
        # Create some leave applications
        for _ in range(20):
            emp = random.choice(employees)
            start = date.today() - timedelta(days=random.randint(-30, 60))
            days = random.randint(1, 5)
            
            LeaveApplication.objects.create(
                employee=emp,
                leave_type=random.choice(leave_types),
                start_date=start,
                end_date=start + timedelta(days=days - 1),
                total_days=Decimal(str(days)),
                reason=f'Leave request for {days} day(s)',
                status=random.choice(statuses),
            )
        
        self.stdout.write('  Created leave balances and applications')

    def create_payroll(self, employees):
        """Create payroll periods and records"""
        self.stdout.write('💰 Creating payroll data...')
        
        # Create last 6 months of payroll periods
        today = date.today()
        periods = []
        for i in range(6):
            month_offset = i
            year = today.year
            month = today.month - month_offset
            if month < 1:
                month += 12
                year -= 1
            
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            
            period, _ = PayrollPeriod.objects.get_or_create(
                year=year,
                month=month,
                defaults={
                    'name': f'{start.strftime("%B %Y")}',
                    'start_date': start,
                    'end_date': end,
                    'payment_date': end + timedelta(days=5),
                    'status': 'PAID' if i > 0 else 'DRAFT',
                }
            )
            periods.append(period)
        
        # Create payroll records for each employee
        for period in periods:
            for emp in employees:
                Payroll.objects.get_or_create(
                    employee=emp,
                    period=period,
                    defaults={
                        'basic_salary': emp.base_salary,
                        'overtime_pay': Decimal(str(random.randint(0, 5000))),
                        'allowances': Decimal(str(random.randint(1000, 3000))),
                        'tax_deduction': emp.base_salary * Decimal('0.05'),
                        'mpf_employee': min(emp.base_salary * Decimal('0.05'), Decimal('1500')),
                        'mpf_employer': min(emp.base_salary * Decimal('0.05'), Decimal('1500')),
                        'working_days': random.randint(20, 23),
                        'status': period.status,
                    }
                )
        
        self.stdout.write(f'  Created {len(periods)} payroll periods')

    def create_projects(self, users):
        """Create HR projects and tasks"""
        self.stdout.write('📋 Creating projects and tasks...')
        
        projects_data = [
            {'name': 'Year-End Audit Process Improvement', 'status': 'IN_PROGRESS'},
            {'name': 'Tax Filing System Upgrade', 'status': 'IN_PROGRESS'},
            {'name': 'Employee Training Program', 'status': 'CREATED'},
            {'name': 'Client Portal Development', 'status': 'ON_HOLD'},
            {'name': 'Office Relocation Planning', 'status': 'COMPLETED'},
        ]
        
        for proj_data in projects_data:
            project, _ = Project.objects.get_or_create(
                name=proj_data['name'],
                defaults={
                    'description': f"Project: {proj_data['name']}",
                    'start_date': date.today() - timedelta(days=random.randint(30, 180)),
                    'end_date': date.today() + timedelta(days=random.randint(30, 180)),
                    'status': proj_data['status'],
                    'owner': random.choice(users[:4]),
                    'progress': random.randint(0, 100),
                }
            )
            
            # Create tasks for each project
            for i in range(random.randint(3, 7)):
                Task.objects.get_or_create(
                    project=project,
                    title=f'Task {i + 1} for {project.name[:20]}',
                    defaults={
                        'description': f'Task description {i + 1}',
                        'due_date': date.today() + timedelta(days=random.randint(1, 60)),
                        'status': random.choice(['TODO', 'IN_PROGRESS', 'DONE']),
                        'priority': random.choice(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
                        'assigned_to': random.choice(users),
                    }
                )
        
        self.stdout.write('  Created projects and tasks')

    def create_companies(self):
        """Create client companies"""
        self.stdout.write('🏭 Creating companies...')
        
        companies_data = [
            {'name': 'Acme Corporation', 'industry': 'Manufacturing'},
            {'name': 'Globex Industries', 'industry': 'Technology'},
            {'name': 'Stark Enterprises', 'industry': 'Engineering'},
            {'name': 'Wayne Industries', 'industry': 'Finance'},
            {'name': 'Umbrella Corp', 'industry': 'Healthcare'},
            {'name': 'Cyberdyne Systems', 'industry': 'AI Technology'},
            {'name': 'Weyland-Yutani', 'industry': 'Aerospace'},
            {'name': 'Oscorp Industries', 'industry': 'Biotechnology'},
            {'name': 'Massive Dynamic', 'industry': 'Research'},
            {'name': 'Tyrell Corporation', 'industry': 'Robotics'},
        ]
        
        companies = []
        for data in companies_data:
            company, _ = Company.objects.get_or_create(
                name=data['name'],
                defaults={
                    'industry': data['industry'],
                    'registration_number': f'CR{random.randint(100000, 999999)}',
                    'tax_id': f'TID{random.randint(10000000, 99999999)}',
                    'contact_person': f'{random.choice(["Mr.", "Ms.", "Dr."])} {data["name"].split()[0]}',
                    'contact_email': f'contact@{data["name"].lower().replace(" ", "")}.com',
                    'contact_phone': f'+852 {random.randint(2000, 3999)} {random.randint(1000, 9999)}',
                    'address': f'{random.randint(1, 50)}/F, Tower {random.choice(["A", "B", "C"])}, Central, Hong Kong',
                }
            )
            companies.append(company)
        
        self.stdout.write(f'  Created {len(companies)} companies')
        return companies

    def create_audits(self, companies, users):
        """Create audit projects"""
        self.stdout.write('📊 Creating audit projects...')
        
        statuses = ['NOT_STARTED', 'PLANNING', 'FIELDWORK', 'REVIEW', 'REPORTING', 'COMPLETED']
        
        for company in companies[:7]:
            AuditProject.objects.get_or_create(
                company=company,
                fiscal_year='2024',
                defaults={
                    'audit_type': random.choice(['FINANCIAL', 'TAX', 'INTERNAL']),
                    'progress': random.randint(0, 100),
                    'status': random.choice(statuses),
                    'start_date': date(2024, 1, 1) + timedelta(days=random.randint(0, 90)),
                    'deadline': date(2024, 12, 31),
                    'assigned_to': random.choice(users[:5]),
                    'budget_hours': Decimal(str(random.randint(100, 500))),
                    'actual_hours': Decimal(str(random.randint(0, 300))),
                }
            )
        
        self.stdout.write('  Created audit projects')

    def create_tax_returns(self, companies, users):
        """Create tax return cases"""
        self.stdout.write('📝 Creating tax return cases...')
        
        statuses = ['PENDING', 'IN_PROGRESS', 'UNDER_REVIEW', 'SUBMITTED', 'ACCEPTED']
        
        for company in companies:
            TaxReturnCase.objects.get_or_create(
                company=company,
                tax_year='2023/24',
                defaults={
                    'tax_type': 'PROFITS_TAX',
                    'progress': random.randint(0, 100),
                    'status': random.choice(statuses),
                    'deadline': date(2024, 11, 30) + timedelta(days=random.randint(-60, 60)),
                    'handler': random.choice(users[:5]),
                    'tax_amount': Decimal(str(random.randint(50000, 500000))),
                    'documents_received': random.choice([True, False]),
                }
            )
        
        self.stdout.write('  Created tax return cases')

    def create_billable_hours(self, users, companies):
        """Create billable hours records"""
        self.stdout.write('⏱️  Creating billable hours...')
        
        roles = ['CLERK', 'ACCOUNTANT', 'MANAGER', 'DIRECTOR']
        
        for _ in range(50):
            user = random.choice(users)
            company = random.choice(companies)
            role = random.choice(roles)
            
            BillableHour.objects.create(
                employee=user,
                company=company,
                project_reference=f'AUD-{company.name[:3].upper()}-2024',
                role=role,
                base_hourly_rate=Decimal('100'),
                date=date.today() - timedelta(days=random.randint(0, 60)),
                actual_hours=Decimal(str(random.randint(1, 10))),
                description=f'Work on {company.name} project',
                is_billable=random.choice([True, True, True, False]),  # 75% billable
            )
        
        self.stdout.write('  Created billable hours')

    def create_revenue(self, companies):
        """Create revenue records"""
        self.stdout.write('💵 Creating revenue records...')
        
        statuses = ['PENDING', 'PARTIAL', 'RECEIVED', 'OVERDUE']
        
        for company in companies:
            for i in range(random.randint(1, 3)):
                total = Decimal(str(random.randint(50000, 500000)))
                received = total * Decimal(str(random.uniform(0, 1)))
                
                Revenue.objects.create(
                    company=company,
                    invoice_number=f'INV-{company.id.hex[:6].upper()}-{i+1:03d}',
                    description=f'Professional services for {company.name}',
                    total_amount=total,
                    received_amount=received.quantize(Decimal('0.01')),
                    status=random.choice(statuses),
                    invoice_date=date.today() - timedelta(days=random.randint(10, 90)),
                    due_date=date.today() + timedelta(days=random.randint(-30, 60)),
                    contact_name=company.contact_person,
                    contact_email=company.contact_email,
                    contact_phone=company.contact_phone,
                )
        
        self.stdout.write('  Created revenue records')

    def create_bmi_records(self, companies, users):
        """Create BMI IPO/PR records"""
        self.stdout.write('📈 Creating BMI IPO/PR records...')
        
        stages = ['INITIAL_ASSESSMENT', 'DUE_DILIGENCE', 'DOCUMENTATION', 'REGULATORY_FILING', 'MARKETING']
        statuses = ['ACTIVE', 'ON_TRACK', 'DELAYED', 'COMPLETED']
        
        for company in companies[:5]:
            BMIIPOPRRecord.objects.get_or_create(
                project_name=f'{company.name} IPO Project',
                company=company,
                defaults={
                    'stage': random.choice(stages),
                    'status': random.choice(statuses),
                    'project_type': random.choice(['IPO', 'PR', 'RIGHTS_ISSUE']),
                    'estimated_value': Decimal(str(random.randint(10000000, 100000000))),
                    'total_cost': Decimal(str(random.randint(500000, 5000000))),
                    'start_date': date.today() - timedelta(days=random.randint(30, 180)),
                    'target_completion_date': date.today() + timedelta(days=random.randint(60, 365)),
                    'progress': random.randint(0, 100),
                    'lead_manager': random.choice(users[:3]),
                }
            )
        
        self.stdout.write('  Created BMI IPO/PR records')

    def create_analytics(self):
        """Create sales analytics data"""
        self.stdout.write('📊 Creating analytics data...')
        
        # Create 12 months of sales data
        current_year = date.today().year
        base_revenue = 1000000
        
        for month in range(1, 13):
            revenue = base_revenue * (1 + random.uniform(-0.2, 0.3))
            prev_revenue = base_revenue * (1 + random.uniform(-0.2, 0.2))
            
            AnalyticsSales.objects.get_or_create(
                year=current_year,
                month=month,
                defaults={
                    'revenue': Decimal(str(int(revenue))),
                    'target_revenue': Decimal(str(int(base_revenue * 1.1))),
                    'growth_percentage': Decimal(str(round((revenue - prev_revenue) / prev_revenue * 100, 2))),
                    'new_clients': random.randint(2, 10),
                    'total_clients': 50 + month * 3,
                    'churned_clients': random.randint(0, 3),
                    'churn_rate': Decimal(str(round(random.uniform(1, 5), 2))),
                    'deals_closed': random.randint(5, 20),
                    'deals_pipeline': random.randint(10, 30),
                    'average_deal_value': Decimal(str(random.randint(50000, 150000))),
                    'operating_costs': Decimal(str(int(revenue * 0.6))),
                    'marketing_spend': Decimal(str(random.randint(20000, 80000))),
                }
            )
        
        # Create KPI metrics
        kpis_data = [
            {'name': 'Monthly Revenue', 'category': 'FINANCIAL', 'current': 1200000, 'target': 1500000, 'unit': 'HKD'},
            {'name': 'Client Satisfaction', 'category': 'OPERATIONAL', 'current': 92, 'target': 95, 'unit': '%'},
            {'name': 'Employee Utilization', 'category': 'HR', 'current': 78, 'target': 85, 'unit': '%'},
            {'name': 'New Clients', 'category': 'SALES', 'current': 8, 'target': 10, 'unit': 'clients'},
            {'name': 'Audit Completion Rate', 'category': 'OPERATIONAL', 'current': 85, 'target': 90, 'unit': '%'},
        ]
        
        for kpi in kpis_data:
            KPIMetric.objects.get_or_create(
                name=kpi['name'],
                defaults={
                    'category': kpi['category'],
                    'current_value': Decimal(str(kpi['current'])),
                    'target_value': Decimal(str(kpi['target'])),
                    'previous_value': Decimal(str(kpi['current'] * 0.9)),
                    'unit': kpi['unit'],
                    'period': f'{current_year}-Q4',
                }
            )
        
        self.stdout.write('  Created analytics data')

    def create_dashboards(self):
        """Create default dashboards"""
        self.stdout.write('📉 Creating dashboards...')
        
        # Main Dashboard
        dashboard, _ = Dashboard.objects.get_or_create(
            title='Executive Dashboard',
            defaults={
                'description': 'Company-wide KPIs and metrics',
                'is_default': True,
            }
        )
        
        charts_data = [
            {'title': 'Monthly Revenue', 'type': 'line', 'position': 1},
            {'title': 'Client Distribution', 'type': 'pie', 'position': 2},
            {'title': 'Audit Progress', 'type': 'bar', 'position': 3},
            {'title': 'Revenue vs Target', 'type': 'bar', 'position': 4},
        ]
        
        for chart_data in charts_data:
            Chart.objects.get_or_create(
                dashboard=dashboard,
                title=chart_data['title'],
                defaults={
                    'type': chart_data['type'],
                    'position': chart_data['position'],
                    'config': {'series': [], 'labels': []},
                }
            )
        
        self.stdout.write('  Created dashboards and charts')
