"""
Visualization Service - Chart Generation API
視覺化服務 - 圖表生成 API

This service handles:
1. Converting document data to charts
2. Generating chart configurations from raw data
3. Auto-detecting best chart types for data
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from openai import OpenAI
from django.conf import settings


client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ============================================================================
# CHART TYPE DEFINITIONS
# ============================================================================

CHART_TYPES = {
    'bar': {
        'name': 'Bar Chart',
        'description': 'Compare values across categories',
        'best_for': ['categorical comparison', 'ranking', 'frequency'],
        'required_fields': ['xKey', 'yKey'],
    },
    'line': {
        'name': 'Line Chart',
        'description': 'Show trends over time',
        'best_for': ['time series', 'trend analysis', 'continuous data'],
        'required_fields': ['xKey', 'yKey'],
    },
    'area': {
        'name': 'Area Chart',
        'description': 'Show cumulative trends',
        'best_for': ['volume over time', 'cumulative values', 'stacked comparison'],
        'required_fields': ['xKey', 'yKey'],
    },
    'pie': {
        'name': 'Pie Chart',
        'description': 'Show proportions of a whole',
        'best_for': ['percentage distribution', 'part-to-whole', 'composition'],
        'required_fields': ['labelKey', 'valueKey'],
    },
    'scatter': {
        'name': 'Scatter Plot',
        'description': 'Show correlation between variables',
        'best_for': ['correlation', 'distribution', 'outlier detection'],
        'required_fields': ['xKey', 'yKey'],
    },
    'table': {
        'name': 'Data Table',
        'description': 'Display detailed data in rows and columns',
        'best_for': ['detailed view', 'exact values', 'multi-column data'],
        'required_fields': [],
    },
}


# ============================================================================
# DATA ANALYSIS FUNCTIONS
# ============================================================================

def analyze_data_structure(data: List[Dict]) -> Dict:
    """Analyze data structure to determine suitable chart types / 分析數據結構以確定適合的圖表類型"""
    if not data or len(data) == 0:
        return {'error': 'No data provided'}
    
    df = pd.DataFrame(data)
    
    # Analyze columns
    column_info = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        unique_count = df[col].nunique()
        null_count = df[col].isnull().sum()
        
        # Determine column type
        if pd.api.types.is_numeric_dtype(df[col]):
            col_type = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_type = 'datetime'
        elif unique_count <= 20:
            col_type = 'categorical'
        else:
            col_type = 'text'
        
        column_info[col] = {
            'dtype': dtype,
            'type': col_type,
            'unique_count': unique_count,
            'null_count': null_count,
            'sample_values': df[col].dropna().head(3).tolist()
        }
    
    return {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': column_info
    }


def suggest_chart_types(data: List[Dict]) -> List[Dict]:
    """Suggest best chart types based on data structure / 根據數據結構建議最佳圖表類型"""
    analysis = analyze_data_structure(data)
    
    if 'error' in analysis:
        return []
    
    columns = analysis['columns']
    suggestions = []
    
    # Find numeric and categorical columns
    numeric_cols = [col for col, info in columns.items() if info['type'] == 'numeric']
    categorical_cols = [col for col, info in columns.items() if info['type'] == 'categorical']
    datetime_cols = [col for col, info in columns.items() if info['type'] == 'datetime']
    
    # Suggest bar chart if we have categorical + numeric
    if categorical_cols and numeric_cols:
        suggestions.append({
            'type': 'bar',
            'xKey': categorical_cols[0],
            'yKey': numeric_cols[0],
            'title': f'{numeric_cols[0]} by {categorical_cols[0]}',
            'confidence': 0.9
        })
    
    # Suggest line chart for time series
    if datetime_cols and numeric_cols:
        suggestions.append({
            'type': 'line',
            'xKey': datetime_cols[0],
            'yKey': numeric_cols[0],
            'title': f'{numeric_cols[0]} over time',
            'confidence': 0.95
        })
    
    # Suggest pie chart for categorical distribution
    if categorical_cols and numeric_cols:
        suggestions.append({
            'type': 'pie',
            'labelKey': categorical_cols[0],
            'valueKey': numeric_cols[0],
            'title': f'Distribution of {numeric_cols[0]} by {categorical_cols[0]}',
            'confidence': 0.85
        })
    
    # Suggest scatter for 2 numeric columns
    if len(numeric_cols) >= 2:
        suggestions.append({
            'type': 'scatter',
            'xKey': numeric_cols[0],
            'yKey': numeric_cols[1],
            'title': f'{numeric_cols[0]} vs {numeric_cols[1]}',
            'confidence': 0.8
        })
    
    # Always suggest table
    suggestions.append({
        'type': 'table',
        'title': 'Data Table',
        'confidence': 1.0
    })
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x['confidence'], reverse=True)
    
    return suggestions


def generate_chart_from_data(
    data: List[Dict],
    chart_type: str,
    title: Optional[str] = None,
    x_key: Optional[str] = None,
    y_key: Optional[str] = None,
    label_key: Optional[str] = None,
    value_key: Optional[str] = None,
    description: Optional[str] = None
) -> Dict:
    """Generate chart configuration from raw data / 從原始數據生成圖表配置"""
    
    if not data:
        return {'error': 'No data provided'}
    
    df = pd.DataFrame(data)
    
    # Auto-detect keys if not provided
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    non_numeric_cols = [col for col in df.columns if not pd.api.types.is_numeric_dtype(df[col])]
    
    if chart_type == 'pie':
        label_key = label_key or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        value_key = value_key or (numeric_cols[0] if numeric_cols else df.columns[1] if len(df.columns) > 1 else df.columns[0])
        
        # Aggregate data for pie chart
        pie_data = df.groupby(label_key)[value_key].sum().reset_index()
        pie_data.columns = ['label', 'value']
        
        return {
            'type': 'pie',
            'title': title or f'{value_key} by {label_key}',
            'description': description or f'Distribution of {value_key} across {label_key}',
            'data': pie_data.to_dict(orient='records'),
            'labelKey': 'label',
            'valueKey': 'value'
        }
    
    elif chart_type == 'table':
        return {
            'type': 'table',
            'title': title or 'Data Table',
            'description': description or f'Showing {len(df)} rows',
            'data': df.head(100).to_dict(orient='records'),
            'columns': [
                {
                    'key': col,
                    'label': col.replace('_', ' ').title(),
                    'align': 'right' if pd.api.types.is_numeric_dtype(df[col]) else 'left',
                    'format': 'number' if pd.api.types.is_numeric_dtype(df[col]) else 'text'
                }
                for col in df.columns
            ]
        }
    
    else:  # bar, line, area, scatter
        x_key = x_key or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        y_key = y_key or (numeric_cols[0] if numeric_cols else df.columns[1] if len(df.columns) > 1 else df.columns[0])
        
        # For bar charts, aggregate by x_key
        if chart_type == 'bar' and x_key in non_numeric_cols:
            chart_data = df.groupby(x_key)[y_key].sum().reset_index()
        else:
            chart_data = df[[x_key, y_key]].dropna()
        
        return {
            'type': chart_type,
            'title': title or f'{y_key} by {x_key}',
            'description': description or f'{chart_type.title()} chart showing {y_key} vs {x_key}',
            'data': chart_data.to_dict(orient='records'),
            'xKey': x_key,
            'yKey': y_key
        }


# ============================================================================
# AI-POWERED CHART GENERATION
# ============================================================================

def generate_chart_with_ai(
    data: List[Dict],
    user_prompt: str,
    language: str = 'en'
) -> Dict:
    """Use AI to generate optimal chart configuration based on user request / 使用 AI 根據用戶請求生成最佳圖表配置"""
    
    df = pd.DataFrame(data)
    
    system_prompt = f"""You are a data visualization expert. Given a dataset and user request, generate the optimal chart configuration.

