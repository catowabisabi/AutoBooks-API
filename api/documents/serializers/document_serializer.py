from rest_framework import serializers
from documents.models.document import Document


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'original_filename', 'uploaded_at', 'processed', 'ocr_text', 'language']
        read_only_fields = ['id', 'uploaded_at', 'processed', 'ocr_text']

    def create(self, validated_data):
        return Document.objects.create(**validated_data)
