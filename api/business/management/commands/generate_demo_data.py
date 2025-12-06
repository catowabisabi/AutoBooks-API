"""
Generate Demo Data for All Company Types
=========================================
Creates realistic demo data for:
- ZL CPA (Accounting Firm)
- BMI Innovation PR (Financial PR)
- BMI IPO (IPO Advisory)
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models as db_models
from business.models import (
    Company, AuditProject, TaxReturnCase, BillableHour, Revenue,
    ListedClient, Announcement, MediaCoverage, IPOMandate,
    ActiveEngagement, ServiceRevenue, ClientPerformance,
    ClientIndustry, MediaSentimentRecord, RevenueTrend,
    IPOTimelineProgress, IPODealFunnel, IPODealSize, BusinessPartner
)
from users.models import User


class Command(BaseCommand):
    help = 'Generate demo data for all three company types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Generating demo data...')
        
        # Get or create demo companies
        zl_cpa = self.get_or_create_company('ZL CPA', 'accounting')
        bmi_pr = self.get_or_create_company('BMI Innovation (PR)', 'financial-pr')
        bmi_ipo = self.get_or_create_company('BMI (IPO)', 'ipo-advisory')
        
        # Generate data for each company
        self.generate_zl_cpa_data(zl_cpa)
        self.generate_bmi_pr_data(bmi_pr)
        self.generate_bmi_ipo_data(bmi_ipo)
        
        # Generate shared data
        self.generate_engagements_for_all([zl_cpa, bmi_pr, bmi_ipo])
        self.generate_revenue_trends([zl_cpa, bmi_pr, bmi_ipo])
        
        # Generate IPO-specific data (for ipo-advisory dashboard charts)
        self.generate_ipo_timeline_progress(bmi_ipo)
        self.generate_ipo_deal_funnel(bmi_ipo)
        self.generate_ipo_deal_size(bmi_ipo)
        
        # Generate business partners for all companies
        self.generate_business_partners([zl_cpa, bmi_pr, bmi_ipo])
        
        self.stdout.write(self.style.SUCCESS('Demo data generated successfully!'))

    def clear_data(self):
        """Clear existing demo data"""
        AuditProject.objects.all().delete()
        TaxReturnCase.objects.all().delete()
        BillableHour.objects.all().delete()
        Revenue.objects.all().delete()
        ListedClient.objects.all().delete()
        Announcement.objects.all().delete()
        MediaCoverage.objects.all().delete()
        IPOMandate.objects.all().delete()
        ActiveEngagement.objects.all().delete()
        ServiceRevenue.objects.all().delete()
        ClientPerformance.objects.all().delete()
        MediaSentimentRecord.objects.all().delete()
        RevenueTrend.objects.all().delete()
        # New models
        IPOTimelineProgress.objects.all().delete()
        IPODealFunnel.objects.all().delete()
        IPODealSize.objects.all().delete()
        BusinessPartner.objects.all().delete()

    def get_or_create_company(self, name, company_type):
        """Get or create a company"""
        company, created = Company.objects.get_or_create(
            name=name,
            defaults={
                'industry': company_type,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f'Created company: {name}')
        return company

    def get_random_user(self):
        """Get a random user or None"""
        users = User.objects.filter(is_active=True)
        return random.choice(list(users)) if users.exists() else None

    # =================================================================
    # ZL CPA Data Generation
    # =================================================================
    def generate_zl_cpa_data(self, company):
        """Generate data for ZL CPA (Accounting Firm)"""
        self.stdout.write(f'Generating ZL CPA data...')
        
        # Create client companies for audits
        client_companies = []
        hk_company_names = [
            'Pacific Trading Ltd.', 'Golden Dragon Holdings', 'Asia Tech Solutions',
            'Sunshine Property Management', 'Eastern Import Export Co.', 'Fortune Investment Ltd.',
            'Wing Tai Manufacturing', 'Cheung Kong Logistics', 'New World Services',
            'Henderson Properties', 'Swire Pacific Ltd.', 'Cathay Group Holdings',
            'HSBC Insurance HK', 'Bank of East Asia', 'Standard Chartered HK',
            'MTR Corporation', 'CLP Holdings', 'HK Electric',
            'Li & Fung Ltd.', 'Esprit Holdings', 'Giordano International',
            'Sa Sa International', 'Emperor Group', 'Galaxy Entertainment',
            'Melco Resorts', 'MGM China', 'Wynn Macau',
            'China Resources', 'CITIC Pacific', 'China Overseas Land',
            'Kerry Properties', 'Hang Lung Properties', 'Sino Land',
            'Great Eagle Holdings', 'Hysan Development', 'Wharf Holdings',
            'Wheelock Properties', 'Shun Tak Holdings', 'NWS Holdings',
            'PCCW Ltd.', 'HKT Trust', 'SmarTone Telecom'
        ]
        
        for name in hk_company_names[:35]:
            client, _ = Company.objects.get_or_create(
                name=name,
                defaults={
                    'industry': random.choice(['Manufacturing', 'Property', 'Finance', 'Retail', 'Services']),
                    'is_active': True
                }
            )
            client_companies.append(client)
        
        # Generate Audit Projects (32 in progress as per demo data)
        audit_types = ['FINANCIAL', 'TAX', 'INTERNAL', 'COMPLIANCE']
        statuses = ['NOT_STARTED', 'PLANNING', 'FIELDWORK', 'REVIEW', 'REPORTING', 'COMPLETED']
        
        for i, client in enumerate(client_companies):
            # Create 1-2 audits per client
            num_audits = random.randint(1, 2)
            for j in range(num_audits):
                status = random.choices(
                    statuses,
                    weights=[5, 10, 25, 20, 15, 25]  # More in fieldwork/review
                )[0]
                
                AuditProject.objects.create(
                    company=client,
                    fiscal_year=f'FY{2024 if random.random() > 0.3 else 2023}',
                    audit_type=random.choice(audit_types),
                    progress=random.randint(10, 95) if status != 'COMPLETED' else 100,
                    status=status,
                    start_date=timezone.now().date() - timedelta(days=random.randint(30, 180)),
                    deadline=timezone.now().date() + timedelta(days=random.randint(30, 120)),
                    assigned_to=self.get_random_user(),
                    budget_hours=Decimal(str(random.randint(100, 500))),
                    actual_hours=Decimal(str(random.randint(50, 400))),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {AuditProject.objects.count()} audit projects')
        
        # Generate Tax Return Cases (156 pending as per demo data)
        tax_types = ['PROFITS_TAX', 'SALARIES_TAX', 'PROPERTY_TAX', 'STAMP_DUTY']
        tax_statuses = ['PENDING', 'IN_PROGRESS', 'UNDER_REVIEW', 'SUBMITTED', 'ACCEPTED']
        
        for client in client_companies:
            num_tax_returns = random.randint(2, 6)
            for _ in range(num_tax_returns):
                status = random.choices(
                    tax_statuses,
                    weights=[30, 25, 15, 15, 15]  # More pending
                )[0]
                
                TaxReturnCase.objects.create(
                    company=client,
                    tax_year=f'{random.choice([2023, 2024])}',
                    tax_type=random.choice(tax_types),
                    progress=random.randint(0, 90) if status != 'ACCEPTED' else 100,
                    status=status,
                    deadline=timezone.now().date() + timedelta(days=random.randint(-30, 90)),
                    handler=self.get_random_user(),
                    tax_amount=Decimal(str(random.randint(50000, 5000000))),
                    documents_received=random.choice([True, True, True, False]),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {TaxReturnCase.objects.count()} tax return cases')
        
        # Generate Billable Hours (2847 hours MTD as per demo data)
        roles = ['CLERK', 'ACCOUNTANT', 'MANAGER', 'DIRECTOR', 'PARTNER']
        base_rates = {
            'CLERK': Decimal('200'),
            'ACCOUNTANT': Decimal('500'),
            'MANAGER': Decimal('800'),
            'DIRECTOR': Decimal('1200'),
            'PARTNER': Decimal('1800')
        }
        
        for day in range(30):  # Last 30 days
            date = timezone.now().date() - timedelta(days=day)
            # Generate 10-20 billable hour entries per day
            for _ in range(random.randint(10, 20)):
                role = random.choices(
                    roles,
                    weights=[20, 35, 25, 15, 5]
                )[0]
                hours = Decimal(str(random.randint(2, 10)))
                
                BillableHour.objects.create(
                    employee=self.get_random_user(),
                    company=random.choice(client_companies),
                    role=role,
                    base_hourly_rate=base_rates[role],
                    hourly_rate_multiplier=Decimal('1.0'),
                    date=date,
                    actual_hours=hours,
                    description=f'{role} work on audit/tax project',
                    is_billable=True,
                    is_invoiced=random.choice([True, False]),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {BillableHour.objects.count()} billable hour entries')
        
        # Generate Revenue records
        revenue_statuses = ['PENDING', 'PARTIAL', 'RECEIVED', 'OVERDUE']
        
        for client in client_companies:
            num_revenues = random.randint(2, 5)
            for i in range(num_revenues):
                total = Decimal(str(random.randint(50000, 500000)))
                status = random.choices(
                    revenue_statuses,
                    weights=[25, 20, 40, 15]
                )[0]
                
                if status == 'RECEIVED':
                    received = total
                elif status == 'PARTIAL':
                    received = total * Decimal(str(random.uniform(0.3, 0.7)))
                else:
                    received = Decimal('0')
                
                Revenue.objects.create(
                    company=client,
                    invoice_number=f'INV-{2024}{str(i+1).zfill(4)}',
                    description=f'Professional services - {random.choice(["Audit", "Tax", "Advisory"])}',
                    total_amount=total,
                    received_amount=received,
                    status=status,
                    invoice_date=timezone.now().date() - timedelta(days=random.randint(0, 90)),
                    due_date=timezone.now().date() + timedelta(days=random.randint(-30, 60)),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {Revenue.objects.count()} revenue records')
        
        # Generate Service Revenue breakdown (for pie chart)
        self.generate_service_revenues(company)

    # =================================================================
    # BMI PR Data Generation
    # =================================================================
    def generate_bmi_pr_data(self, company):
        """Generate data for BMI Innovation PR (Financial PR)"""
        self.stdout.write(f'Generating BMI PR data...')
        
        # Create Listed Clients (52 as per demo data)
        listed_companies = [
            ('China Biotech Holdings', '2389.HK', 'Healthcare'),
            ('Pacific Real Estate', '1688.HK', 'Property'),
            ('Dragon FinTech Ltd.', '8888.HK', 'Technology'),
            ('Golden Mining Resources', '0888.HK', 'Mining'),
            ('Asia Green Energy', '6128.HK', 'Energy'),
            ('New Century Healthcare', '1518.HK', 'Healthcare'),
            ('Evergreen Properties', '3383.HK', 'Property'),
            ('Smart City Holdings', '2288.HK', 'Technology'),
            ('Blue Ocean Shipping', '0316.HK', 'Logistics'),
            ('Silver Star Entertainment', '0970.HK', 'Entertainment'),
            ('Phoenix Media Group', '1100.HK', 'Media'),
            ('Eastern Pharmaceutical', '1177.HK', 'Healthcare'),
            ('Green Valley Agriculture', '1357.HK', 'Agriculture'),
            ('Metro Transit Ltd.', '0066.HK', 'Transport'),
            ('Crown Finance', '1878.HK', 'Finance'),
            ('Sapphire Technology', '2382.HK', 'Technology'),
            ('Diamond Retail', '1929.HK', 'Retail'),
            ('Ruby Hotels', '0069.HK', 'Hospitality'),
            ('Pearl Education', '1565.HK', 'Education'),
            ('Jade Insurance', '2628.HK', 'Insurance'),
            ('Amber Resources', '1818.HK', 'Mining'),
            ('Crystal Clean Energy', '0958.HK', 'Energy'),
            ('Platinum Automotive', '0489.HK', 'Automotive'),
            ('Bronze Manufacturing', '2689.HK', 'Manufacturing'),
            ('Copper Networks', '0762.HK', 'Telecom'),
            ('Iron Construction', '1800.HK', 'Construction'),
            ('Steel Industries', '0042.HK', 'Industrial'),
            ('Zinc Chemicals', '0867.HK', 'Chemicals'),
            ('Nickel Foods', '0151.HK', 'Food & Beverage'),
            ('Cobalt Textiles', '2313.HK', 'Textiles'),
            ('Titanium Aerospace', '0753.HK', 'Aerospace'),
            ('Chromium Electronics', '0992.HK', 'Electronics'),
            ('Molybdenum Mining', '3993.HK', 'Mining'),
            ('Tungsten Power', '0836.HK', 'Utilities'),
            ('Vanadium Ventures', '1088.HK', 'Investments'),
            ('Zirconium Group', '0027.HK', 'Conglomerate'),
            ('Magnesium Motors', '0175.HK', 'Automotive'),
            ('Lithium Tech', '1211.HK', 'Technology'),
            ('Sodium Pharma', '1093.HK', 'Healthcare'),
            ('Calcium Healthcare', '1099.HK', 'Healthcare'),
            ('Potassium Foods', '0220.HK', 'Food'),
            ('Chlorine Chemicals', '0297.HK', 'Chemicals'),
            ('Argon Gas', '2688.HK', 'Energy'),
            ('Neon Lighting', '1098.HK', 'Consumer'),
            ('Xenon Tech', '0241.HK', 'Technology'),
            ('Krypton Security', '0363.HK', 'Services'),
            ('Radon Properties', '0101.HK', 'Property'),
            ('Helium Networks', '0728.HK', 'Telecom'),
            ('Hydrogen Energy', '3800.HK', 'Energy'),
            ('Oxygen Medical', '1666.HK', 'Healthcare'),
            ('Nitrogen Agriculture', '0910.HK', 'Agriculture'),
            ('Carbon Trading', '0386.HK', 'Trading'),
        ]
        
        listed_clients = []
        for name, stock_code, sector in listed_companies:
            client_company, _ = Company.objects.get_or_create(
                name=name,
                defaults={'industry': sector, 'is_active': True}
            )
            
            lc = ListedClient.objects.create(
                company=client_company,
                stock_code=stock_code,
                exchange='HKEX',
                sector=sector,
                market_cap=Decimal(str(random.randint(500000000, 50000000000))),
                status=random.choices(
                    ['ACTIVE', 'INACTIVE', 'PROSPECT'],
                    weights=[70, 10, 20]
                )[0],
                contract_start_date=timezone.now().date() - timedelta(days=random.randint(180, 720)),
                annual_retainer=Decimal(str(random.randint(300000, 1200000))),
                is_active=True
            )
            listed_clients.append(lc)
        
        self.stdout.write(f'  Created {len(listed_clients)} listed clients')
        
        # Generate Announcements (28 this month as per demo data)
        announcement_types = [
            'RESULTS', 'INTERIM_RESULTS', 'PROFIT_WARNING', 'INSIDE_INFO',
            'NOTIFIABLE_TRANSACTION', 'DIVIDEND', 'AGM_EGM', 'OTHER'
        ]
        ann_statuses = ['DRAFT', 'IN_REVIEW', 'APPROVED', 'PUBLISHED']
        
        for client in listed_clients[:40]:  # Active clients
            num_announcements = random.randint(1, 4)
            for _ in range(num_announcements):
                publish_date = timezone.now().date() - timedelta(days=random.randint(0, 60))
                Announcement.objects.create(
                    listed_client=client,
                    announcement_type=random.choice(announcement_types),
                    title=f'{client.company.name} - {random.choice(["Annual Results", "Interim Results", "Major Transaction", "Dividend Declaration", "Board Changes"])}',
                    publish_date=publish_date,
                    deadline=publish_date - timedelta(days=3),
                    status=random.choices(
                        ann_statuses,
                        weights=[15, 15, 20, 50]
                    )[0],
                    handler=self.get_random_user(),
                    word_count=random.randint(2000, 15000),
                    languages='EN,TC',
                    is_active=True
                )
        
        self.stdout.write(f'  Created {Announcement.objects.count()} announcements')
        
        # Generate Media Coverage (94+ entries with 85% positive as per demo)
        media_outlets = [
            'South China Morning Post', 'Hong Kong Economic Times', 'Ming Pao',
            'Apple Daily', 'Oriental Daily', 'The Standard', 'HKEJ',
            'Sing Tao Daily', 'Reuters HK', 'Bloomberg HK', 'CNBC Asia',
            'AAStocks', 'ET Net', 'AASTV', 'Now Finance', 'TVB Finance',
            'iMoney', 'HKET', 'MetroDaily', 'Headline Daily'
        ]
        
        for client in listed_clients:
            num_coverage = random.randint(1, 5)
            for _ in range(num_coverage):
                sentiment = random.choices(
                    ['POSITIVE', 'NEUTRAL', 'NEGATIVE'],
                    weights=[70, 20, 10]  # 85% positive
                )[0]
                
                MediaCoverage.objects.create(
                    listed_client=client,
                    company=client.company,
                    title=f'{client.company.name} {random.choice(["reports strong growth", "announces expansion", "exceeds expectations", "maintains steady performance", "unveils new strategy"])}',
                    media_outlet=random.choice(media_outlets),
                    publish_date=timezone.now().date() - timedelta(days=random.randint(0, 90)),
                    sentiment=sentiment,
                    reach=random.randint(10000, 500000),
                    engagement=random.randint(100, 10000),
                    is_press_release=random.choice([True, False]),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {MediaCoverage.objects.count()} media coverage records')
        
        # Generate Media Sentiment Records (for sentiment analysis chart)
        self.generate_media_sentiment_records(company, listed_clients)
        
        # Generate Client Industries (for pie chart)
        self.generate_client_industries(company)

    def generate_media_sentiment_records(self, company, listed_clients):
        """Generate Media Sentiment Records for the sentiment analysis chart"""
        self.stdout.write(f'  Generating media sentiment records...')
        
        # Match the mock data structure from bar-graph.tsx
        # prSentimentData: positive, neutral, negative percentages over months
        sentiment_data = [
            {'month': 7, 'positive': 72, 'neutral': 20, 'negative': 8},
            {'month': 8, 'positive': 68, 'neutral': 25, 'negative': 7},
            {'month': 9, 'positive': 78, 'neutral': 18, 'negative': 4},
            {'month': 10, 'positive': 82, 'neutral': 15, 'negative': 3},
            {'month': 11, 'positive': 75, 'neutral': 20, 'negative': 5},
            {'month': 12, 'positive': 85, 'neutral': 12, 'negative': 3},
        ]
        
        year = 2024
        for data in sentiment_data:
            # Create one record per week in each month
            for week in range(4):
                period_date = timezone.now().replace(
                    year=year, 
                    month=data['month'], 
                    day=min(1 + week * 7, 28)
                ).date()
                
                # Convert percentages to counts (assume ~100 total articles per week)
                total_articles = random.randint(80, 120)
                positive = int(total_articles * data['positive'] / 100)
                neutral = int(total_articles * data['neutral'] / 100)
                negative = total_articles - positive - neutral
                
                MediaSentimentRecord.objects.create(
                    company=company,
                    period_date=period_date,
                    positive_count=positive + random.randint(-5, 5),
                    neutral_count=neutral + random.randint(-3, 3),
                    negative_count=max(0, negative + random.randint(-2, 2)),
                    total_reach=random.randint(500000, 2000000),
                    total_engagement=random.randint(10000, 50000),
                    sentiment_score=Decimal(str(data['positive'] - data['negative'])),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {MediaSentimentRecord.objects.filter(company=company).count()} media sentiment records')

    def generate_client_industries(self, company):
        """Generate Client Industry records for the industry distribution chart"""
        self.stdout.write(f'  Generating client industries...')
        
        # Match the mock data structure from pie-graph.tsx
        # prIndustryData: name, value (percentage), clients count
        industry_data = [
            {'name': 'Technology', 'code': 'TECH', 'clients': 28, 'revenue': 8500000, 'color': '#3b82f6'},
            {'name': 'Healthcare', 'code': 'HEALTH', 'clients': 18, 'revenue': 5200000, 'color': '#22c55e'},
            {'name': 'Finance', 'code': 'FIN', 'clients': 14, 'revenue': 4100000, 'color': '#a855f7'},
            {'name': 'Consumer', 'code': 'CONS', 'clients': 12, 'revenue': 3200000, 'color': '#f97316'},
            {'name': 'Industrial', 'code': 'IND', 'clients': 8, 'revenue': 2400000, 'color': '#06b6d4'},
            {'name': 'Property', 'code': 'PROP', 'clients': 10, 'revenue': 2800000, 'color': '#ec4899'},
            {'name': 'Energy', 'code': 'ENERGY', 'clients': 6, 'revenue': 1800000, 'color': '#eab308'},
            {'name': 'Other', 'code': 'OTHER', 'clients': 4, 'revenue': 900000, 'color': '#6b7280'},
        ]
        
        for data in industry_data:
            ClientIndustry.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': f'{data["name"]} sector clients',
                    'color': data['color'],
                    'client_count': data['clients'],
                    'total_revenue': Decimal(str(data['revenue'])),
                    'is_active': True
                }
            )
        
        self.stdout.write(f'  Created/Updated {ClientIndustry.objects.count()} client industries')

    # =================================================================
    # BMI IPO Data Generation
    # =================================================================
    def generate_bmi_ipo_data(self, company):
        """Generate data for BMI IPO (IPO Advisory)"""
        self.stdout.write(f'Generating BMI IPO data...')
        
        # Create IPO project companies
        ipo_companies = [
            ('TechVenture Holdings Ltd.', 'Technology', 6500000000),
            ('BioPharm Innovation Inc.', 'Healthcare', 5200000000),
            ('Smart Manufacturing Group', 'Industrial', 2800000000),
            ('Green Mobility Technologies', 'Automotive', 1500000000),
            ('Asia Digital Finance', 'Finance', 3200000000),
            ('Pacific Logistics Holdings', 'Logistics', 1800000000),
            ('CloudNet Solutions', 'Technology', 4500000000),
            ('MedTech Innovations', 'Healthcare', 3800000000),
            ('EcoEnergy Systems', 'Energy', 2200000000),
            ('DataStream Analytics', 'Technology', 2900000000),
            ('FinServ Group', 'Finance', 4100000000),
            ('PropTech Ventures', 'Property', 1600000000),
        ]
        
        stages = [
            'INITIAL_CONTACT', 'PITCH', 'MANDATE_WON', 'PREPARATION',
            'A1_FILING', 'HKEX_REVIEW', 'SFC_REVIEW', 'HEARING', 'ROADSHOW', 'LISTING'
        ]
        
        for name, sector, deal_size in ipo_companies:
            ipo_company, _ = Company.objects.get_or_create(
                name=name,
                defaults={'industry': sector, 'is_active': True}
            )
            
            stage = random.choices(
                stages,
                weights=[5, 10, 15, 20, 15, 10, 10, 5, 5, 5]
            )[0]
            
            fee_pct = Decimal(str(random.uniform(2.0, 4.0)))
            
            IPOMandate.objects.create(
                project_name=f'{name} IPO',
                company=ipo_company,
                stage=stage,
                target_exchange='HKEX',
                target_board=random.choice(['MAIN', 'GEM']),
                deal_size=Decimal(str(deal_size)),
                deal_size_category='LARGE' if deal_size > 2000000000 else 'MEDIUM',
                fee_percentage=fee_pct,
                estimated_fee=Decimal(str(deal_size)) * fee_pct / 100,
                probability=random.randint(40, 90),
                pitch_date=timezone.now().date() - timedelta(days=random.randint(90, 365)),
                mandate_date=timezone.now().date() - timedelta(days=random.randint(30, 180)) if stage not in ['INITIAL_CONTACT', 'PITCH'] else None,
                target_listing_date=timezone.now().date() + timedelta(days=random.randint(60, 365)),
                lead_partner=self.get_random_user(),
                is_sfc_approved=stage in ['HEARING', 'ROADSHOW', 'LISTING'],
                is_active=True
            )
        
        self.stdout.write(f'  Created {IPOMandate.objects.count()} IPO mandates')
    
    def generate_service_revenues(self, company):
        """Generate Service Revenue breakdown for the pie chart (accounting)"""
        self.stdout.write(f'  Generating service revenues...')
        
        # Match the mock data from pie-graph.tsx
        # accountingServiceData: service, label, revenue
        service_data = [
            {'type': 'IPO_ADVISORY', 'revenue': 4850000, 'hours': 1200},   # Audit Services
            {'type': 'FINANCIAL_PR', 'revenue': 2180000, 'hours': 650},    # Tax Advisory
            {'type': 'INVESTOR_RELATIONS', 'revenue': 1560000, 'hours': 420},  # Consulting
            {'type': 'TRANSACTION_SUPPORT', 'revenue': 890000, 'hours': 280},  # Compliance
            {'type': 'CRISIS_MANAGEMENT', 'revenue': 520000, 'hours': 150},
            {'type': 'ESG_ADVISORY', 'revenue': 380000, 'hours': 120},
        ]
        
        year = 2024
        for month in range(7, 13):  # Jul to Dec 2024
            for data in service_data:
                # Add some monthly variation
                variation = random.uniform(0.8, 1.2)
                monthly_revenue = int(data['revenue'] / 6 * variation)
                monthly_hours = int(data['hours'] / 6 * variation)
                
                ServiceRevenue.objects.update_or_create(
                    company=company,
                    service_type=data['type'],
                    period_year=year,
                    period_month=month,
                    defaults={
                        'amount': Decimal(str(monthly_revenue)),
                        'billable_hours': Decimal(str(monthly_hours)),
                        'is_active': True
                    }
                )
        
        self.stdout.write(f'  Created {ServiceRevenue.objects.filter(company=company).count()} service revenue records')

    # =================================================================
    # Shared Data Generation
    # =================================================================
    def generate_engagements_for_all(self, companies):
        """Generate Active Engagements for all companies"""
        self.stdout.write(f'Generating engagements for all companies...')
        
        engagement_types = ['RETAINER', 'PROJECT', 'AD_HOC']
        engagement_statuses = ['ACTIVE', 'PAUSED', 'COMPLETED']
        
        # Different engagement counts per company type
        engagement_counts = {
            'accounting': 45,      # ZL CPA: 45 active engagements
            'financial-pr': 38,    # BMI PR: 38 active engagements
            'ipo-advisory': 12,    # BMI IPO: 12 active engagements
        }
        
        for company in companies:
            company_type = company.industry
            count = engagement_counts.get(company_type, 20)
            
            # Get client companies based on type
            if company_type == 'accounting':
                clients = Company.objects.filter(audit_projects__isnull=False).distinct()[:count]
            elif company_type == 'financial-pr':
                clients = Company.objects.filter(listed_client_records__isnull=False).distinct()[:count]
            else:
                clients = Company.objects.filter(ipo_mandates__isnull=False).distinct()[:count]
            
            for client in clients:
                status = random.choices(
                    engagement_statuses,
                    weights=[60, 10, 30]
                )[0]
                
                ActiveEngagement.objects.create(
                    company=client,
                    title=f'{random.choice(["Annual", "Q4", "Special", "Ongoing"])} {random.choice(["Audit", "Advisory", "Compliance", "Retainer"])} Services',
                    engagement_type=random.choice(engagement_types),
                    status=status,
                    start_date=timezone.now().date() - timedelta(days=random.randint(30, 365)),
                    end_date=timezone.now().date() + timedelta(days=random.randint(30, 365)) if status != 'COMPLETED' else timezone.now().date() - timedelta(days=random.randint(1, 30)),
                    value=Decimal(str(random.randint(50000, 2000000))),
                    progress=random.randint(20, 90) if status == 'ACTIVE' else (100 if status == 'COMPLETED' else 0),
                    lead=self.get_random_user(),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {ActiveEngagement.objects.count()} engagements')
        
        # Generate ClientPerformance for each company's clients
        self.generate_client_performance()

    def generate_client_performance(self):
        """Generate Client Performance records"""
        self.stdout.write(f'Generating client performance records...')
        
        # Get companies that have been involved in projects
        companies = Company.objects.filter(
            db_models.Q(audit_projects__isnull=False) |
            db_models.Q(listed_client_records__isnull=False) |
            db_models.Q(ipo_mandates__isnull=False)
        ).distinct()[:50]
        
        for company in companies:
            # Generate performance for last 4 quarters
            for year in [2023, 2024]:
                for quarter in range(1, 5):
                    if year == 2024 and quarter > ((timezone.now().month - 1) // 3 + 1):
                        continue
                    
                    ClientPerformance.objects.create(
                        company=company,
                        period_year=year,
                        period_quarter=quarter,
                        revenue_generated=Decimal(str(random.randint(100000, 5000000))),
                        satisfaction_score=random.randint(70, 100),
                        projects_completed=random.randint(1, 5),
                        referrals_made=random.randint(0, 3),
                        response_time_hours=Decimal(str(random.uniform(2.0, 24.0))),
                        is_active=True
                    )
        
        self.stdout.write(f'  Created {ClientPerformance.objects.count()} client performance records')

    def generate_revenue_trends(self, companies):
        """Generate Revenue Trends for charts per company"""
        self.stdout.write(f'Generating revenue trends...')
        
        # Revenue multipliers per company type
        revenue_bases = {
            'accounting': 1000000,    # ZL CPA: ~HK$12.8M YTD
            'financial-pr': 1500000,  # BMI PR: ~HK$18.5M YTD
            'ipo-advisory': 3800000,  # BMI IPO: ~HK$45.8M YTD
        }
        
        for company in companies:
            base_revenue = revenue_bases.get(company.industry, 1000000)
            
            for year in [2023, 2024]:
                for month in range(1, 13):
                    if year == 2024 and month > timezone.now().month:
                        continue
                    
                    # Check if already exists for this company
                    if RevenueTrend.objects.filter(company=company, period_year=year, period_month=month).exists():
                        continue
                    
                    # Add seasonal variation
                    seasonal = 1.0 + (0.2 if month in [3, 4, 9, 10] else 0)  # Peak seasons
                    
                    RevenueTrend.objects.create(
                        company=company,
                        period_year=year,
                        period_month=month,
                        total_revenue=Decimal(str(int(base_revenue * seasonal * random.uniform(0.8, 1.2)))),
                        recurring_revenue=Decimal(str(int(base_revenue * 0.4 * random.uniform(0.9, 1.1)))),
                        project_revenue=Decimal(str(int(base_revenue * 0.6 * seasonal * random.uniform(0.7, 1.3)))),
                        new_clients=random.randint(2, 8),
                        churned_clients=random.randint(0, 2),
                        is_active=True
                    )
        
        self.stdout.write(f'  Created {RevenueTrend.objects.count()} revenue trend records')

    # =================================================================
    # IPO Timeline Progress Data Generation
    # =================================================================
    def generate_ipo_timeline_progress(self, company):
        """Generate IPO Timeline Progress data - matches bar-graph chart"""
        self.stdout.write(f'Generating IPO Timeline Progress data...')
        
        # Data matches frontend chart: IPO Completion Status
        # Due Diligence: 92%, Documentation: 78%, Regulatory: 45%, Marketing: 30%, Pricing: 15%
        phases_data = [
            ('due_diligence', 92, 'completed', -30),
            ('documentation', 78, 'in_progress', 15),
            ('regulatory', 45, 'in_progress', 45),
            ('marketing', 30, 'not_started', 75),
            ('pricing', 15, 'not_started', 90),
        ]
        
        for phase, progress, status, days_offset in phases_data:
            IPOTimelineProgress.objects.create(
                company=company,
                phase=phase,
                progress_percentage=progress,
                target_date=timezone.now().date() + timedelta(days=days_offset),
                status=status,
                is_active=True
            )
        
        self.stdout.write(f'  Created {IPOTimelineProgress.objects.count()} IPO timeline progress records')

    # =================================================================
    # IPO Deal Funnel Data Generation
    # =================================================================
    def generate_ipo_deal_funnel(self, company):
        """Generate IPO Deal Funnel data - matches area-graph chart"""
        self.stdout.write(f'Generating IPO Deal Funnel data...')
        
        # Data matches frontend chart: Deal Funnel
        # Leads: 45, Qualified: 28, Proposal: 18, Negotiation: 8, Closed: 3
        stages_data = [
            ('leads', 45, Decimal('0'), Decimal('250000000')),
            ('qualified', 28, Decimal('62.2'), Decimal('180000000')),
            ('proposal', 18, Decimal('64.3'), Decimal('120000000')),
            ('negotiation', 8, Decimal('44.4'), Decimal('80000000')),
            ('closed_won', 3, Decimal('37.5'), Decimal('45800000')),
        ]
        
        current_date = timezone.now().date().replace(day=1)
        
        for stage, count, conversion, value in stages_data:
            IPODealFunnel.objects.create(
                company=company,
                period_date=current_date,
                stage=stage,
                deal_count=count,
                conversion_rate=conversion,
                total_value=value,
                notes=f'Data for {stage} stage',
                is_active=True
            )
        
        self.stdout.write(f'  Created {IPODealFunnel.objects.count()} IPO deal funnel records')

    # =================================================================
    # IPO Deal Size Data Generation
    # =================================================================
    def generate_ipo_deal_size(self, company):
        """Generate IPO Deal Size data - matches pie-graph chart"""
        self.stdout.write(f'Generating IPO Deal Size data...')
        
        # Data matches frontend chart: Deal Size Distribution
        # Mega >$1B: 2 deals, Large $500M-1B: 4 deals, Mid $100M-500M: 12 deals, Small <$100M: 27 deals
        sizes_data = [
            ('mega', 2, Decimal('2500000000'), Decimal('1250000000')),     # >$1B
            ('large', 4, Decimal('2800000000'), Decimal('700000000')),     # $500M-1B
            ('mid', 12, Decimal('3200000000'), Decimal('266666667')),      # $100M-500M
            ('small', 27, Decimal('1800000000'), Decimal('66666667')),     # <$100M
        ]
        
        current_date = timezone.now().date().replace(day=1)
        
        for category, count, total, avg in sizes_data:
            IPODealSize.objects.create(
                company=company,
                period_date=current_date,
                size_category=category,
                deal_count=count,
                total_amount=total,
                avg_deal_size=avg,
                notes=f'Data for {category} category deals',
                is_active=True
            )
        
        self.stdout.write(f'  Created {IPODealSize.objects.count()} IPO deal size records')

    # =================================================================
    # Business Partner Data Generation
    # =================================================================
    def generate_business_partners(self, companies):
        """Generate Business Partner data - replaces Active Engagements concept"""
        self.stdout.write(f'Generating Business Partners data...')
        
        # Partner types matching frontend Recent Sales/Active Engagements section
        partners_data = {
            'accounting': [
                ('Elite Tax Advisory', 'consultant', 'active', 'Tax planning services', Decimal('250000'), 4.8),
                ('HK Audit Partners', 'vendor', 'active', 'Audit support services', Decimal('180000'), 4.5),
                ('Legal Eagles LLP', 'consultant', 'active', 'Corporate law advisory', Decimal('320000'), 4.9),
                ('Data Analytics Pro', 'provider', 'active', 'Data processing services', Decimal('95000'), 4.3),
            ],
            'financial-pr': [
                ('MediaMax HK', 'media', 'active', 'Press release distribution', Decimal('150000'), 4.7),
                ('KOL Connect', 'kol', 'active', 'Influencer marketing', Decimal('280000'), 4.6),
                ('PR Wire Global', 'provider', 'active', 'Global media coverage', Decimal('200000'), 4.4),
                ('Finance Weekly', 'media', 'active', 'Financial news publication', Decimal('85000'), 4.2),
                ('Social Buzz Agency', 'kol', 'active', 'Social media campaigns', Decimal('120000'), 4.5),
            ],
            'ipo-advisory': [
                ('Goldman Investment Banking', 'consultant', 'active', 'Underwriting services', Decimal('5000000'), 4.9),
                ('Legal & Corporate HK', 'vendor', 'active', 'Legal due diligence', Decimal('800000'), 4.8),
                ('Market Research Pro', 'provider', 'active', 'Market analysis', Decimal('350000'), 4.6),
                ('Investor Relations Co', 'provider', 'active', 'IR support services', Decimal('450000'), 4.7),
                ('Road Show Events', 'vendor', 'active', 'Event management', Decimal('280000'), 4.4),
                ('FinTech Analytics', 'consultant', 'active', 'Valuation services', Decimal('620000'), 4.8),
            ],
        }
        
        for company in companies:
            company_type = company.industry
            partners_list = partners_data.get(company_type, [])
            
            for name, p_type, status, desc, value, rating in partners_list:
                BusinessPartner.objects.create(
                    company=company,
                    name=name,
                    partner_type=p_type,
                    status=status,
                    contact_person=f'{name} Contact',
                    contact_email=f'contact@{name.lower().replace(" ", "")}.com',
                    contact_phone='+852 ' + ''.join([str(random.randint(0, 9)) for _ in range(8)]),
                    service_description=desc,
                    contract_start_date=timezone.now().date() - timedelta(days=random.randint(90, 365)),
                    contract_end_date=timezone.now().date() + timedelta(days=random.randint(180, 730)),
                    contract_value=value,
                    rating=Decimal(str(rating)),
                    is_active=True
                )
        
        self.stdout.write(f'  Created {BusinessPartner.objects.count()} business partner records')