"""
Visualization ViewSet - Chart Generation API Endpoints
視覺化視圖集 - 圖表生成 API 端點
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
import os
import logging

from ai_assistants.services.visualization_service import (
    analyze_data_structure,
    suggest_chart_types,
    generate_chart_from_data,
    generate_chart_with_ai,
    extract_chart_data_from_document,
    process_file_for_visualization,
    generate_dashboard_charts,
    CHART_TYPES
)
from ai_assistants.services.file_validation import (
    validate_data_file,
    FileValidationError,
    MAX_CSV_SIZE,
)

logger = logging.getLogger(__name__)


class ChartTypesView(APIView):
    """List all available chart types / 列出所有可用的圖表類型"""
    
    def get(self, request):
        return Response({
            'chart_types': CHART_TYPES,
            'message': 'Available chart types and their configurations'
        })


class AnalyzeDataView(APIView):
    """Analyze data structure and suggest chart types / 分析數據結構並建議圖表類型"""
    parser_classes = [JSONParser]
    
    def post(self, request):
        data = request.data.get('data', [])
        
        if not data:
            return Response(
                {'error': 'No data provided. Send JSON array in "data" field.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        analysis = analyze_data_structure(data)
        suggestions = suggest_chart_types(data)
        
        return Response({
            'analysis': analysis,
            'suggested_charts': suggestions
        })


class GenerateChartView(APIView):
    """Generate a chart configuration from data / 從數據生成圖表配置"""
    parser_classes = [JSONParser]
    
    def post(self, request):
        data = request.data.get('data', [])
        chart_type = request.data.get('type', 'bar')
        title = request.data.get('title')
        description = request.data.get('description')
        x_key = request.data.get('xKey')
        y_key = request.data.get('yKey')
        label_key = request.data.get('labelKey')
        value_key = request.data.get('valueKey')
        
        if not data:
            return Response(
                {'error': 'No data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if chart_type not in CHART_TYPES:
            return Response(
                {'error': f'Invalid chart type. Available: {list(CHART_TYPES.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = generate_chart_from_data(
            data=data,
            chart_type=chart_type,
            title=title,
            x_key=x_key,
            y_key=y_key,
            label_key=label_key,
            value_key=value_key,
            description=description
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)


class GenerateChartWithAIView(APIView):
    """Use AI to generate optimal chart based on natural language request / 使用 AI 根據自然語言請求生成最佳圖表"""
    parser_classes = [JSONParser]
    
    def post(self, request):
        data = request.data.get('data', [])
        prompt = request.data.get('prompt', '')
        language = request.data.get('language', 'en')
        
        if not data:
            return Response(
                {'error': 'No data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not prompt:
            return Response(
                {'error': 'No prompt provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = generate_chart_with_ai(
            data=data,
            user_prompt=prompt,
            language=language
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)


class DocumentChartView(APIView):
    """Extract chart data from a document / 從文件中提取圖表數據"""
    
    def get(self, request, document_id):
        result = extract_chart_data_from_document(document_id)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        return Response(result)
    
    def post(self, request, document_id):
        """Generate specific chart from document data / 從文件數據生成特定圖表"""
        chart_type = request.data.get('type', 'bar')
        title = request.data.get('title')
        x_key = request.data.get('xKey')
        y_key = request.data.get('yKey')
        label_key = request.data.get('labelKey')
        value_key = request.data.get('valueKey')
        
        # First get document data
        doc_result = extract_chart_data_from_document(document_id)
        
        if 'error' in doc_result:
            return Response(doc_result, status=status.HTTP_404_NOT_FOUND)
        
        if 'data' not in doc_result:
            return Response(
                {'error': 'Document has no chartable data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate chart
        result = generate_chart_from_data(
            data=doc_result['data'],
            chart_type=chart_type,
            title=title,
            x_key=x_key,
            y_key=y_key,
            label_key=label_key,
            value_key=value_key
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)


class FileVisualizationView(APIView):
    """Upload and visualize a file / 上傳並視覺化文件"""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Comprehensive file validation
        try:
            ext, mime_type = validate_data_file(file)
            logger.info(f"File validated: {file.name} ({ext}, {mime_type})")
        except FileValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine file type
        file_name = file.name.lower()
        if file_name.endswith('.csv'):
            file_type = 'csv'
        elif file_name.endswith(('.xlsx', '.xls')):
            file_type = 'xlsx'
        elif file_name.endswith('.json'):
            file_type = 'json'
        else:
            return Response(
                {'error': 'Unsupported file type. Supported: CSV, Excel, JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        try:
            result = process_file_for_visualization(tmp_path, file_type)
            
            if 'error' in result:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'filename': file.name,
                **result
            })
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class DashboardChartsView(APIView):
    """Generate multiple charts for dashboard / 為儀表板生成多個圖表"""
    parser_classes = [JSONParser]
    
    def post(self, request):
        data = request.data.get('data', [])
        max_charts = request.data.get('max_charts', 4)
        
        if not data:
            return Response(
                {'error': 'No data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        charts = generate_dashboard_charts(data, max_charts=max_charts)
        
        return Response({
            'charts': charts,
            'count': len(charts)
        })


class QuickChartView(APIView):
    """Quick chart generation with minimal configuration / 使用最少配置快速生成圖表"""
    parser_classes = [JSONParser]
    
    def post(self, request):
        data = request.data.get('data', [])
        
        if not data:
            return Response(
                {'error': 'No data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Auto-detect best chart
        suggestions = suggest_chart_types(data)
        
        if not suggestions:
            return Response(
                {'error': 'Could not determine suitable chart type for data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        best_suggestion = suggestions[0]
        
        result = generate_chart_from_data(
            data=data,
            chart_type=best_suggestion['type'],
            title=best_suggestion.get('title'),
            x_key=best_suggestion.get('xKey'),
            y_key=best_suggestion.get('yKey'),
            label_key=best_suggestion.get('labelKey'),
            value_key=best_suggestion.get('valueKey')
        )
        
        return Response({
            'chart': result,
            'alternatives': suggestions[1:4] if len(suggestions) > 1 else []
        })
