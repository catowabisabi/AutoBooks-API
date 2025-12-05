from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from documents.models.document import Document
from documents.serializers.document_serializer import DocumentUploadSerializer
from documents.services.ocr_service import perform_ocr
from documents.services.extraction_service import extract_data_from_text
from documents.services.translation_service import translate_text


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentUploadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def extract_text(self, request, pk=None):
        doc = self.get_object()
        text = perform_ocr(doc.file.path)
        doc.ocr_text = text
        doc.save()
        return Response({"ocr_text": text})

    @action(detail=True, methods=['post'])
    def extract_data(self, request, pk=None):
        doc = self.get_object()
        data = extract_data_from_text(doc.ocr_text or "")
        doc.extracted_data = data
        doc.save()
        return Response({"data": data})

    @action(detail=True, methods=['post'])
    def translate(self, request, pk=None):
        target_lang = request.query_params.get("lang", "en")
        doc = self.get_object()
        translated = translate_text(doc.ocr_text or "", target_lang)
        doc.translated_text = translated
        doc.language = target_lang
        doc.save()
        return Response({"translated_text": translated})
