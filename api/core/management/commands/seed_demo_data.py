"""
Seed demo data for the Wisematic ERP system.
This command creates sample data for testing and demonstration.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed demo data for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo data before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...\n')
        
        # Create demo users
        self._create_users()
        
        # Create HRMS data
        self._create_hrms_data()
        
        # Create accounting data
        self._create_accounting_data()
        
        # Create documents
        self._create_documents()
        
        # Create projects
        self._create_projects()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))

    def _create_users(self):
        """Create demo users"""
        self.stdout.write('Creating demo users...')
        
        demo_users = [
            {
                'email': 'admin@wisematic.com',
                'full_name': 'Admin User',
                'is_staff': True,
                'is_superuser': True,
                'role': 'ADMIN',
            },
            {
                'email': 'manager@wisematic.com',
                'full_name': 'John Manager',
                'is_staff': True,
                'role': 'USER',
            },
            {
                'email': 'accountant@wisematic.com',
                'full_name': 'Alice Chen',
                'is_staff': True,
                'role': 'USER',
            },
            {
                'email': 'hr@wisematic.com',
                'full_name': 'Bob HR',
                'is_staff': True,
                'role': 'USER',
            },
            {
                'email': 'employee@wisematic.com',
                'full_name': 'Tom Employee',
                'is_staff': False,
                'role': 'USER',
            },
        ]
        
        for user_data in demo_users:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password('demo123456')
                user.save()
                self.stdout.write(f'  Created user: {user.email}')
            else:
                self.stdout.write(f'  User exists: {user.email}')

    def _create_hrms_data(self):
        """Create HRMS demo data"""
        self.stdout.write('Creating HRMS data...')
        
        try:
            from hrms.models import Department, Designation, Employee, Leave
            
            # Departments
            departments_data = [
                {'name': 'Engineering', 'code': 'ENG', 'description': 'Software Engineering Team'},
                {'name': 'Finance', 'code': 'FIN', 'description': 'Finance and Accounting'},
                {'name': 'Human Resources', 'code': 'HR', 'description': 'HR Department'},
                {'name': 'Sales', 'code': 'SALES', 'description': 'Sales and Marketing'},
                {'name': 'Operations', 'code': 'OPS', 'description': 'Operations Team'},
            ]
            
            departments = {}
            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    code=dept_data['code'],
                    defaults=dept_data
                )
                departments[dept_data['code']] = dept
                if created:
                    self.stdout.write(f'  Created department: {dept.name}')
            
            # Designations
            designations_data = [
                {'title': 'Software Engineer', 'level': 'L3'},
                {'title': 'Senior Software Engineer', 'level': 'L4'},
                {'title': 'Engineering Manager', 'level': 'L5'},
                {'title': 'Accountant', 'level': 'L3'},
                {'title': 'Senior Accountant', 'level': 'L4'},
                {'title': 'HR Specialist', 'level': 'L3'},
                {'title': 'Sales Representative', 'level': 'L3'},
            ]
            
            designations = {}
            for desig_data in designations_data:
                desig, created = Designation.objects.get_or_create(
                    title=desig_data['title'],
                    defaults=desig_data
                )
                designations[desig_data['title']] = desig
                if created:
                    self.stdout.write(f'  Created designation: {desig.title}')
            
            # Employees
            employees_data = [
                {
                    'employee_id': 'EMP001',
                    'user_email': 'manager@wisematic.com',
                    'department': 'ENG',
                    'designation': 'Engineering Manager',
                    'salary': Decimal('120000'),
                },
                {
                    'employee_id': 'EMP002',
                    'user_email': 'accountant@wisematic.com',
                    'department': 'FIN',
                    'designation': 'Senior Accountant',
                    'salary': Decimal('85000'),
                },
                {
                    'employee_id': 'EMP003',
                    'user_email': 'hr@wisematic.com',
                    'department': 'HR',
                    'designation': 'HR Specialist',
                    'salary': Decimal('75000'),
                },
                {
                    'employee_id': 'EMP004',
                    'user_email': 'employee@wisematic.com',
                    'department': 'ENG',
                    'designation': 'Software Engineer',
                    'salary': Decimal('90000'),
                },
            ]
            
            for emp_data in employees_data:
                try:
                    user = User.objects.get(email=emp_data['user_email'])
                    emp, created = Employee.objects.get_or_create(
                        employee_id=emp_data['employee_id'],
                        defaults={
                            'user': user,
                            'department': departments.get(emp_data['department']),
                            'designation': designations.get(emp_data['designation']),
                            'salary': emp_data['salary'],
                            'date_joined': timezone.now().date() - timedelta(days=random.randint(30, 365)),
                        }
                    )
                    if created:
                        self.stdout.write(f'  Created employee: {emp.employee_id}')
                except User.DoesNotExist:
                    self.stdout.write(f'  User not found for employee: {emp_data["employee_id"]}')
            
        except ImportError:
            self.stdout.write('  HRMS module not available, skipping...')
        except Exception as e:
            self.stdout.write(f'  Error creating HRMS data: {e}')

    def _create_accounting_data(self):
        """Create accounting demo data"""
        self.stdout.write('Creating accounting data...')
        
        try:
            from accounting.models import (
                Account, JournalEntry, JournalEntryLine,
                Invoice, InvoiceLine, Payment, Expense
            )
            
            # Get some accounts
            cash = Account.objects.filter(code='1100').first()
            ar = Account.objects.filter(code='1200').first()
            ap = Account.objects.filter(code='2100').first()
            revenue = Account.objects.filter(code='4100').first()
            expense = Account.objects.filter(code='5100').first()
            
            if not all([cash, ar, revenue]):
                self.stdout.write('  Required accounts not found, run init_accounting first')
                return
            
            # Create sample journal entries
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                return
            
            entries_data = [
                {
                    'description': 'Initial capital investment',
                    'debit_account': cash,
                    'credit_account': Account.objects.filter(code='3100').first(),  # Retained Earnings
                    'amount': Decimal('100000'),
                },
                {
                    'description': 'Service revenue received',
                    'debit_account': cash,
                    'credit_account': revenue,
                    'amount': Decimal('15000'),
                },
                {
                    'description': 'Office supplies purchase',
                    'debit_account': expense,
                    'credit_account': cash,
                    'amount': Decimal('500'),
                },
            ]
            
            for i, entry_data in enumerate(entries_data):
                if not entry_data['credit_account']:
                    continue
                    
                entry, created = JournalEntry.objects.get_or_create(
                    entry_number=f'JE-{timezone.now().year}-{str(i+1).zfill(4)}',
                    defaults={
                        'date': timezone.now().date() - timedelta(days=i*7),
                        'description': entry_data['description'],
                        'created_by': admin,
                        'status': 'posted',
                    }
                )
                
                if created:
                    # Debit line
                    JournalEntryLine.objects.create(
                        journal_entry=entry,
                        account=entry_data['debit_account'],
                        debit=entry_data['amount'],
                        credit=Decimal('0'),
                    )
                    # Credit line
                    JournalEntryLine.objects.create(
                        journal_entry=entry,
                        account=entry_data['credit_account'],
                        debit=Decimal('0'),
                        credit=entry_data['amount'],
                    )
                    self.stdout.write(f'  Created journal entry: {entry.entry_number}')
            
            # Create sample invoices
            invoices_data = [
                {
                    'invoice_number': 'INV-2024-0001',
                    'customer_name': 'ABC Corporation',
                    'customer_email': 'contact@abc.com',
                    'amount': Decimal('5000'),
                    'status': 'paid',
                },
                {
                    'invoice_number': 'INV-2024-0002',
                    'customer_name': 'XYZ Ltd.',
                    'customer_email': 'billing@xyz.com',
                    'amount': Decimal('3500'),
                    'status': 'sent',
                },
                {
                    'invoice_number': 'INV-2024-0003',
                    'customer_name': 'Tech Solutions Inc.',
                    'customer_email': 'ap@techsol.com',
                    'amount': Decimal('8000'),
                    'status': 'draft',
                },
            ]
            
            for inv_data in invoices_data:
                inv, created = Invoice.objects.get_or_create(
                    invoice_number=inv_data['invoice_number'],
                    defaults={
                        'invoice_type': 'sales',
                        'customer_name': inv_data['customer_name'],
                        'customer_email': inv_data['customer_email'],
                        'date': timezone.now().date() - timedelta(days=random.randint(1, 30)),
                        'due_date': timezone.now().date() + timedelta(days=30),
                        'total_amount': inv_data['amount'],
                        'amount_due': inv_data['amount'] if inv_data['status'] != 'paid' else Decimal('0'),
                        'status': inv_data['status'],
                        'created_by': admin,
                    }
                )
                
                if created:
                    InvoiceLine.objects.create(
                        invoice=inv,
                        description='Professional Services',
                        quantity=1,
                        unit_price=inv_data['amount'],
                        amount=inv_data['amount'],
                        account=revenue,
                    )
                    self.stdout.write(f'  Created invoice: {inv.invoice_number}')
            
        except ImportError as e:
            self.stdout.write(f'  Accounting module not available: {e}')
        except Exception as e:
            self.stdout.write(f'  Error creating accounting data: {e}')

    def _create_documents(self):
        """Create document demo data"""
        self.stdout.write('Creating documents...')
        
        try:
            from documents.models import Document, Folder
            
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                return
            
            # Create folders
            folders_data = [
                {'name': 'Invoices', 'description': 'Sales and purchase invoices'},
                {'name': 'Receipts', 'description': 'Expense receipts'},
                {'name': 'Contracts', 'description': 'Business contracts'},
                {'name': 'Reports', 'description': 'Financial reports'},
            ]
            
            for folder_data in folders_data:
                folder, created = Folder.objects.get_or_create(
                    name=folder_data['name'],
                    defaults={
                        **folder_data,
                        'created_by': admin,
                    }
                )
                if created:
                    self.stdout.write(f'  Created folder: {folder.name}')
                    
        except ImportError:
            self.stdout.write('  Documents module not available, skipping...')
        except Exception as e:
            self.stdout.write(f'  Error creating documents: {e}')

    def _create_projects(self):
        """Create project demo data"""
        self.stdout.write('Creating projects...')
        
        try:
            from projects.models import Project, Task
            
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                return
            
            projects_data = [
                {
                    'name': 'ERP Implementation',
                    'description': 'Implement Wisematic ERP system',
                    'status': 'in_progress',
                    'tasks': [
                        {'title': 'Setup accounting module', 'status': 'done'},
                        {'title': 'Configure HRMS', 'status': 'in_progress'},
                        {'title': 'Train users', 'status': 'todo'},
                    ]
                },
                {
                    'name': 'Q4 Financial Audit',
                    'description': 'Prepare for year-end audit',
                    'status': 'planning',
                    'tasks': [
                        {'title': 'Gather financial documents', 'status': 'todo'},
                        {'title': 'Review journal entries', 'status': 'todo'},
                        {'title': 'Prepare audit report', 'status': 'todo'},
                    ]
                },
            ]
            
            for proj_data in projects_data:
                proj, created = Project.objects.get_or_create(
                    name=proj_data['name'],
                    defaults={
                        'description': proj_data['description'],
                        'status': proj_data['status'],
                        'owner': admin,
                        'start_date': timezone.now().date(),
                        'end_date': timezone.now().date() + timedelta(days=90),
                    }
                )
                
                if created:
                    self.stdout.write(f'  Created project: {proj.name}')
                    
                    for task_data in proj_data.get('tasks', []):
                        Task.objects.create(
                            project=proj,
                            title=task_data['title'],
                            status=task_data['status'],
                            assigned_to=admin,
                        )
                        
        except ImportError:
            self.stdout.write('  Projects module not available, skipping...')
        except Exception as e:
            self.stdout.write(f'  Error creating projects: {e}')
