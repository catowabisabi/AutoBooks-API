from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import json
from ai_assistants.services.finance_service import ReceiptAnalyzerService


class ReceiptAnalyzerViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze_receipt(self, request):
        file = request.FILES.get('file')
        categories = request.data.get('category', '[]')

        try:
            categories = json.loads(categories)
        except Exception:
            categories = []

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = ReceiptAnalyzerService()
            parsed_data = service
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {
            "merchantName": parsed_data.get("merchantName"),
            "invoiceNo": parsed_data.get("invoiceNo"),
            "expenseDate": parsed_data.get("expenseDate"),
            "currency": parsed_data.get("receiptCurrency"),
            "claimedAmount": parsed_data.get("invoiceAmount"),
            "city": parsed_data.get("city"),
            "country": parsed_data.get("country"),
            "description": parsed_data.get("description"),
            "status": "Pending",
            "receiptFile": None
        }

        return Response(response_data, status=status.HTTP_200_OK)
