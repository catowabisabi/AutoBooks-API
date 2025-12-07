"""
Seed Demo Data for AI Assistants
Includes: Emails (10 types), Planner Tasks, Documents, Brainstorm Sessions
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

from ai_assistants.models import (
    # Email
    EmailAccount, Email, EmailTemplate,
    EmailStatus, EmailCategory, EmailPriority,
    # Planner
    PlannerTask, ScheduleEvent,
    TaskStatus, TaskPriority,
    # Document
    AIDocument, DocumentType,
    # Brainstorming
    BrainstormSession, BrainstormIdea,
    # Brainstorming Meeting
    BrainstormMeeting, BrainstormMeetingParticipant,
    MeetingStatus, MeetingParticipantRole, MeetingParticipantStatus,
)
from business.models import Company, AuditProject, BMIIPOPRRecord

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = 'Seed demo data for AI Assistants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--emails',
            type=int,
            default=30,
            help='Number of demo emails to create'
        )
        parser.add_argument(
            '--tasks',
            type=int,
            default=20,
            help='Number of planner tasks to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing AI assistant data before seeding'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting AI Assistants data seeding...'))
        
        if options['clear']:
            self.clear_data()
        
        # Get or create demo user
        user = self.get_or_create_user()
        
        # Get companies for linking
        companies = list(Company.objects.filter(is_active=True)[:5])
        projects = list(AuditProject.objects.filter(is_active=True)[:5])
        campaigns = list(BMIIPOPRRecord.objects.filter(is_active=True)[:5])
        
        # Seed data
        self.seed_email_templates(user)
        self.seed_email_accounts(user)
        self.seed_emails(user, companies, projects, options['emails'])
        self.seed_planner_tasks(user, companies, projects, options['tasks'])
        self.seed_schedule_events(user)
        self.seed_brainstorm_sessions(user, companies, campaigns)
        self.seed_brainstorm_meetings(user, companies, campaigns)
        
        self.stdout.write(self.style.SUCCESS('✅ AI Assistants data seeding completed!'))

    def clear_data(self):
        """Clear existing AI assistant data"""
        self.stdout.write('Clearing existing AI assistant data...')
        Email.objects.all().delete()
        EmailAccount.objects.all().delete()
        EmailTemplate.objects.all().delete()
        PlannerTask.objects.all().delete()
        ScheduleEvent.objects.all().delete()
        AIDocument.objects.all().delete()
        BrainstormSession.objects.all().delete()
        BrainstormIdea.objects.all().delete()
        BrainstormMeetingParticipant.objects.all().delete()
        BrainstormMeeting.objects.all().delete()
        self.stdout.write(self.style.WARNING('Existing data cleared.'))

    def get_or_create_user(self):
        """Get or create a demo user"""
        user, created = User.objects.get_or_create(
            email='demo@wisematic.com',
            defaults={
                'full_name': 'Demo User',
                'is_staff': True,
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write(f'Created demo user: {user.email}')
        return user

    def seed_email_templates(self, user):
        """Create email templates for all 10 categories"""
        self.stdout.write('Seeding email templates...')
        
        templates_data = [
            {
                'name': 'Payment Reminder',
                'category': EmailCategory.PAYMENT_REMINDER,
                'subject_template': 'Payment Reminder: Invoice #{{invoice_number}} Due {{due_date}}',
                'body_template': '''Dear {{client_name}},

This is a friendly reminder that invoice #{{invoice_number}} for {{amount}} is due on {{due_date}}.

Please arrange payment at your earliest convenience. If you have already made the payment, please disregard this notice.

Thank you for your business.

Best regards,
Wisematic Finance Team''',
                'variables': ['client_name', 'invoice_number', 'amount', 'due_date']
            },
            {
                'name': 'Project Follow-up',
                'category': EmailCategory.PROJECT_FOLLOWUP,
                'subject_template': 'Project Update: {{project_name}} - Week {{week_number}}',
                'body_template': '''Dear {{client_name}},

I wanted to follow up on the progress of {{project_name}}.

Current Status: {{status}}
Completion: {{completion_percent}}%
Next Milestone: {{next_milestone}}

Please let me know if you have any questions or need additional information.

Best regards,
{{manager_name}}''',
                'variables': ['client_name', 'project_name', 'status', 'completion_percent', 'next_milestone', 'week_number', 'manager_name']
            },
            {
                'name': 'Tax Document Request',
                'category': EmailCategory.TAX_DOC_REQUEST,
                'subject_template': 'Tax Document Request - {{tax_year}} Filing',
                'body_template': '''Dear {{client_name}},

As we prepare your {{tax_year}} tax return, we require the following documents:

{{document_list}}

Please submit these documents by {{deadline}} to ensure timely filing.

If you have any questions, please don't hesitate to contact us.

Best regards,
{{accountant_name}}
Wisematic Tax Team''',
                'variables': ['client_name', 'tax_year', 'document_list', 'deadline', 'accountant_name']
            },
            {
                'name': 'Meeting Confirmation',
                'category': EmailCategory.MEETING_CONFIRM,
                'subject_template': 'Meeting Confirmed: {{meeting_subject}} - {{meeting_date}}',
                'body_template': '''Dear {{attendee_name}},

This is to confirm your meeting:

Subject: {{meeting_subject}}
Date: {{meeting_date}}
Time: {{meeting_time}}
Location: {{location}}
{{meeting_link}}

Agenda:
{{agenda}}

Please confirm your attendance by replying to this email.

Best regards,
{{organizer_name}}''',
                'variables': ['attendee_name', 'meeting_subject', 'meeting_date', 'meeting_time', 'location', 'meeting_link', 'agenda', 'organizer_name']
            },
            {
                'name': 'Invoice Sent',
                'category': EmailCategory.INVOICE_SENT,
                'subject_template': 'Invoice #{{invoice_number}} from Wisematic',
                'body_template': '''Dear {{client_name}},

Please find attached invoice #{{invoice_number}} for services rendered.

Invoice Details:
Amount: {{amount}}
Due Date: {{due_date}}
Payment Terms: {{payment_terms}}

Payment Methods:
- Bank Transfer: {{bank_details}}
- Online: {{payment_link}}

Thank you for your business.

Best regards,
Wisematic Billing Team''',
                'variables': ['client_name', 'invoice_number', 'amount', 'due_date', 'payment_terms', 'bank_details', 'payment_link']
            },
            {
                'name': 'Event Invitation',
                'category': EmailCategory.EVENT_INVITE,
                'subject_template': "You're Invited: {{event_name}}",
                'body_template': '''Dear {{recipient_name}},

We are pleased to invite you to {{event_name}}.

Event Details:
Date: {{event_date}}
Time: {{event_time}}
Venue: {{venue}}

{{event_description}}

RSVP by {{rsvp_deadline}}: {{rsvp_link}}

We look forward to seeing you there!

Best regards,
Wisematic Events Team''',
                'variables': ['recipient_name', 'event_name', 'event_date', 'event_time', 'venue', 'event_description', 'rsvp_deadline', 'rsvp_link']
            },
            {
                'name': 'IPO Press Release',
                'category': EmailCategory.IPO_RELEASE,
                'subject_template': '{{company_name}} Announces IPO - {{release_date}}',
                'body_template': '''FOR IMMEDIATE RELEASE

{{headline}}

{{city}}, {{release_date}} - {{company_name}} today announced {{announcement_details}}.

Key Highlights:
{{highlights}}

About {{company_name}}:
{{company_description}}

Media Contact:
{{contact_name}}
{{contact_email}}
{{contact_phone}}

###''',
                'variables': ['company_name', 'release_date', 'headline', 'city', 'announcement_details', 'highlights', 'company_description', 'contact_name', 'contact_email', 'contact_phone']
            },
            {
                'name': 'Billing Issue Notice',
                'category': EmailCategory.BILLING_ISSUE,
                'subject_template': 'Action Required: Billing Issue - Account #{{account_number}}',
                'body_template': '''Dear {{client_name}},

We've encountered an issue with your recent payment:

Account: #{{account_number}}
Issue: {{issue_description}}
Invoice: #{{invoice_number}}

Required Action: {{required_action}}

Please resolve this matter by {{deadline}} to avoid service interruption.

Contact our billing team:
Email: billing@wisematic.com
Phone: {{phone_number}}

Best regards,
Wisematic Billing Support''',
                'variables': ['client_name', 'account_number', 'issue_description', 'invoice_number', 'required_action', 'deadline', 'phone_number']
            },
            {
                'name': 'Document Missing',
                'category': EmailCategory.DOCUMENT_MISSING,
                'subject_template': 'Missing Documents Required - {{project_name}}',
                'body_template': '''Dear {{client_name}},

We are missing the following documents for {{project_name}}:

Missing Documents:
{{missing_documents}}

These documents are required for {{purpose}}.

Please submit by {{deadline}} via:
- Email: documents@wisematic.com
- Upload Portal: {{upload_link}}

If you have any questions, please contact {{contact_name}}.

Best regards,
{{sender_name}}''',
                'variables': ['client_name', 'project_name', 'missing_documents', 'purpose', 'deadline', 'upload_link', 'contact_name', 'sender_name']
            },
            {
                'name': 'Appreciation Email',
                'category': EmailCategory.APPRECIATION,
                'subject_template': 'Thank You for {{occasion}}',
                'body_template': '''Dear {{recipient_name}},

I wanted to take a moment to express our sincere appreciation for {{occasion}}.

{{appreciation_message}}

Your {{contribution_type}} has made a significant impact on {{impact_area}}.

We truly value our partnership and look forward to continued collaboration.

With gratitude,
{{sender_name}}
{{sender_title}}
Wisematic''',
                'variables': ['recipient_name', 'occasion', 'appreciation_message', 'contribution_type', 'impact_area', 'sender_name', 'sender_title']
            },
        ]
        
        for data in templates_data:
            template, created = EmailTemplate.objects.get_or_create(
                name=data['name'],
                defaults={
                    'category': data['category'],
                    'subject_template': data['subject_template'],
                    'body_template': data['body_template'],
                    'variables': data['variables'],
                    'owner': user,
                    'is_shared': True,
                }
            )
            if created:
                self.stdout.write(f'  Created template: {template.name}')
        
        self.stdout.write(f'  Total templates: {EmailTemplate.objects.count()}')

    def seed_email_accounts(self, user):
        """Create demo email accounts"""
        self.stdout.write('Seeding email accounts...')
        
        accounts = [
            {'email': 'info@wisematic.com', 'name': 'Wisematic Info'},
            {'email': 'support@wisematic.com', 'name': 'Wisematic Support'},
            {'email': 'billing@wisematic.com', 'name': 'Wisematic Billing'},
        ]
        
        for acc in accounts:
            account, created = EmailAccount.objects.get_or_create(
                email_address=acc['email'],
                defaults={
                    'display_name': acc['name'],
                    'owner': user,
                    'is_demo': True,
                    'smtp_host': 'smtp.demo.com',
                    'smtp_port': 587,
                }
            )
            if created:
                self.stdout.write(f'  Created account: {account.email_address}')
        
        self.stdout.write(f'  Total accounts: {EmailAccount.objects.count()}')

    def seed_emails(self, user, companies, projects, count):
        """Create demo emails - 10 types per company as per Blueprint"""
        self.stdout.write(f'Seeding {count} demo emails...')
        
        accounts = list(EmailAccount.objects.all())
        if not accounts:
            self.stdout.write(self.style.WARNING('No email accounts found, skipping emails'))
            return
        
        email_samples = {
            EmailCategory.PAYMENT_REMINDER: {
                'subjects': [
                    'Payment Reminder: Invoice #INV-2024-001',
                    'Overdue Payment Notice - Account Review Required',
                    'Friendly Reminder: Outstanding Balance',
                ],
                'bodies': [
                    'This is a reminder that your invoice is due soon. Please arrange payment.',
                    'Our records show an outstanding balance on your account. Please review.',
                    'Just a friendly reminder about the pending payment for our services.',
                ]
            },
            EmailCategory.PROJECT_FOLLOWUP: {
                'subjects': [
                    'Project Update: Q4 Audit Progress Report',
                    'Follow-up: Financial Review Status',
                    'Weekly Project Sync - Action Items',
                ],
                'bodies': [
                    'Here is the latest update on your project. We have completed 75% of the work.',
                    'Following up on our recent meeting regarding the financial review.',
                    'Please find the action items from our weekly sync meeting.',
                ]
            },
            EmailCategory.TAX_DOC_REQUEST: {
                'subjects': [
                    'Tax Documentation Required - 2024 Filing',
                    'Missing Tax Documents - Urgent',
                    'Request for Tax Records - Annual Return',
                ],
                'bodies': [
                    'Please provide the following documents for your 2024 tax filing.',
                    'We are missing several key documents for your tax return.',
                    'As we prepare your annual return, please submit the required records.',
                ]
            },
            EmailCategory.MEETING_CONFIRM: {
                'subjects': [
                    'Meeting Confirmed: Quarterly Review - Dec 15',
                    'Calendar Invite: Strategy Session',
                    'Meeting Request Accepted',
                ],
                'bodies': [
                    'Your meeting has been confirmed. Please find the details below.',
                    'This email confirms the scheduled strategy session.',
                    'Thank you for accepting the meeting request.',
                ]
            },
            EmailCategory.INVOICE_SENT: {
                'subjects': [
                    'Invoice #INV-2024-156 Attached',
                    'Your Monthly Invoice from Wisematic',
                    'Service Invoice - December 2024',
                ],
                'bodies': [
                    'Please find the attached invoice for services rendered.',
                    'Your monthly invoice is now ready for review.',
                    'Attached is the invoice for services provided in December.',
                ]
            },
            EmailCategory.EVENT_INVITE: {
                'subjects': [
                    "You're Invited: Annual Client Appreciation Gala",
                    'Invitation: Industry Networking Event',
                    'Save the Date: 2025 Business Summit',
                ],
                'bodies': [
                    'We would be honored to have you at our annual gala.',
                    'Please join us for an evening of networking and insights.',
                    'Mark your calendar for our upcoming business summit.',
                ]
            },
            EmailCategory.IPO_RELEASE: {
                'subjects': [
                    'Press Release: TechCorp IPO Announcement',
                    'BREAKING: Major IPO Filing Submitted',
                    'IPO Update: Pricing and Timeline',
                ],
                'bodies': [
                    'FOR IMMEDIATE RELEASE - TechCorp announces intention to go public.',
                    'We are pleased to announce the successful IPO filing.',
                    'Important update regarding the upcoming IPO pricing.',
                ]
            },
            EmailCategory.BILLING_ISSUE: {
                'subjects': [
                    'Action Required: Payment Declined',
                    'Billing Issue - Please Update Payment Method',
                    'Important: Account Billing Notice',
                ],
                'bodies': [
                    'We were unable to process your recent payment.',
                    'Please update your payment method to avoid service interruption.',
                    'There is an issue with your account billing that needs attention.',
                ]
            },
            EmailCategory.DOCUMENT_MISSING: {
                'subjects': [
                    'Missing Documents for Audit Completion',
                    'Required Documents Not Received',
                    'Document Request Follow-up',
                ],
                'bodies': [
                    'We are still waiting for several documents to complete your audit.',
                    'The required documents have not been received yet.',
                    'Following up on our previous document request.',
                ]
            },
            EmailCategory.APPRECIATION: {
                'subjects': [
                    'Thank You for Your Partnership',
                    'Appreciation: Outstanding Collaboration',
                    'Gratitude for Your Trust in Wisematic',
                ],
                'bodies': [
                    'We want to express our heartfelt thanks for your continued trust.',
                    'Thank you for the outstanding collaboration on recent projects.',
                    'We truly appreciate your partnership and look forward to more success.',
                ]
            },
        }
        
        categories = list(email_samples.keys())
        
        for i in range(count):
            category = random.choice(categories)
            samples = email_samples[category]
            
            received_at = timezone.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23)
            )
            
            company = random.choice(companies) if companies else None
            project = random.choice(projects) if projects else None
            
            email = Email.objects.create(
                account=random.choice(accounts),
                from_address=fake.email(),
                from_name=fake.name(),
                to_addresses=[random.choice(accounts).email_address],
                subject=random.choice(samples['subjects']),
                body_text=random.choice(samples['bodies']),
                status=EmailStatus.RECEIVED,
                category=category,
                priority=random.choice([EmailPriority.LOW, EmailPriority.NORMAL, EmailPriority.HIGH]),
                received_at=received_at,
                is_read=random.choice([True, False]),
                is_starred=random.random() < 0.2,
                related_client=company,
                related_project=project,
                ai_summary=f"Auto-generated summary: {random.choice(samples['subjects'])}",
                ai_keywords=random.sample(['urgent', 'follow-up', 'document', 'payment', 'meeting', 'project'], 3),
            )
        
        self.stdout.write(f'  Created {count} emails across {len(categories)} categories')
        self.stdout.write(f'  Total emails: {Email.objects.count()}')

    def seed_planner_tasks(self, user, companies, projects, count):
        """Create demo planner tasks"""
        self.stdout.write(f'Seeding {count} planner tasks...')
        
        task_templates = [
            {'title': 'Review client documentation', 'priority': TaskPriority.HIGH},
            {'title': 'Prepare monthly financial report', 'priority': TaskPriority.HIGH},
            {'title': 'Follow up on payment reminder', 'priority': TaskPriority.MEDIUM},
            {'title': 'Schedule quarterly review meeting', 'priority': TaskPriority.MEDIUM},
            {'title': 'Update project timeline', 'priority': TaskPriority.MEDIUM},
            {'title': 'Send tax filing confirmation', 'priority': TaskPriority.HIGH},
            {'title': 'Review and approve invoices', 'priority': TaskPriority.MEDIUM},
            {'title': 'Prepare campaign presentation', 'priority': TaskPriority.HIGH},
            {'title': 'Compile compliance checklist', 'priority': TaskPriority.CRITICAL},
            {'title': 'Draft press release', 'priority': TaskPriority.MEDIUM},
            {'title': 'Organize client meeting notes', 'priority': TaskPriority.LOW},
            {'title': 'Update CRM records', 'priority': TaskPriority.LOW},
            {'title': 'Review contract amendments', 'priority': TaskPriority.HIGH},
            {'title': 'Prepare board presentation', 'priority': TaskPriority.CRITICAL},
            {'title': 'Complete expense report', 'priority': TaskPriority.MEDIUM},
        ]
        
        statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE]
        
        for i in range(count):
            template = random.choice(task_templates)
            due_date = timezone.now().date() + timedelta(days=random.randint(-5, 30))
            
            task = PlannerTask.objects.create(
                title=f"{template['title']} - {fake.company()[:20]}",
                description=fake.paragraph(nb_sentences=3),
                created_by=user,
                assigned_to=user,
                status=random.choice(statuses),
                priority=template['priority'],
                due_date=due_date,
                ai_generated=random.choice([True, False]),
                ai_priority_score=random.uniform(30, 90),
                ai_reasoning='Auto-prioritized based on due date and importance',
                related_client=random.choice(companies) if companies else None,
                related_project=random.choice(projects) if projects else None,
                tags=random.sample(['audit', 'tax', 'client', 'urgent', 'follow-up', 'review'], 2),
            )
            
            if task.status == TaskStatus.DONE:
                task.completed_at = timezone.now() - timedelta(days=random.randint(1, 10))
                task.save()
        
        self.stdout.write(f'  Created {count} planner tasks')
        self.stdout.write(f'  Total tasks: {PlannerTask.objects.count()}')

    def seed_schedule_events(self, user):
        """Create demo schedule events"""
        self.stdout.write('Seeding schedule events...')
        
        events_data = [
            {'title': 'Weekly Team Standup', 'duration': 30, 'recurring': True},
            {'title': 'Client Quarterly Review', 'duration': 60, 'recurring': False},
            {'title': 'Board Meeting', 'duration': 120, 'recurring': False},
            {'title': 'Tax Filing Deadline Review', 'duration': 45, 'recurring': False},
            {'title': 'Project Kickoff Meeting', 'duration': 60, 'recurring': False},
            {'title': 'Training Session: New Software', 'duration': 90, 'recurring': False},
            {'title': 'Monthly Financial Review', 'duration': 60, 'recurring': True},
            {'title': 'IPO Preparation Call', 'duration': 45, 'recurring': False},
        ]
        
        for event_data in events_data:
            start_time = timezone.now() + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(9, 16)
            )
            
            event = ScheduleEvent.objects.create(
                title=event_data['title'],
                description=fake.paragraph(nb_sentences=2),
                location=random.choice(['Conference Room A', 'Virtual - Zoom', 'Office 3F', 'Client Site']),
                organizer=user,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=event_data['duration']),
                is_recurring=event_data['recurring'],
                meeting_type=random.choice(['zoom', 'teams', 'in-person']),
                ai_generated=random.choice([True, False]),
            )
        
        self.stdout.write(f'  Created {len(events_data)} schedule events')
        self.stdout.write(f'  Total events: {ScheduleEvent.objects.count()}')

    def seed_brainstorm_sessions(self, user, companies, campaigns):
        """Create demo brainstorm sessions"""
        self.stdout.write('Seeding brainstorm sessions...')
        
        sessions_data = [
            {
                'title': 'Q1 Marketing Campaign Ideas',
                'type': 'IDEA_GENERATOR',
                'prompt': 'Generate creative marketing ideas for Q1 2025',
                'ideas': ['Social media campaign', 'Influencer partnership', 'Virtual event', 'Email series']
            },
            {
                'title': 'Product Launch Campaign Breakdown',
                'type': 'CAMPAIGN_BREAKDOWN',
                'prompt': 'Break down the product launch campaign into phases',
                'ideas': ['Pre-launch teaser', 'Launch event', 'Post-launch follow-up', 'Customer testimonials']
            },
            {
                'title': 'Market Analysis: FinTech Sector',
                'type': 'MARKET_ANALYSIS',
                'prompt': 'Analyze the FinTech market in Hong Kong',
                'ideas': ['Competitor landscape', 'Market trends', 'Opportunity areas', 'Risk factors']
            },
            {
                'title': 'Investor Pitch Preparation',
                'type': 'PITCH_WRITER',
                'prompt': 'Create a compelling investor pitch',
                'ideas': ['Problem statement', 'Solution overview', 'Market size', 'Financial projections']
            },
            {
                'title': '2025 Strategic Planning',
                'type': 'STRATEGY',
                'prompt': 'Develop strategic initiatives for 2025',
                'ideas': ['Market expansion', 'Product development', 'Team growth', 'Technology upgrade']
            },
        ]
        
        for data in sessions_data:
            session = BrainstormSession.objects.create(
                title=data['title'],
                session_type=data['type'],
                prompt=data['prompt'],
                created_by=user,
                related_campaign=random.choice(campaigns) if campaigns else None,
                related_client=random.choice(companies) if companies else None,
                ai_response=f"Generated {len(data['ideas'])} ideas for your {data['type']} session.",
                ai_structured_output={'ideas_count': len(data['ideas'])},
            )
            
            for idea_content in data['ideas']:
                BrainstormIdea.objects.create(
                    session=session,
                    content=idea_content,
                    category=data['type'],
                    rating=random.randint(1, 5),
                    is_selected=random.choice([True, False]),
                )
        
        self.stdout.write(f'  Created {len(sessions_data)} brainstorm sessions')
        self.stdout.write(f'  Total sessions: {BrainstormSession.objects.count()}')
        self.stdout.write(f'  Total ideas: {BrainstormIdea.objects.count()}')

    def seed_brainstorm_meetings(self, user, companies, campaigns):
        """Create demo brainstorm meetings with participants"""
        self.stdout.write('Seeding brainstorm meetings...')
        
        # Get some users for participants
        users = list(User.objects.filter(is_active=True)[:10])
        if not users:
            users = [user]
        
        meetings_data = [
            {
                'title': 'Q1 2025 Marketing Strategy Brainstorm',
                'description': '團隊腦力激盪會議，討論2025年第一季度的市場營銷策略',
                'meeting_type': 'IN_PERSON',
                'location': 'Conference Room A - 3/F',
                'status': MeetingStatus.COMPLETED,
                'agenda': '''1. 回顧2024年營銷成效
2. 討論目標客戶群體
3. 腦力激盪：新渠道開發
4. 預算分配討論
5. 行動計劃制定''',
                'objectives': ['確定Q1營銷目標', '識別新機會', '分配資源'],
                'ideas': [
                    {'content': '開發短影片營銷內容', 'author': 'Marketing Team', 'votes': 5},
                    {'content': '與行業KOL合作推廣', 'author': 'PR Team', 'votes': 3},
                    {'content': '舉辦線上研討會', 'author': 'Sales Team', 'votes': 4},
                    {'content': '優化社交媒體廣告投放', 'author': 'Digital Team', 'votes': 2},
                ],
                'action_items': [
                    {'task': '準備KOL合作提案', 'assignee': 'Marketing Manager', 'deadline': '2025-01-15'},
                    {'task': '設計研討會內容', 'assignee': 'Content Team', 'deadline': '2025-01-20'},
                ],
                'decisions_made': ['確定使用短影片策略', '預算增加20%投放數字廣告'],
                'participant_count': 8,
                'days_offset': -5,
                'duration_hours': 2,
            },
            {
                'title': '新產品發布會議',
                'description': '討論即將推出的新產品發布計劃和策略',
                'meeting_type': 'HYBRID',
                'location': 'Board Room + Zoom',
                'meeting_link': 'https://zoom.us/j/123456789',
                'status': MeetingStatus.COMPLETED,
                'agenda': '''1. 產品功能介紹
2. 目標市場分析
3. 發布時間線
4. 媒體策略
5. Q&A''',
                'objectives': ['確定發布日期', '分配任務', '準備媒體資料'],
                'ideas': [
                    {'content': '舉辦線上發布會', 'author': 'Events Team', 'votes': 6},
                    {'content': '準備新聞稿', 'author': 'PR Team', 'votes': 4},
                    {'content': '建立產品落地頁', 'author': 'Web Team', 'votes': 5},
                ],
                'action_items': [
                    {'task': '完成新聞稿初稿', 'assignee': 'PR Manager', 'deadline': '2025-01-10'},
                    {'task': '設計落地頁', 'assignee': 'Design Team', 'deadline': '2025-01-12'},
                ],
                'decisions_made': ['發布日期定為2月1日', '線上線下同步發布'],
                'participant_count': 12,
                'days_offset': -3,
                'duration_hours': 3,
            },
            {
                'title': '客戶服務改進研討會',
                'description': '分析客戶反饋，討論服務改進方案',
                'meeting_type': 'ONLINE',
                'location': '',
                'meeting_link': 'https://teams.microsoft.com/l/meetup-join/123',
                'status': MeetingStatus.SCHEDULED,
                'agenda': '''1. 客戶滿意度調查結果
2. 常見問題分析
3. 改進建議討論
4. 培訓計劃''',
                'objectives': ['提高客戶滿意度', '減少投訴', '優化服務流程'],
                'ideas': [],
                'action_items': [],
                'decisions_made': [],
                'participant_count': 6,
                'days_offset': 3,
                'duration_hours': 1.5,
            },
            {
                'title': '技術架構討論會',
                'description': '討論系統升級和技術架構優化方案',
                'meeting_type': 'IN_PERSON',
                'location': 'Tech Lab - 5/F',
                'status': MeetingStatus.SCHEDULED,
                'agenda': '''1. 現有架構分析
2. 瓶頸識別
3. 解決方案討論
4. 實施計劃''',
                'objectives': ['優化系統性能', '提高可擴展性', '降低運維成本'],
                'ideas': [],
                'action_items': [],
                'decisions_made': [],
                'participant_count': 5,
                'days_offset': 7,
                'duration_hours': 2,
            },
            {
                'title': '年度戰略規劃會議',
                'description': '2025年度公司戰略規劃腦力激盪',
                'meeting_type': 'IN_PERSON',
                'location': 'Executive Board Room',
                'status': MeetingStatus.IN_PROGRESS,
                'agenda': '''1. 2024年度回顧
2. 市場趨勢分析
3. 競爭格局討論
4. 戰略方向制定
5. 資源配置''',
                'objectives': ['制定2025年戰略', '確定增長目標', '分配部門預算'],
                'ideas': [
                    {'content': '擴展東南亞市場', 'author': 'CEO', 'votes': 8},
                    {'content': '投資AI技術研發', 'author': 'CTO', 'votes': 7},
                    {'content': '建立戰略合作夥伴關係', 'author': 'BD Team', 'votes': 5},
                ],
                'action_items': [],
                'decisions_made': [],
                'participant_count': 10,
                'days_offset': 0,
                'duration_hours': 4,
            },
            {
                'title': '品牌重塑討論',
                'description': '探討公司品牌形象更新和市場定位',
                'meeting_type': 'HYBRID',
                'location': 'Marketing Office + Google Meet',
                'meeting_link': 'https://meet.google.com/abc-defg-hij',
                'status': MeetingStatus.POSTPONED,
                'agenda': '''1. 品牌現狀分析
2. 競品品牌研究
3. 新品牌方向討論
4. 視覺識別設計''',
                'objectives': ['更新品牌形象', '提高品牌認知度', '統一視覺識別'],
                'ideas': [
                    {'content': '設計新Logo', 'author': 'Design Lead', 'votes': 3},
                    {'content': '更新品牌色彩', 'author': 'Marketing', 'votes': 2},
                ],
                'action_items': [],
                'decisions_made': [],
                'participant_count': 7,
                'days_offset': 14,
                'duration_hours': 2,
            },
            {
                'title': 'IPO 準備會議',
                'description': '討論公司上市準備工作和時間表',
                'meeting_type': 'IN_PERSON',
                'location': 'Board Room - Confidential',
                'status': MeetingStatus.COMPLETED,
                'agenda': '''1. 上市時間表
2. 法律合規要求
3. 財務審計準備
4. 投資者關係策略''',
                'objectives': ['確定上市時間表', '識別合規要求', '準備財務文件'],
                'ideas': [
                    {'content': '聘請外部法律顧問', 'author': 'Legal Team', 'votes': 6},
                    {'content': '建立投資者關係網站', 'author': 'IR Team', 'votes': 4},
                    {'content': '準備招股書初稿', 'author': 'Finance', 'votes': 5},
                ],
                'action_items': [
                    {'task': '完成財務審計', 'assignee': 'CFO', 'deadline': '2025-03-01'},
                    {'task': '聘請承銷商', 'assignee': 'CEO', 'deadline': '2025-02-15'},
                ],
                'decisions_made': ['目標Q3完成上市', '選擇香港交易所'],
                'participant_count': 6,
                'days_offset': -10,
                'duration_hours': 3,
            },
            {
                'title': '團隊建設活動規劃',
                'description': '討論下季度團隊建設活動方案',
                'meeting_type': 'ONLINE',
                'location': '',
                'meeting_link': 'https://zoom.us/j/987654321',
                'status': MeetingStatus.SCHEDULED,
                'agenda': '''1. 預算討論
2. 活動類型選擇
3. 日期協調
4. 後勤安排''',
                'objectives': ['增強團隊凝聚力', '提高員工士氣', '促進跨部門合作'],
                'ideas': [],
                'action_items': [],
                'decisions_made': [],
                'participant_count': 4,
                'days_offset': 5,
                'duration_hours': 1,
            },
        ]
        
        for data in meetings_data:
            # Calculate meeting times
            base_time = timezone.now() + timedelta(days=data['days_offset'])
            scheduled_start = base_time.replace(hour=10, minute=0, second=0, microsecond=0)
            scheduled_end = scheduled_start + timedelta(hours=data['duration_hours'])
            
            # Set actual times for completed meetings
            actual_start = None
            actual_end = None
            if data['status'] == MeetingStatus.COMPLETED:
                actual_start = scheduled_start
                actual_end = scheduled_end
            elif data['status'] == MeetingStatus.IN_PROGRESS:
                actual_start = scheduled_start
            
            # Get a random company and campaign for relation
            company = random.choice(companies) if companies else None
            campaign = random.choice(campaigns) if campaigns else None
            
            meeting = BrainstormMeeting.objects.create(
                title=data['title'],
                description=data['description'],
                status=data['status'],
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                actual_start=actual_start,
                actual_end=actual_end,
                location=data['location'],
                meeting_link=data.get('meeting_link', ''),
                meeting_type=data['meeting_type'],
                agenda=data['agenda'],
                objectives=data['objectives'],
                meeting_notes=f"會議記錄：{data['title']}" if data['status'] == MeetingStatus.COMPLETED else '',
                summary=f"會議總結：{data['description']}" if data['status'] == MeetingStatus.COMPLETED else '',
                action_items=data['action_items'],
                decisions_made=data['decisions_made'],
                ideas_generated=[
                    {**idea, 'created_at': (timezone.now() - timedelta(days=abs(data['days_offset']))).isoformat()}
                    for idea in data['ideas']
                ],
                selected_ideas=[idea for idea in data['ideas'] if idea.get('votes', 0) >= 5],
                organizer=user,
                max_participants=data['participant_count'] + 5,
                related_client=company,
                related_campaign=campaign,
                tags=['brainstorm', data['meeting_type'].lower(), data['status'].lower()],
            )
            
            # Add organizer as participant
            BrainstormMeetingParticipant.objects.create(
                meeting=meeting,
                user=user,
                role=MeetingParticipantRole.ORGANIZER,
                status=MeetingParticipantStatus.ATTENDED if data['status'] == MeetingStatus.COMPLETED else MeetingParticipantStatus.ACCEPTED,
                joined_at=actual_start,
                left_at=actual_end,
                ideas_contributed=random.randint(1, 5) if data['status'] == MeetingStatus.COMPLETED else 0,
                votes_cast=random.randint(0, 3) if data['status'] == MeetingStatus.COMPLETED else 0,
            )
            
            # Add other participants
            participant_users = random.sample(users, min(data['participant_count'] - 1, len(users) - 1))
            roles = [MeetingParticipantRole.FACILITATOR, MeetingParticipantRole.PRESENTER, 
                     MeetingParticipantRole.PARTICIPANT, MeetingParticipantRole.NOTETAKER]
            
            for i, participant_user in enumerate(participant_users):
                if participant_user == user:
                    continue
                    
                # Determine status based on meeting status
                if data['status'] == MeetingStatus.COMPLETED:
                    p_status = MeetingParticipantStatus.ATTENDED
                    joined_at = actual_start + timedelta(minutes=random.randint(0, 10)) if actual_start else None
                    left_at = actual_end - timedelta(minutes=random.randint(0, 5)) if actual_end else None
                elif data['status'] == MeetingStatus.IN_PROGRESS:
                    p_status = random.choice([MeetingParticipantStatus.ACCEPTED, MeetingParticipantStatus.ATTENDED])
                    joined_at = actual_start + timedelta(minutes=random.randint(0, 10)) if actual_start else None
                    left_at = None
                else:
                    p_status = random.choice([MeetingParticipantStatus.INVITED, MeetingParticipantStatus.ACCEPTED, MeetingParticipantStatus.TENTATIVE])
                    joined_at = None
                    left_at = None
                
                BrainstormMeetingParticipant.objects.create(
                    meeting=meeting,
                    user=participant_user,
                    role=roles[i % len(roles)] if i < len(roles) else MeetingParticipantRole.PARTICIPANT,
                    status=p_status,
                    responded_at=timezone.now() - timedelta(days=random.randint(1, 7)) if p_status != MeetingParticipantStatus.INVITED else None,
                    joined_at=joined_at,
                    left_at=left_at,
                    ideas_contributed=random.randint(0, 3) if data['status'] == MeetingStatus.COMPLETED else 0,
                    votes_cast=random.randint(0, 5) if data['status'] == MeetingStatus.COMPLETED else 0,
                )
            
            # Add some external participants
            if random.random() < 0.3:  # 30% chance to have external participants
                external_count = random.randint(1, 3)
                for j in range(external_count):
                    BrainstormMeetingParticipant.objects.create(
                        meeting=meeting,
                        user=None,
                        is_external=True,
                        external_name=fake.name(),
                        external_email=fake.email(),
                        external_company=fake.company(),
                        role=MeetingParticipantRole.OBSERVER,
                        status=MeetingParticipantStatus.ACCEPTED if data['status'] != MeetingStatus.SCHEDULED else MeetingParticipantStatus.INVITED,
                    )
        
        self.stdout.write(f'  Created {len(meetings_data)} brainstorm meetings')
        self.stdout.write(f'  Total meetings: {BrainstormMeeting.objects.count()}')
        self.stdout.write(f'  Total participants: {BrainstormMeetingParticipant.objects.count()}')
