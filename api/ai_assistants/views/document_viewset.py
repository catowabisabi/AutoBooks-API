from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from ai_assistants.serializers.document_serializer import DocumentQuerySerializer, CombinedDocumentSerializer
from ai_assistants.services.document_service import process_document, is_allowed_file, document_cache
from ai_assistants.agents.document_classifier import classify_document_query
from ai_assistants.services.document_service import handle_document_query_logic
import logging

logger = logging.getLogger(__name__)


class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

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

    def post(self, request):
        serializer = CombinedDocumentSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data["file"]
        query = serializer.validated_data["query"]
        return_document_data = serializer.validated_data.get("return_document_data", False)

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
