"""
Celery Configuration
====================
Configure Celery for async task processing (OCR, report generation, etc.)
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Create Celery app
app = Celery('wisematic_erp')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Configuration
app.conf.update(
    # Broker settings (Redis default)
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,  # Track when tasks start
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Rate limiting
    task_annotations={
        'ai_assistants.tasks.ocr_tasks.*': {'rate_limit': '10/m'},
        'ai_assistants.tasks.report_tasks.*': {'rate_limit': '5/m'},
    },
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        'cleanup-old-results': {
            'task': 'ai_assistants.tasks.cleanup_tasks.cleanup_old_task_results',
            'schedule': 3600.0,  # Every hour
        },
    },
)

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
