"""
Cleanup Tasks
==============
Periodic tasks for cleaning up old data.
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_task_results(days: int = 30):
    """
    Clean up old task results and logs.
    
    Args:
        days: Number of days to keep results (default: 30)
    
    Returns:
        dict: Cleanup statistics
    """
    from ai_assistants.models_tasks import AsyncTask
    from ai_assistants.models_feedback import AIResultLog
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Delete old completed/failed tasks
    old_tasks = AsyncTask.objects.filter(
        completed_at__lt=cutoff_date,
        status__in=['SUCCESS', 'FAILURE', 'REVOKED']
    )
    tasks_deleted = old_tasks.count()
    old_tasks.delete()
    
    # Delete old result logs (keep feedback-related ones longer)
    old_results = AIResultLog.objects.filter(
        created_at__lt=cutoff_date,
        feedback_count=0  # Only delete results without feedback
    )
    results_deleted = old_results.count()
    old_results.delete()
    
    logger.info(f"Cleanup completed: {tasks_deleted} tasks, {results_deleted} results deleted")
    
    return {
        'tasks_deleted': tasks_deleted,
        'results_deleted': results_deleted,
        'cutoff_date': cutoff_date.isoformat(),
    }


@shared_task
def cleanup_orphaned_files():
    """
    Clean up orphaned task result files.
    """
    import os
    from django.conf import settings
    
    media_root = getattr(settings, 'MEDIA_ROOT', '/media')
    task_results_dir = os.path.join(media_root, 'task_results')
    
    if not os.path.exists(task_results_dir):
        return {'files_deleted': 0}
    
    from ai_assistants.models_tasks import AsyncTask
    
    # Get all file paths in database
    db_files = set(
        AsyncTask.objects.exclude(result_file='')
        .values_list('result_file', flat=True)
    )
    
    files_deleted = 0
    for filename in os.listdir(task_results_dir):
        file_path = os.path.join('task_results', filename)
        if file_path not in db_files:
            try:
                os.remove(os.path.join(task_results_dir, filename))
                files_deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete orphaned file {filename}: {e}")
    
    return {'files_deleted': files_deleted}
