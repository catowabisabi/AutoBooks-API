"""
Management command to seed subscription plans into the database.
Creates Free, Pro, and Pro+ Enterprise plans with bilingual names.
"""
from django.core.management.base import BaseCommand
from users.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed subscription plans (Free, Pro, Pro+ Enterprise)'

    def handle(self, *args, **options):
        plans_data = [
            {
                'plan_type': 'free',
                'name': 'Free',
                'name_en': 'Free',
                'name_zh': '免費版',
                'description': 'Get started with basic ERP features',
                'description_en': 'Get started with basic ERP features. Perfect for small businesses and individuals looking to explore our platform.',
                'description_zh': '開始使用基本的 ERP 功能。非常適合小型企業和個人探索我們的平台。',
                'price_monthly': 0,
                'price_yearly': 0,
                'currency': 'USD',
                'max_users': 1,
                'max_companies': 1,
                'max_storage_gb': 1,
                'max_documents': 50,
                'max_invoices_monthly': 10,
                'max_employees': 5,
                'max_projects': 2,
                'has_ai_assistant': False,
                'has_advanced_analytics': False,
                'has_custom_reports': False,
                'has_api_access': False,
                'has_priority_support': False,
                'has_sso': False,
                'has_audit_logs': False,
                'has_data_export': True,
                'has_multi_currency': False,
                'has_custom_branding': False,
                'ai_queries_monthly': 10,
                'rag_documents': 5,
                'is_active': True,
                'is_popular': False,
                'sort_order': 1,
            },
            {
                'plan_type': 'pro',
                'name': 'Pro',
                'name_en': 'Pro',
                'name_zh': '專業版',
                'description': 'Advanced features for growing businesses',
                'description_en': 'Advanced features for growing businesses. Includes AI assistant, advanced analytics, and priority support.',
                'description_zh': '為成長中的企業提供進階功能。包括 AI 助理、進階分析和優先支援。',
                'price_monthly': 29,
                'price_yearly': 290,
                'currency': 'USD',
                'max_users': 10,
                'max_companies': 3,
                'max_storage_gb': 50,
                'max_documents': 1000,
                'max_invoices_monthly': 100,
                'max_employees': 50,
                'max_projects': 20,
                'has_ai_assistant': True,
                'has_advanced_analytics': True,
                'has_custom_reports': True,
                'has_api_access': True,
                'has_priority_support': True,
                'has_sso': False,
                'has_audit_logs': True,
                'has_data_export': True,
                'has_multi_currency': True,
                'has_custom_branding': False,
                'ai_queries_monthly': 500,
                'rag_documents': 100,
                'is_active': True,
                'is_popular': True,
                'sort_order': 2,
            },
            {
                'plan_type': 'pro_plus',
                'name': 'Pro+ Enterprise',
                'name_en': 'Pro+ Enterprise',
                'name_zh': 'Pro+ 企業版',
                'description': 'Full enterprise solution with unlimited access',
                'description_en': 'Full enterprise solution with unlimited access. SSO, custom branding, dedicated support, and unlimited AI queries.',
                'description_zh': '完整的企業解決方案，無限制存取。包括 SSO 單一登入、自訂品牌、專屬支援和無限 AI 查詢。',
                'price_monthly': 99,
                'price_yearly': 990,
                'currency': 'USD',
                'max_users': 0,  # 0 = unlimited
                'max_companies': 0,  # 0 = unlimited
                'max_storage_gb': 500,
                'max_documents': 0,  # 0 = unlimited
                'max_invoices_monthly': 0,  # 0 = unlimited
                'max_employees': 0,  # 0 = unlimited
                'max_projects': 0,  # 0 = unlimited
                'has_ai_assistant': True,
                'has_advanced_analytics': True,
                'has_custom_reports': True,
                'has_api_access': True,
                'has_priority_support': True,
                'has_sso': True,
                'has_audit_logs': True,
                'has_data_export': True,
                'has_multi_currency': True,
                'has_custom_branding': True,
                'ai_queries_monthly': 0,  # 0 = unlimited
                'rag_documents': 0,  # 0 = unlimited
                'is_active': True,
                'is_popular': False,
                'sort_order': 3,
            },
        ]

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f'{action} plan: {plan.name} ({plan.plan_type})')
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded subscription plans!'))
