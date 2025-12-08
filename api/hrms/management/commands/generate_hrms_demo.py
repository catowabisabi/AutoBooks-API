"""
HRMS Demo Fixture Generator
============================
Generate demo data for HRMS module (employees, departments, leaves, etc.)
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate demo data for HRMS module'
    
    # Sample data pools
    FIRST_NAMES = [
        'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
        'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
        'Thomas', 'Sarah', 'Charles', 'Karen', 'Wei', 'Mei', 'Jun', 'Xia', 'Hong',
        'Yuki', 'Kenji', 'Sakura', 'Haruki', 'Aiko', 'Jin', 'Min', 'Soo', 'Hye', 'Jae'
    ]
    
    LAST_NAMES = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
        'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
        'Wang', 'Li', 'Zhang', 'Liu', 'Chen', 'Tanaka', 'Yamamoto', 'Suzuki', 'Watanabe',
        'Kim', 'Lee', 'Park', 'Choi', 'Jung', 'Kang'
    ]
    
    DEPARTMENTS = [
        {'name': 'Engineering', 'code': 'ENG', 'description': 'Software development and technical operations'},
        {'name': 'Human Resources', 'code': 'HR', 'description': 'Employee relations and recruitment'},
        {'name': 'Finance', 'code': 'FIN', 'description': 'Financial planning and accounting'},
        {'name': 'Marketing', 'code': 'MKT', 'description': 'Brand management and marketing campaigns'},
        {'name': 'Sales', 'code': 'SLS', 'description': 'Sales and business development'},
        {'name': 'Operations', 'code': 'OPS', 'description': 'Business operations and logistics'},
        {'name': 'Customer Support', 'code': 'SUP', 'description': 'Customer service and support'},
        {'name': 'Product', 'code': 'PRD', 'description': 'Product management and strategy'},
        {'name': 'Design', 'code': 'DSN', 'description': 'UI/UX and graphic design'},
        {'name': 'Legal', 'code': 'LGL', 'description': 'Legal affairs and compliance'},
    ]
    
    DESIGNATIONS = [
        {'name': 'CEO', 'level': 10},
        {'name': 'CTO', 'level': 9},
        {'name': 'CFO', 'level': 9},
        {'name': 'VP', 'level': 8},
        {'name': 'Director', 'level': 7},
        {'name': 'Senior Manager', 'level': 6},
        {'name': 'Manager', 'level': 5},
        {'name': 'Team Lead', 'level': 4},
        {'name': 'Senior', 'level': 3},
        {'name': 'Associate', 'level': 2},
        {'name': 'Junior', 'level': 1},
        {'name': 'Intern', 'level': 0},
    ]
    
    PROJECTS = [
        {'name': 'Website Redesign', 'description': 'Complete redesign of company website'},
        {'name': 'Mobile App v2.0', 'description': 'Major update to mobile application'},
        {'name': 'CRM Implementation', 'description': 'Implement new CRM system'},
        {'name': 'Data Migration', 'description': 'Migrate legacy data to new system'},
        {'name': 'Security Audit', 'description': 'Comprehensive security assessment'},
        {'name': 'Process Automation', 'description': 'Automate manual business processes'},
        {'name': 'Training Program', 'description': 'Employee training and development'},
        {'name': 'Market Research', 'description': 'Customer and competitor analysis'},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--employees',
            type=int,
            default=50,
            help='Number of employees to create (default: 50)'
        )
        parser.add_argument(
            '--leaves',
            type=int,
            default=30,
            help='Number of leave applications to create (default: 30)'
        )
        parser.add_argument(
            '--tasks',
            type=int,
            default=40,
            help='Number of tasks to create (default: 40)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing HRMS data before generating'
        )

    def handle(self, *args, **options):
        from hrms.models import Department, Designation, Employee, LeaveApplication, Project, Task
        
        num_employees = options['employees']
        num_leaves = options['leaves']
        num_tasks = options['tasks']
        
        if options['clear']:
            self.stdout.write('Clearing existing HRMS data...')
            Task.objects.all().delete()
            Project.objects.all().delete()
            LeaveApplication.objects.all().delete()
            Employee.objects.all().delete()
            Designation.objects.all().delete()
            Department.objects.all().delete()
        
        # Create departments
        self.stdout.write('Creating departments...')
        departments = []
        for dept_data in self.DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'description': dept_data['description'],
                    'budget': random.randint(100000, 1000000),
                    'is_active': True,
                }
            )
            departments.append(dept)
            if created:
                self.stdout.write(f'  Created department: {dept.name}')
        
        # Create designations
        self.stdout.write('Creating designations...')
        designations = []
        for des_data in self.DESIGNATIONS:
            des, created = Designation.objects.get_or_create(
                name=des_data['name'],
                defaults={
                    'level': des_data['level'],
                    'is_active': True,
                }
            )
            designations.append(des)
            if created:
                self.stdout.write(f'  Created designation: {des.name}')
        
        # Create employees
        self.stdout.write(f'Creating {num_employees} employees...')
        employees = []
        used_ids = set()
        
        for i in range(num_employees):
            # Generate unique employee ID
            while True:
                emp_id = f'EMP{random.randint(1000, 9999)}'
                if emp_id not in used_ids:
                    used_ids.add(emp_id)
                    break
            
            first_name = random.choice(self.FIRST_NAMES)
            last_name = random.choice(self.LAST_NAMES)
            email = f'{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@example.com'
            
            # Create user if needed
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                }
            )
            
            # Random dates
            hire_date = timezone.now() - timedelta(days=random.randint(30, 1500))
            dob = timezone.now() - timedelta(days=random.randint(8000, 18000))
            
            # Determine designation based on index (hierarchy)
            if i == 0:
                designation = designations[0]  # CEO
            elif i < 3:
                designation = designations[random.randint(1, 3)]  # C-level
            elif i < 10:
                designation = designations[random.randint(4, 6)]  # Directors/Managers
            else:
                designation = designations[random.randint(7, 11)]  # Staff
            
            employee = Employee.objects.create(
                user=user,
                employee_id=emp_id,
                department=random.choice(departments),
                designation=designation,
                employment_status=random.choices(
                    ['ACTIVE', 'ON_LEAVE', 'PROBATION'],
                    weights=[85, 10, 5]
                )[0],
                employment_type=random.choices(
                    ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'],
                    weights=[70, 10, 15, 5]
                )[0],
                hire_date=hire_date.date(),
                date_of_birth=dob.date(),
                gender=random.choice(['male', 'female', 'other']),
                phone=f'+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}',
                base_salary=random.randint(30000, 150000),
                annual_leave_balance=random.randint(5, 25),
                sick_leave_balance=random.randint(5, 15),
                is_active=True,
            )
            employees.append(employee)
        
        # Assign managers
        self.stdout.write('Assigning managers...')
        for emp in employees[1:]:  # Skip first (CEO)
            potential_managers = [e for e in employees if e.designation.level > emp.designation.level]
            if potential_managers:
                emp.manager = random.choice(potential_managers)
                emp.save()
        
        # Assign department managers
        for dept in departments:
            dept_employees = [e for e in employees if e.department == dept]
            if dept_employees:
                highest = max(dept_employees, key=lambda e: e.designation.level)
                dept.manager = highest
                dept.save()
        
        # Create projects
        self.stdout.write('Creating projects...')
        projects = []
        for proj_data in self.PROJECTS:
            owner = random.choice([e for e in employees if e.designation.level >= 5])
            start_date = timezone.now() - timedelta(days=random.randint(0, 180))
            
            project = Project.objects.create(
                name=proj_data['name'],
                description=proj_data['description'],
                start_date=start_date.date(),
                end_date=(start_date + timedelta(days=random.randint(60, 180))).date(),
                status=random.choice(['CREATED', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED']),
                owner=owner,
                budget=random.randint(10000, 100000),
                progress=random.randint(0, 100),
                is_active=True,
            )
            projects.append(project)
            self.stdout.write(f'  Created project: {project.name}')
        
        # Create tasks
        self.stdout.write(f'Creating {num_tasks} tasks...')
        task_titles = [
            'Review documentation', 'Fix bug', 'Implement feature', 'Write tests',
            'Update dependencies', 'Code review', 'Deploy to staging', 'Performance optimization',
            'Security patch', 'Database migration', 'API integration', 'UI improvements',
        ]
        
        for _ in range(num_tasks):
            project = random.choice(projects)
            assigned_to = random.choice(employees)
            assigned_by = assigned_to.manager or random.choice(employees)
            
            Task.objects.create(
                project=project,
                title=f'{random.choice(task_titles)} #{random.randint(100, 999)}',
                description=f'Task description for {project.name}',
                due_date=(timezone.now() + timedelta(days=random.randint(-30, 60))).date(),
                status=random.choice(['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE', 'BLOCKED']),
                priority=random.choice(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
                assigned_to=assigned_to,
                assigned_by=assigned_by,
                estimated_hours=random.randint(1, 40),
                actual_hours=random.randint(0, 50) if random.random() > 0.3 else None,
                is_active=True,
            )
        
        # Create leave applications
        self.stdout.write(f'Creating {num_leaves} leave applications...')
        leave_types = ['SICK', 'CASUAL', 'EARNED', 'MATERNITY', 'PATERNITY', 'UNPAID']
        
        for _ in range(num_leaves):
            employee = random.choice(employees)
            start_date = timezone.now() + timedelta(days=random.randint(-60, 60))
            days = random.randint(1, 10)
            
            status = random.choices(
                ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'],
                weights=[30, 50, 15, 5]
            )[0]
            
            leave = LeaveApplication.objects.create(
                employee=employee,
                leave_type=random.choice(leave_types),
                start_date=start_date.date(),
                end_date=(start_date + timedelta(days=days)).date(),
                total_days=days,
                reason=f'Leave request for personal reasons',
                status=status,
                is_active=True,
            )
            
            if status == 'APPROVED' and employee.manager:
                leave.approved_by = employee.manager
                leave.approved_at = timezone.now()
                leave.save()
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'''
HRMS Demo Data Generated Successfully!
======================================
Departments: {len(departments)}
Designations: {len(designations)}
Employees: {num_employees}
Projects: {len(projects)}
Tasks: {num_tasks}
Leave Applications: {num_leaves}
        '''))
