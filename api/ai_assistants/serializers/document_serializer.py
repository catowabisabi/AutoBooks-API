# api/ai_assistants/serializers/document_serializer.py
"""
Document Assistant Serializers
"""
from rest_framework import serializers
from ai_assistants.models import AIDocument, DocumentComparison, DocumentType


class DocumentQuerySerializer(serializers.Serializer):
    document_id = serializers.CharField()
    query = serializers.CharField()


class CombinedDocumentSerializer(serializers.Serializer):
    """
    Serializer for the combined document processing API.
    Handles file upload and query processing in a single request.
    """
    file = serializers.FileField(
        help_text="The document file to process (PDF, PNG, JPG, JPEG, GIF, JFIF)"
    )
    query = serializers.CharField(
        max_length=2000,
        help_text="The query or instruction to process on the document"
    )
    return_document_data = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Whether to include the full document processing data in the response"
    )

    def validate_file(self, value):
        """Validate file size and basic properties"""
        if value.size > 50 * 1024 * 1024:  # 50MB limit
            raise serializers.ValidationError("File size cannot exceed 50MB")
        return value

    def validate_query(self, value):
        """Validate query content"""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty or whitespace only")
        return value.strip()


class AIDocumentSerializer(serializers.ModelSerializer):
    """Full AI Document serializer"""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = AIDocument
        fields = [
            'id', 'title', 'document_type', 'document_type_display',
            'file', 'original_filename', 'file_size', 'mime_type',
            'uploaded_by', 'uploaded_by_name',
            'is_ocr_processed', 'extracted_text', 'ocr_confidence',
            'ai_summary', 'ai_keywords', 'ai_entities', 'ai_sentiment',
            'related_project', 'related_client', 'related_campaign',
            'tags',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'is_ocr_processed', 'extracted_text', 'ocr_confidence',
            'ai_summary', 'ai_keywords', 'ai_entities', 'ai_sentiment'
        ]


class AIDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight document list serializer"""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = AIDocument
        fields = [
            'id', 'title', 'document_type', 'document_type_display',
            'original_filename', 'file_size',
            'is_ocr_processed', 'ai_summary',
            'tags', 'created_at'
        ]


class AIDocumentUploadSerializer(serializers.ModelSerializer):
    """Upload a new document"""
    
    class Meta:
        model = AIDocument
        fields = [
            'title', 'document_type', 'file',
            'related_project', 'related_client', 'related_campaign',
            'tags'
        ]


class DocumentComparisonSerializer(serializers.ModelSerializer):
    """Document comparison serializer"""
    document_a_title = serializers.CharField(source='document_a.title', read_only=True)
    document_b_title = serializers.CharField(source='document_b.title', read_only=True)
    
    class Meta:
        model = DocumentComparison
        fields = [
            'id', 'document_a', 'document_a_title',
            'document_b', 'document_b_title',
            'similarity_score', 'differences', 'ai_analysis',
            'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'similarity_score', 'differences', 'ai_analysis']


class DocumentCompareRequestSerializer(serializers.Serializer):
    """Request to compare two documents"""
    document_a_id = serializers.UUIDField()
    document_b_id = serializers.UUIDField()


class DocumentOCRRequestSerializer(serializers.Serializer):
    """Request OCR processing on a document"""
    document_id = serializers.UUIDField()
    language = serializers.CharField(default='eng+chi_tra', help_text='Tesseract language codes')


class DocumentSummarizeRequestSerializer(serializers.Serializer):
    """Request AI summarization of a document"""
    document_id = serializers.UUIDField()
    summary_length = serializers.ChoiceField(
        choices=[('short', 'Short'), ('medium', 'Medium'), ('detailed', 'Detailed')],
        default='medium'
    )


class DocumentSearchSerializer(serializers.Serializer):
    """Search across all documents"""
    query = serializers.CharField()
    document_types = serializers.ListField(
        child=serializers.ChoiceField(choices=DocumentType.choices),
        required=False
    )
    tags = serializers.ListField(child=serializers.CharField(), required=False)