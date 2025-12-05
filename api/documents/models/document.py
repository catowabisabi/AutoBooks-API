import uuid
from django.db import models
from core.models import BaseModel


class Document(BaseModel):
    file = models.FileField(upload_to='documents/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    ocr_text = models.TextField(null=True, blank=True)
    extracted_data = models.JSONField(null=True, blank=True)
    translated_text = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=10, default='en')
