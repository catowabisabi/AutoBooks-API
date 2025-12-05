from rest_framework import serializers
from documents.models.document import Document


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'original_filename']

    def create(self, validated_data):
        tenant = self.context['request'].user.tenant
        return Document.objects.create(**validated_data, tenant=tenant)
