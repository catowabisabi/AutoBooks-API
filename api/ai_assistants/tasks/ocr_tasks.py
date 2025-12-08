"""
OCR Processing Tasks
====================
Async tasks for document OCR processing.
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_ocr(self, document_path: str, user_id: int, options: dict = None):
    """
    Process a single document with OCR.
    
    Args:
        document_path: Path to the document file
        user_id: ID of the user who initiated the task
        options: OCR processing options (language, dpi, etc.)
    
    Returns:
        dict: OCR results with extracted text and metadata
    """
    from ai_assistants.models_tasks import AsyncTask, TaskStatus
    
    options = options or {}
    task_id = self.request.id
    
    try:
        # Update task as started
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        # Phase 1: Load document (10%)
        update_task_progress(task_id, 10, 'Loading document...')
        
        # TODO: Implement actual OCR processing
        # For now, simulate the process
        import time
        
        # Phase 2: Pre-process image (30%)
        update_task_progress(task_id, 30, 'Pre-processing image...')
        time.sleep(1)  # Simulate processing
        
        # Phase 3: Run OCR (60%)
        update_task_progress(task_id, 60, 'Running OCR engine...')
        time.sleep(2)  # Simulate OCR
        
        # Phase 4: Post-process text (80%)
        update_task_progress(task_id, 80, 'Post-processing extracted text...')
        time.sleep(0.5)
        
        # Phase 5: Complete (100%)
        result = {
            'document_path': document_path,
            'extracted_text': 'Sample extracted text from document...',
            'pages': 1,
            'confidence': 0.95,
            'language': options.get('language', 'en'),
            'processing_time_ms': 3500,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Mark success
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_success(result)
        except AsyncTask.DoesNotExist:
            pass
        
        return result
        
    except Exception as exc:
        logger.error(f"OCR processing failed: {exc}")
        
        # Mark failure
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        
        # Retry if retries remaining
        raise self.retry(exc=exc)


@shared_task(bind=True)
def batch_ocr_process(self, document_paths: list, user_id: int, options: dict = None):
    """
    Process multiple documents with OCR in batch.
    
    Args:
        document_paths: List of document file paths
        user_id: ID of the user who initiated the task
        options: OCR processing options
    
    Returns:
        dict: Batch results with individual document results
    """
    from ai_assistants.models_tasks import AsyncTask
    
    options = options or {}
    task_id = self.request.id
    total_docs = len(document_paths)
    results = []
    errors = []
    
    try:
        # Update task as started
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_started()
        except AsyncTask.DoesNotExist:
            pass
        
        for i, doc_path in enumerate(document_paths):
            try:
                # Update progress
                progress = int((i / total_docs) * 100)
                update_task_progress(task_id, progress, f'Processing document {i+1} of {total_docs}')
                
                # Process each document (simplified)
                result = {
                    'document_path': doc_path,
                    'extracted_text': f'Extracted text from {doc_path}',
                    'confidence': 0.9,
                    'status': 'success',
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process {doc_path}: {e}")
                errors.append({
                    'document_path': doc_path,
                    'error': str(e),
                })
        
        # Complete
        final_result = {
            'total_documents': total_docs,
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
        logger.error(f"Batch OCR processing failed: {exc}")
        try:
            async_task = AsyncTask.objects.get(celery_task_id=task_id)
            async_task.mark_failure(str(exc), traceback.format_exc())
        except AsyncTask.DoesNotExist:
            pass
        raise
