# Generated manually for performance optimization
# 手動生成的性能優化遷移

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add database indexes for frequently queried fields.
    為常用查詢欄位添加資料庫索引。
    
    These indexes improve query performance for:
    - Status filtering
    - Date range queries
    - User/company lookups
    - Foreign key joins
    """

    dependencies = [
        ('accounting', '0001_initial'),
    ]

    operations = [
        # Invoice indexes
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['status'],
                name='acc_invoice_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['created_at'],
                name='acc_invoice_created_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['issue_date'],
                name='acc_invoice_issue_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['invoice_type', 'status'],
                name='acc_invoice_type_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['contact', 'status'],
                name='acc_invoice_contact_status_idx'
            ),
        ),
        
        # InvoiceLine indexes
        migrations.AddIndex(
            model_name='invoiceline',
            index=models.Index(
                fields=['invoice'],
                name='acc_invline_invoice_idx'
            ),
        ),
        
        # Payment indexes
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['status'],
                name='acc_payment_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['date'],
                name='acc_payment_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['created_at'],
                name='acc_payment_created_idx'
            ),
        ),
        
        # Contact indexes
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(
                fields=['contact_type'],
                name='acc_contact_type_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(
                fields=['company_name'],
                name='acc_contact_company_idx'
            ),
        ),
        
        # JournalEntry indexes
        migrations.AddIndex(
            model_name='journalentry',
            index=models.Index(
                fields=['status'],
                name='acc_je_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='journalentry',
            index=models.Index(
                fields=['date'],
                name='acc_je_entry_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='journalentry',
            index=models.Index(
                fields=['created_at'],
                name='acc_je_created_idx'
            ),
        ),
        
        # Account indexes
        migrations.AddIndex(
            model_name='account',
            index=models.Index(
                fields=['account_type'],
                name='acc_account_type_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(
                fields=['is_active'],
                name='acc_account_active_idx'
            ),
        ),
        
        # Expense indexes  
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(
                fields=['status'],
                name='acc_expense_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(
                fields=['date'],
                name='acc_expense_date_idx'
            ),
        ),
    ]