Available chart types: bar, line, area, pie, scatter, table

Dataset columns: {df.columns.tolist()}
Data types: {df.dtypes.to_dict()}
Sample data (first 5 rows): {df.head(5).to_dict(orient='records')}
Total rows: {len(df)}

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{{
    "type": "bar|line|area|pie|scatter|table",
    "title": "Chart title",
    "title_{language}": "Title in {language}",
    "description": "Chart description",
    "description_{language}": "Description in {language}",
    "xKey": "column_name (for bar/line/area/scatter)",
    "yKey": "column_name (for bar/line/area/scatter)",
    "labelKey": "column_name (for pie only)",
    "valueKey": "column_name (for pie only)",
    "aggregation": "sum|count|mean|max|min (optional)",
    "filter": "optional filter expression"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0
        )
        
        config = json.loads(response.choices[0].message.content)
        
        # Apply aggregation if specified
        chart_type = config.get('type', 'bar')
        aggregation = config.get('aggregation')
        
        if chart_type == 'pie':
            label_key = config.get('labelKey', df.columns[0])
            value_key = config.get('valueKey', df.columns[1] if len(df.columns) > 1 else df.columns[0])
            
            if aggregation == 'count':
                result_df = df[label_key].value_counts().reset_index()
                result_df.columns = ['label', 'value']
            else:
                result_df = df.groupby(label_key)[value_key].sum().reset_index()
                result_df.columns = ['label', 'value']
            
            return {
                'type': 'pie',
                'title': config.get('title', f'{value_key} by {label_key}'),
                'description': config.get('description', ''),
                'data': result_df.to_dict(orient='records'),
                'labelKey': 'label',
                'valueKey': 'value'
            }
        
        elif chart_type == 'table':
            return {
                'type': 'table',
                'title': config.get('title', 'Data Table'),
                'description': config.get('description', ''),
                'data': df.head(50).to_dict(orient='records')
            }
        
        else:  # bar, line, area, scatter
            x_key = config.get('xKey', df.columns[0])
            y_key = config.get('yKey', df.columns[1] if len(df.columns) > 1 else df.columns[0])
            
            if aggregation:
                agg_func = getattr(df.groupby(x_key)[y_key], aggregation, 'sum')
                result_df = agg_func().reset_index()
            else:
                result_df = df[[x_key, y_key]].dropna()
            
            return {
                'type': chart_type,
                'title': config.get('title', f'{y_key} by {x_key}'),
                'description': config.get('description', ''),
                'data': result_df.to_dict(orient='records'),
                'xKey': x_key,
                'yKey': y_key
            }
    
    except Exception as e:
        return {'error': f'AI chart generation failed: {str(e)}'}


# ============================================================================
# DOCUMENT DATA EXTRACTION
# ============================================================================

def extract_chart_data_from_document(document_id: int) -> Dict:
    """Extract chartable data from a document / 從文件中提取可圖表化的數據"""
    from documents.models import Document
    
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return {'error': 'Document not found'}
    
    # Check if document has extracted data
    if doc.extracted_data:
        data = doc.extracted_data
        
        # If it's already structured data
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            analysis = analyze_data_structure(data)
            suggestions = suggest_chart_types(data)
            
            return {
                'document_id': document_id,
                'filename': doc.original_filename,
                'data': data,
                'analysis': analysis,
                'suggested_charts': suggestions
            }
        
        # If it's a nested structure, try to find arrays
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    analysis = analyze_data_structure(value)
                    suggestions = suggest_chart_types(value)
                    
                    return {
                        'document_id': document_id,
                        'filename': doc.original_filename,
                        'data_key': key,
                        'data': value,
                        'analysis': analysis,
                        'suggested_charts': suggestions
                    }
    
    # No structured data, try to parse OCR text
    if doc.ocr_text:
        return {
            'document_id': document_id,
            'filename': doc.original_filename,
            'message': 'Document has text but no structured data. Use AI to extract data first.',
            'ocr_text_preview': doc.ocr_text[:500] if doc.ocr_text else None
        }
    
    return {
        'document_id': document_id,
        'filename': doc.original_filename,
        'message': 'Document has no extractable data'
    }


def process_file_for_visualization(file_path: str, file_type: str) -> Dict:
    """Process uploaded file and generate visualization options / 處理上傳的文件並生成視覺化選項"""
    
    try:
        # Read file based on type
        if file_type in ['csv', 'text/csv', 'application/csv']:
            df = pd.read_csv(file_path)
        elif file_type in ['xlsx', 'xls', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
            df = pd.read_excel(file_path)
        elif file_type in ['json', 'application/json']:
            with open(file_path, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try to find array data in dict
                for key, value in data.items():
                    if isinstance(value, list):
                        df = pd.DataFrame(value)
                        break
                else:
                    df = pd.DataFrame([data])
        else:
            return {'error': f'Unsupported file type: {file_type}'}
        
        # Convert data to records
        data = df.to_dict(orient='records')
        
        # Analyze and suggest charts
        analysis = analyze_data_structure(data)
        suggestions = suggest_chart_types(data)
        
        return {
            'success': True,
            'data': data[:1000],  # Limit to 1000 rows
            'total_rows': len(df),
            'analysis': analysis,
            'suggested_charts': suggestions
        }
    
    except Exception as e:
        return {'error': f'Failed to process file: {str(e)}'}


# ============================================================================
# BATCH CHART GENERATION
# ============================================================================

def generate_dashboard_charts(data: List[Dict], max_charts: int = 4) -> List[Dict]:
    """Generate multiple charts for a dashboard view / 為儀表板視圖生成多個圖表"""
    
    suggestions = suggest_chart_types(data)
    charts = []
    
    for suggestion in suggestions[:max_charts]:
        chart_type = suggestion['type']
        
        chart = generate_chart_from_data(
            data=data,
            chart_type=chart_type,
            title=suggestion.get('title'),
            x_key=suggestion.get('xKey'),
            y_key=suggestion.get('yKey'),
            label_key=suggestion.get('labelKey'),
            value_key=suggestion.get('valueKey')
        )
        
        if 'error' not in chart:
            charts.append(chart)
    
    return charts
