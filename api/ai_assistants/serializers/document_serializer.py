# api/ai_assistants/serializers/document_serializer.py

from rest_framework import serializers


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