"""
AI Analysis Tasks
==================
Async tasks for AI-powered analysis operations.
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


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_ai_analysis(self, analysis_type: str, user_id: int, data: dict, options: dict = None):
    """
    Run AI analysis on provided data.
    
    Args:
        analysis_type: Type of analysis (sentiment, classification, extraction, etc.)
        user_id: ID of the user who initiated the analysis
        data: Data to analyze
        options: Analysis options (model, temperature, etc.)
    
    Returns:
        dict: Analysis results
    """
    from ai_assistants.models_tasks import AsyncTask
    from ai_assistants.models_feedback import AIResultLog
    import uuid
    
    options = options or {}
    task_id = self.request.id
    result_id = str(uuid.uuid4())
    
    try:
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        start_time = timezone.now()
        
        # Phase 1: Prepare data (15%)
        update_task_progress(task_id, 15, 'Preparing data for analysis...')
        
        import time
        time.sleep(0.5)
        
        # Phase 2: Run AI model (50%)
        update_task_progress(task_id, 50, f'Running {analysis_type} analysis...')
        time.sleep(2)  # Simulate AI processing
        
        # Phase 3: Process results (75%)
        update_task_progress(task_id, 75, 'Processing analysis results...')
        time.sleep(0.5)
        
        # Generate mock results based on analysis type
        if analysis_type == 'sentiment':
            analysis_result = {
                'sentiment': 'positive',
                'confidence': 0.87,
                'scores': {
                    'positive': 0.87,
                    'neutral': 0.10,
                    'negative': 0.03,
                },
            }
        elif analysis_type == 'classification':
            analysis_result = {
                'category': 'invoice',
                'confidence': 0.92,
                'alternatives': [
                    {'category': 'receipt', 'confidence': 0.05},
                    {'category': 'quote', 'confidence': 0.03},
                ],
            }
        elif analysis_type == 'extraction':
            analysis_result = {
                'fields': [
                    {'name': 'vendor', 'value': 'Acme Corp', 'confidence': 0.95},
                    {'name': 'amount', 'value': '1234.56', 'confidence': 0.88},
                    {'name': 'date', 'value': '2024-01-15', 'confidence': 0.92},
                ],
                'overall_confidence': 0.92,
            }
        else:
            analysis_result = {
                'type': analysis_type,
                'status': 'completed',
                'confidence': 0.85,
            }
        
        end_time = timezone.now()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Log the result
        try:
            from users.models import User
            user = User.objects.get(id=user_id)
            AIResultLog.objects.create(
                user=user,
                result_id=result_id,
                result_type=f'ai_analysis_{analysis_type}',
                output_data=analysis_result,
                overall_confidence=analysis_result.get('confidence', 0.0),
                model_provider=options.get('provider', 'openai'),
                model_name=options.get('model', 'gpt-4'),
                processing_time_ms=processing_time_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to log AI result: {e}")
        
        result = {
            'result_id': result_id,
            'analysis_type': analysis_type,
            'analysis_result': analysis_result,
            'processing_time_ms': processing_time_ms,
            'model': options.get('model', 'default'),
            'timestamp': end_time.isoformat(),
        }
        
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_success(result)
        except AsyncTask.DoesNotExist:
            pass
        
        return result
        
    except Exception as exc:
        logger.error(f"AI analysis failed: {exc}")
        
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        
        raise self.retry(exc=exc)


@shared_task(bind=True)
def batch_ai_analysis(self, items: list, analysis_type: str, user_id: int, options: dict = None):
    """
    Run AI analysis on multiple items in batch.
    
    Args:
        items: List of items to analyze
        analysis_type: Type of analysis
        user_id: ID of the user who initiated the analysis
        options: Analysis options
    
    Returns:
        dict: Batch analysis results
    """
    from ai_assistants.models_tasks import AsyncTask
    
    options = options or {}
    task_id = self.request.id
    total_items = len(items)
    results = []
    errors = []
    
    try:
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        for i, item in enumerate(items):
            try:
                progress = int((i / total_items) * 100)
                update_task_progress(task_id, progress, f'Analyzing item {i+1} of {total_items}')
                
                import time
                time.sleep(1)  # Simulate processing
                
                result = {
                    'item_index': i,
                    'analysis_type': analysis_type,
                    'confidence': 0.85 + (i % 10) * 0.01,
                    'status': 'success',
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to analyze item {i}: {e}")
                errors.append({
                    'item_index': i,
                    'error': str(e),
                })
        
        final_result = {
            'total_items': total_items,
            'successful': len(results),
            'failed': len(errors),
            'analysis_type': analysis_type,
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
        logger.error(f"Batch AI analysis failed: {exc}")
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        raise
