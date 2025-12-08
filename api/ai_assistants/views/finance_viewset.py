from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
import json
from ai_assistants.services.finance_service import ReceiptAnalyzerService


class ReceiptAnalyzerViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]
    
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
            parsed_data = service.analyze(file)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {
            "success": True,
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
    
    @action(detail=False, methods=['post'], url_path='analyze-report')
    def analyze_report(self, request):
        """
        Analyze a financial report using AI
        
        Request body:
        {
            "report_type": "balance_sheet" | "income_statement" | "cash_flow" | "trial_balance",
            "report_data": {...},  // The report data to analyze
            "questions": ["What are the key insights?", "Any concerns?"],
            "period": "2024-Q4"
        }
        
        Or upload a file:
        - file: PDF/Excel report file
        - report_type: string
        """
        from core.libs.ai_service import get_ai_service
        
        file = request.FILES.get('file')
        report_type = request.data.get('report_type', 'general')
        report_data = request.data.get('report_data')
        questions = request.data.get('questions', [])
        period = request.data.get('period', '')
        
        if not file and not report_data:
            return Response({
                'success': False,
                'error': 'Either file or report_data is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Build analysis prompt
            prompt = f"""Analyze the following {report_type} financial report{f' for period {period}' if period else ''}.

"""
            if report_data:
                prompt += f"Report Data:\n{json.dumps(report_data, indent=2, default=str)}\n\n"
            
            if questions:
                prompt += "Please address the following questions:\n"
                for i, q in enumerate(questions, 1):
                    prompt += f"{i}. {q}\n"
            else:
                prompt += """Please provide:
1. Key financial insights and metrics
2. Notable trends or changes
3. Potential concerns or risks
4. Recommendations for improvement
5. Overall financial health assessment
"""
            
            # Get AI analysis
            ai = get_ai_service(provider='openai')
            response = ai.chat(
                message=prompt,
                system_prompt="You are an expert financial analyst. Provide detailed, actionable insights from financial reports. Use bullet points and clear formatting.",
                temperature=0.3,
                max_tokens=2000
            )
            
            return Response({
                'success': True,
                'report_type': report_type,
                'period': period,
                'analysis': response.content,
                'model': response.model,
                'usage': response.usage
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='compare-periods')
    def compare_periods(self, request):
        """
        Compare financial data across periods
        
        Request body:
        {
            "report_type": "income_statement",
            "periods": [
                {"period": "2024-Q3", "data": {...}},
                {"period": "2024-Q4", "data": {...}}
            ]
        }
        """
        from core.libs.ai_service import get_ai_service
        
        report_type = request.data.get('report_type', 'financial')
        periods = request.data.get('periods', [])
        
        if len(periods) < 2:
            return Response({
                'success': False,
                'error': 'At least 2 periods are required for comparison'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            prompt = f"""Compare the following {report_type} reports across periods:

"""
            for p in periods:
                prompt += f"\n--- {p.get('period', 'Period')} ---\n"
                prompt += json.dumps(p.get('data', {}), indent=2, default=str)
            
            prompt += """

Please provide:
1. Period-over-period changes (with percentages where applicable)
2. Key trends observed
3. Notable improvements or concerns
4. Variance analysis for major items
5. Recommendations based on the trends
"""
            
            ai = get_ai_service(provider='openai')
            response = ai.chat(
                message=prompt,
                system_prompt="You are an expert financial analyst specializing in period-over-period analysis. Provide detailed comparisons with specific numbers and percentages.",
                temperature=0.3,
                max_tokens=2500
            )
            
            return Response({
                'success': True,
                'report_type': report_type,
                'periods_compared': [p.get('period') for p in periods],
                'analysis': response.content,
                'model': response.model
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='forecast')
    def forecast(self, request):
        """
        Generate financial forecasts based on historical data
        
        Request body:
        {
            "historical_data": [...],  // Array of period data
            "forecast_periods": 4,  // Number of periods to forecast
            "metric": "revenue"  // Metric to forecast
        }
        """
        from core.libs.ai_service import get_ai_service
        
        historical_data = request.data.get('historical_data', [])
        forecast_periods = request.data.get('forecast_periods', 4)
        metric = request.data.get('metric', 'revenue')
        
        if not historical_data:
            return Response({
                'success': False,
                'error': 'historical_data is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            prompt = f"""Based on the following historical {metric} data, provide a forecast for the next {forecast_periods} periods:

Historical Data:
{json.dumps(historical_data, indent=2, default=str)}

Please provide:
1. Forecasted values for each of the next {forecast_periods} periods
2. The methodology/assumptions used
3. Confidence level for the forecast
4. Key factors that could affect the forecast
5. Best case and worst case scenarios
"""
            
            ai = get_ai_service(provider='openai')
            response = ai.chat(
                message=prompt,
                system_prompt="You are an expert financial forecaster. Provide realistic forecasts with clear reasoning and confidence intervals.",
                temperature=0.4,
                max_tokens=2000
            )
            
            return Response({
                'success': True,
                'metric': metric,
                'forecast_periods': forecast_periods,
                'forecast': response.content,
                'model': response.model
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
