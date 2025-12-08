"""
Report Generation Tasks
========================
Async tasks for generating reports (PDF, Excel, etc.).
"""

import logging
import traceback
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def update_task_progress(task_id: str, progress: int, message: str = ''):
    """Update task progress in database"""
    try:
        from ai_assistants.models_tasks import AsyncTask
        task = AsyncTask.objects.get(celery_task_id=task_id)
        task.update_progress(progress, message)
    except Exception as e:
        logger.warning(f"Failed to update task progress: {e}")


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_report(self, report_type: str, user_id: int, params: dict = None):
    """
    Generate a single report.
    
    Args:
        report_type: Type of report (financial, hrms, project, etc.)
        user_id: ID of the user who requested the report
        params: Report parameters (date range, filters, format, etc.)
    
    Returns:
        dict: Report generation result with file path
    """
    from ai_assistants.models_tasks import AsyncTask
    
    params = params or {}
    task_id = self.request.id
    
    try:
        # Update task as started
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        # Phase 1: Gather data (20%)
        update_task_progress(task_id, 20, 'Gathering report data...')
        
        import time
        time.sleep(1)  # Simulate data gathering
        
        # Phase 2: Process data (40%)
        update_task_progress(task_id, 40, 'Processing data...')
        time.sleep(1)
        
        # Phase 3: Generate report (60%)
        update_task_progress(task_id, 60, 'Generating report...')
        time.sleep(2)
        
        # Phase 4: Format output (80%)
        output_format = params.get('format', 'pdf')
        update_task_progress(task_id, 80, f'Formatting {output_format.upper()} output...')
        time.sleep(1)
        
        # Phase 5: Save file (100%)
        file_name = f"report_{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        file_path = f"/media/reports/{file_name}"
        
        result = {
            'report_type': report_type,
            'file_name': file_name,
            'file_path': file_path,
            'file_size': 1024000,  # 1MB placeholder
            'format': output_format,
            'parameters': params,
            'generated_at': timezone.now().isoformat(),
            'download_url': f'/api/reports/download/{file_name}',
        }
        
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_success(result)
        except AsyncTask.DoesNotExist:
            pass
        
        return result
        
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        
        raise self.retry(exc=exc)


@shared_task(bind=True)
def generate_bulk_reports(self, report_configs: list, user_id: int):
    """
    Generate multiple reports in batch.
    
    Args:
        report_configs: List of report configurations
            [{'type': 'financial', 'params': {...}}, ...]
        user_id: ID of the user who requested the reports
    
    Returns:
        dict: Batch generation results
    """
    from ai_assistants.models_tasks import AsyncTask
    
    task_id = self.request.id
    total_reports = len(report_configs)
    results = []
    errors = []
    
    try:
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        for i, config in enumerate(report_configs):
            try:
                progress = int((i / total_reports) * 100)
                update_task_progress(
                    task_id, 
                    progress, 
                    f'Generating report {i+1} of {total_reports}: {config.get("type", "unknown")}'
                )
                
                # Simulate report generation
                import time
                time.sleep(2)
                
                result = {
                    'report_type': config.get('type'),
                    'file_name': f"report_{config.get('type')}_{i+1}.pdf",
                    'status': 'success',
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
                errors.append({
                    'config': config,
                    'error': str(e),
                })
        
        final_result = {
            'total_reports': total_reports,
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors,
            'timestamp': timezone.now().isoformat(),
        }
        
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_success(final_result)
        except AsyncTask.DoesNotExist:
            pass
        
        return final_result
        
    except Exception as exc:
        logger.error(f"Bulk report generation failed: {exc}")
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        raise
