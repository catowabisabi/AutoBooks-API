"""
AI Assistants Tasks Package
===========================
Celery tasks for async processing of OCR, reports, AI analysis, etc.
"""

from .ocr_tasks import process_document_ocr, batch_ocr_process
from .report_tasks import generate_report, generate_bulk_reports
from .ai_tasks import run_ai_analysis, batch_ai_analysis
from .cleanup_tasks import cleanup_old_task_results

__all__ = [
    'process_document_ocr',
    'batch_ocr_process',
    'generate_report',
    'generate_bulk_reports',
    'run_ai_analysis',
    'batch_ai_analysis',
    'cleanup_old_task_results',
]
