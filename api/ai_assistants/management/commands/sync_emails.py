"""
Management command to sync emails from IMAP for all active accounts.

Usage:
    python manage.py sync_emails
    python manage.py sync_emails --account-id=<uuid>
    python manage.py sync_emails --limit=100
    
Can be run as a scheduled task (cron job, Celery beat, etc.)
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from ai_assistants.models import EmailAccount
from ai_assistants.services.email_service import sync_emails_for_account

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync emails from IMAP servers for all active email accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=str,
            help='Sync only this specific account (UUID)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum emails to fetch per account (default: 50)',
        )
        parser.add_argument(
            '--skip-demo',
            action='store_true',
            help='Skip demo accounts',
        )

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        limit = options.get('limit', 50)
        skip_demo = options.get('skip_demo', False)
        
        # Get accounts to sync
        queryset = EmailAccount.objects.filter(is_active=True)
        
        if account_id:
            queryset = queryset.filter(id=account_id)
            if not queryset.exists():
                raise CommandError(f'Account with ID {account_id} not found')
        
        if skip_demo:
            queryset = queryset.filter(is_demo=False)
        
        accounts = list(queryset)
        
        if not accounts:
            self.stdout.write(self.style.WARNING('No accounts to sync'))
            return
        
        self.stdout.write(f'Syncing {len(accounts)} account(s)...')
        
        total_stats = {
            'accounts': 0,
            'fetched': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
        }
        
        for account in accounts:
            self.stdout.write(f'  Syncing: {account.email_address}')
            
            try:
                result = sync_emails_for_account(account, limit=limit)
                
                total_stats['accounts'] += 1
                total_stats['fetched'] += result.get('fetched', 0)
                total_stats['created'] += result.get('created', 0)
                total_stats['updated'] += result.get('updated', 0)
                total_stats['errors'] += result.get('errors', 0)
                
                self.stdout.write(
                    f'    Fetched: {result.get("fetched", 0)}, '
                    f'Created: {result.get("created", 0)}, '
                    f'Updated: {result.get("updated", 0)}, '
                    f'Errors: {result.get("errors", 0)}'
                )
                
            except Exception as e:
                total_stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'    Error: {str(e)}')
                )
                logger.error(f'Failed to sync account {account.email_address}: {e}', exc_info=True)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Sync complete!\n'
            f'  Accounts: {total_stats["accounts"]}\n'
            f'  Emails fetched: {total_stats["fetched"]}\n'
            f'  Emails created: {total_stats["created"]}\n'
            f'  Emails updated: {total_stats["updated"]}\n'
            f'  Errors: {total_stats["errors"]}'
        ))
