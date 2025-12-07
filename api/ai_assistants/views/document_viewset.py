from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from ai_assistants.serializers.document_serializer import DocumentQuerySerializer, CombinedDocumentSerializer
from ai_assistants.services.document_service import process_document, is_allowed_file, document_cache
from ai_assistants.agents.document_classifier import classify_document_query
from ai_assistants.services.document_service import handle_document_query_logic
from ai_assistants.services.file_validation import (
    validate_document,
    validate_upload,
    FileValidationError,
    MAX_FILE_SIZE,
)
import logging

logger = logging.getLogger(__name__)


class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Comprehensive file validation
        try:
            ext, mime_type = validate_document(file)
            logger.info(f"File validated: {file.name} ({ext}, {mime_type})")
        except FileValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not is_allowed_file(file.name):
            return Response({
                "error": f"Invalid file type. Allowed types: {', '.join(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'jfif'])}"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = process_document(file)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}", exc_info=True)
            return Response({
                "error": f"Document processing failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentInfoView(APIView):
    def get(self, request, document_id):
        doc = document_cache.get(document_id)
        if not doc:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(doc)


class DocumentQueryView(APIView):
    def post(self, request):
        serializer = DocumentQuerySerializer(data=request.data)
        if serializer.is_valid():
            document_id = serializer.validated_data["document_id"]
            query = serializer.validated_data["query"]

            try:
                result = handle_document_query_logic(document_id, query)

                if result.get("type") == "error":
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)

                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Document query error: {str(e)}", exc_info=True)
                return Response({
                    "error": f"Query processing failed: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CombinedDocumentProcessingView(APIView):
    """
    Combined API that handles both file upload and query processing in a single request.

    Usage:
    curl --location 'http://127.0.0.1:8000/api/v1/document-assistant/process/' \
    --form 'file=@"your-file.pdf"' \
    --form 'query="What was the total distance and duration of the trip?"' \
    --form 'return_document_data="false"'
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CombinedDocumentSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data["file"]
        query = serializer.validated_data["query"]
        return_document_data = serializer.validated_data.get("return_document_data", False)

        # Comprehensive file validation
        try:
            ext, mime_type = validate_document(file)
            logger.info(f"File validated: {file.name} ({ext}, {mime_type})")
        except FileValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        if not is_allowed_file(file.name):
            return Response({
                "error": f"Invalid file type. Allowed types: {', '.join(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'jfif'])}"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 1: Process the document
            logger.info(f"Processing document: {file.name}")
            document_result = process_document(file)
            document_id = document_result.get("document_id")

            if not document_id:
                return Response({
                    "error": "Failed to process document - no document ID generated"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info(f"Document processed successfully with ID: {document_id}")

            # Step 2: Process the query
            logger.info(f"Processing query: {query[:50]}...")
            query_result = handle_document_query_logic(document_id, query)

            if query_result.get("type") == "error":
                # If query fails, still return the document processing result
                logger.warning(f"Query processing failed: {query_result.get('message')}")
                response_data = {
                    "success": False,
                    "document_id": document_id,
                    "document_processed": True,
                    "query_processed": False,
                    "error": query_result.get("message", "Query processing failed"),
                    "query_result": None
                }

                if return_document_data:
                    response_data["document_data"] = document_result

                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Step 3: Return combined result
            response_data = {
                "success": True,
                "document_id": document_id,
                "document_processed": True,
                "query_processed": True,
                "query_type": query_result.get("query_type"),
                "query_result": query_result.get("response"),
                "filename": file.name
            }

            # Optionally include the full document data
            if return_document_data:
                response_data["document_data"] = document_result

            logger.info(f"Combined processing completed successfully for document {document_id}")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Combined document processing error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "document_processed": False,
                "query_processed": False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# New Model-Based ViewSets
# ============================================================
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.db.models import Q

from ai_assistants.models import AIDocument, DocumentComparison
from ai_assistants.serializers.document_serializer import (
    AIDocumentSerializer, AIDocumentListSerializer, AIDocumentUploadSerializer,
    DocumentComparisonSerializer, DocumentCompareRequestSerializer,
    DocumentOCRRequestSerializer, DocumentSummarizeRequestSerializer, DocumentSearchSerializer
)


def get_permission_classes():
    """Return permission classes based on DEBUG setting"""
    if settings.DEBUG:
        return [AllowAny()]
    return [IsAuthenticated()]


class AIDocumentViewSet(viewsets.ModelViewSet):
    """
    AI Document management with OCR, summarization, search
    """
    queryset = AIDocument.objects.all()
    serializer_class = AIDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = AIDocument.objects.filter(is_active=True)
        
        # Filter by document type
        doc_type = self.request.query_params.get('document_type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        
        # Filter by OCR status
        ocr_processed = self.request.query_params.get('ocr_processed')
        if ocr_processed is not None:
            queryset = queryset.filter(is_ocr_processed=ocr_processed.lower() == 'true')
        
        # Filter by client
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(related_client_id=client_id)
        
        # Search in extracted text and summary
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(extracted_text__icontains=search) |
                Q(ai_summary__icontains=search) |
                Q(ai_keywords__contains=[search])
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AIDocumentListSerializer
        if self.action == 'create':
            return AIDocumentUploadSerializer
        return AIDocumentSerializer
    
    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        user = self.request.user if self.request.user.is_authenticated else None
        
        serializer.save(
            uploaded_by=user,
            original_filename=file.name if file else '',
            file_size=file.size if file else 0,
            mime_type=file.content_type if file else ''
        )
    
    @action(detail=True, methods=['post'])
    def ocr(self, request, pk=None):
        """
        Run OCR on document
        """
        document = self.get_object()
        
        # TODO: Integrate with OCR service (Tesseract/Google Vision)
        # For now, mock OCR result
        document.is_ocr_processed = True
        document.extracted_text = f"[OCR Demo] Extracted text from {document.original_filename}"
        document.ocr_confidence = 0.85
        document.save()
        
        return Response({
            'status': 'ocr_completed',
            'extracted_text': document.extracted_text,
            'confidence': document.ocr_confidence
        })
    
    @action(detail=True, methods=['post'])
    def summarize(self, request, pk=None):
        """
        AI summarize document
        """
        document = self.get_object()
        
        serializer = DocumentSummarizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        length = serializer.validated_data.get('summary_length', 'medium')
        
        # TODO: Integrate with AI service (GPT)
        # For now, mock summary
        document.ai_summary = f"[AI Summary - {length}] Summary of document: {document.title}"
        document.ai_keywords = ['document', 'summary', 'ai']
        document.ai_entities = {
            'dates': ['2024-01-01'],
            'amounts': ['$1,000'],
            'names': ['John Doe']
        }
        document.save()
        
        return Response({
            'summary': document.ai_summary,
            'keywords': document.ai_keywords,
            'entities': document.ai_entities
        })
    
    @action(detail=False, methods=['post'])
    def compare(self, request):
        """
        Compare two documents
        """
        serializer = DocumentCompareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doc_a_id = serializer.validated_data['document_a_id']
        doc_b_id = serializer.validated_data['document_b_id']
        
        try:
            doc_a = AIDocument.objects.get(id=doc_a_id)
            doc_b = AIDocument.objects.get(id=doc_b_id)
        except AIDocument.DoesNotExist:
            return Response(
                {'error': 'One or both documents not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user if request.user.is_authenticated else None
        
        # TODO: Integrate with AI service for comparison
        # For now, mock comparison
        comparison = DocumentComparison.objects.create(
            document_a=doc_a,
            document_b=doc_b,
            similarity_score=0.75,
            differences=[
                {'section': 'Header', 'type': 'modified', 'description': 'Date changed'},
                {'section': 'Terms', 'type': 'added', 'description': 'New clause added'}
            ],
            ai_analysis=f"Documents {doc_a.title} and {doc_b.title} are 75% similar with key differences in header and terms sections.",
            created_by=user
        )
        
        return Response(
            DocumentComparisonSerializer(comparison).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Full-text search across all documents
        """
        serializer = DocumentSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        doc_types = serializer.validated_data.get('document_types', [])
        tags = serializer.validated_data.get('tags', [])
        
        queryset = self.get_queryset()
        
        # Full-text search
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(extracted_text__icontains=query) |
            Q(ai_summary__icontains=query)
        )
        
        if doc_types:
            queryset = queryset.filter(document_type__in=doc_types)
        
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        results = AIDocumentListSerializer(queryset[:20], many=True).data
        
        return Response({
            'query': query,
            'total': queryset.count(),
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics"""
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'ocr_processed': queryset.filter(is_ocr_processed=True).count(),
            'by_type': {
                doc_type: queryset.filter(document_type=doc_type).count()
                for doc_type, _ in AIDocument._meta.get_field('document_type').choices
            }
        })


class DocumentComparisonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View document comparisons
    """
    queryset = DocumentComparison.objects.all()
    serializer_class = DocumentComparisonSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        return DocumentComparison.objects.filter(is_active=True).order_by('-created_at')
