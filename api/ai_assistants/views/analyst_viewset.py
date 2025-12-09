from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from ai_assistants.serializers.analyst_serializer import AnalystQuerySerializer
from ai_assistants.services.analyst_service import handle_query_logic, dataframe_cache
from ai_assistants.services.analyst_service import load_all_datasets
from django.apps import apps
from django.db import connection
from core.schema_serializers import AnalystDataResponseSerializer
import logging
import time

logger = logging.getLogger('analyst')


class AnalystQueryThrottle(UserRateThrottle):
    """Rate limit for analyst AI queries - 30 requests per minute per user"""
    rate = '30/minute'


class AnalystDataThrottle(UserRateThrottle):
    """Rate limit for data loading - 10 requests per minute per user"""
    rate = '10/minute'


class AnonAnalystThrottle(AnonRateThrottle):
    """Rate limit for anonymous users - more restrictive"""
    rate = '5/minute'


class StartDatasetLoadView(APIView):
    """
    Start loading dataset for analyst assistant.
    Supports both authenticated and anonymous users (demo mode).
    """
    permission_classes = [AllowAny]  # Allow demo mode for unauthenticated users
    throttle_classes = [AnalystDataThrottle, AnonAnalystThrottle]
    serializer_class = AnalystDataResponseSerializer
    
    def get(self, request):
        start_time = time.time()
        try:
            result = load_all_datasets()
            
            # Add demo flag for unauthenticated users
            if not request.user.is_authenticated:
                result['isDemo'] = True
                result['message'] = result.get('message', '') + ' (Demo Mode)'
            
            # Log the operation
            elapsed = time.time() - start_time
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            row_count = sum(result.get('rows', {}).values()) if result.get('rows') else 0
            logger.info(f"[Analyst] Data loaded for user {user_id}: {row_count} rows in {elapsed:.2f}s")
            
            return Response(result)
        except Exception as e:
            logger.error(f"[Analyst] Failed to load data: {str(e)}")
            return Response(
                {"error": "Failed to load data. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalystDataView(APIView):
    """
    Get loaded analyst data.
    Requires authentication for production data.
    """
    permission_classes = [AllowAny]  # Allow demo mode
    throttle_classes = [AnalystDataThrottle, AnonAnalystThrottle]
    serializer_class = AnalystDataResponseSerializer
    
    def get(self, request):
        df = dataframe_cache.get("analysis_data")
        if df is not None:
            # Limit rows for anonymous users
            if not request.user.is_authenticated:
                return Response(df.head(100).to_dict(orient="records"))
            return Response(df.to_dict(orient="records"))
        return Response(
            {"error": "No analysis data found. Please refresh the page."},
            status=status.HTTP_404_NOT_FOUND
        )


class AnalystSchemaView(APIView):
    """
    Get database schema for the analyst assistant.
    Returns table names, columns, and metadata from actual Django models.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnalystDataThrottle]
    serializer_class = AnalystDataResponseSerializer
    
    # Map Django field types to SQL-like types
    FIELD_TYPE_MAP = {
        'AutoField': 'INTEGER',
        'BigAutoField': 'BIGINT',
        'IntegerField': 'INTEGER',
        'BigIntegerField': 'BIGINT',
        'SmallIntegerField': 'SMALLINT',
        'PositiveIntegerField': 'INTEGER',
        'FloatField': 'FLOAT',
        'DecimalField': 'DECIMAL',
        'CharField': 'VARCHAR',
        'TextField': 'TEXT',
        'DateField': 'DATE',
        'DateTimeField': 'TIMESTAMP',
        'TimeField': 'TIME',
        'BooleanField': 'BOOLEAN',
        'NullBooleanField': 'BOOLEAN',
        'UUIDField': 'UUID',
        'ForeignKey': 'UUID',
        'OneToOneField': 'UUID',
        'EmailField': 'VARCHAR',
        'URLField': 'VARCHAR',
        'SlugField': 'VARCHAR',
        'FileField': 'VARCHAR',
        'ImageField': 'VARCHAR',
        'JSONField': 'JSON',
    }
    
    # Model groups for categorization
    MODEL_GROUPS = {
        'accounting': ['Invoice', 'InvoiceLine', 'Payment', 'Expense', 'Account', 'JournalEntry', 'Contact', 'Receipt'],
        'business': ['Company', 'Client', 'Contract'],
        'users': ['User', 'UserProfile'],
        'hrms': ['Employee', 'Department', 'Position', 'Leave', 'Payroll'],
        'projects': ['Project', 'Task', 'TimeEntry'],
        'documents': ['Document', 'UploadedDocument'],
    }
    
    def get_model_group(self, model_name: str) -> str:
        """Determine group for a model based on its name"""
        for group, models in self.MODEL_GROUPS.items():
            if model_name in models:
                return group
        return 'other'
    
    def get(self, request):
        """Get the schema from Django models and loaded data"""
        try:
            schema_tables = []
            data_source = 'database'
            has_db_data = False
            
            # First, get schema from actual Django models
            relevant_apps = ['accounting', 'business', 'users', 'hrms', 'projects', 'documents']
            
            for app_label in relevant_apps:
                try:
                    app_config = apps.get_app_config(app_label)
                    for model in app_config.get_models():
                        model_name = model.__name__
                        table_name = model._meta.db_table
                        
                        # Get row count from DB
                        try:
                            row_count = model.objects.count()
                            if row_count > 0:
                                has_db_data = True
                        except Exception:
                            row_count = 0
                        
                        columns = []
                        for field in model._meta.get_fields():
                            if hasattr(field, 'column') and field.column:
                                field_type = type(field).__name__
                                sql_type = self.FIELD_TYPE_MAP.get(field_type, 'VARCHAR')
                                
                                # Add length for varchar types
                                if sql_type == 'VARCHAR' and hasattr(field, 'max_length') and field.max_length:
                                    sql_type = f'VARCHAR({field.max_length})'
                                elif sql_type == 'DECIMAL' and hasattr(field, 'max_digits'):
                                    decimal_places = getattr(field, 'decimal_places', 2)
                                    sql_type = f'DECIMAL({field.max_digits},{decimal_places})'
                                
                                is_primary = field.primary_key
                                is_foreign = field_type in ['ForeignKey', 'OneToOneField']
                                
                                columns.append({
                                    'name': field.column,
                                    'type': sql_type,
                                    'isPrimary': is_primary,
                                    'isForeign': is_foreign,
                                    'nullable': getattr(field, 'null', False),
                                    'description': getattr(field, 'verbose_name', field.name),
                                })
                        
                        if columns:
                            schema_tables.append({
                                'name': table_name,
                                'displayName': model_name,
                                'columns': columns,
                                'rowCount': row_count,
                                'group': app_label,
                                'description': model._meta.verbose_name or model_name,
                            })
                except LookupError:
                    continue
            
            # Also add schema from loaded DataFrames (for CSV fallback data)
            for name, df in dataframe_cache.items():
                if df is not None and not df.empty:
                    # Check if this is already in schema_tables
                    existing = next((t for t in schema_tables if t['name'] == name), None)
                    if not existing:
                        columns = []
                        for col in df.columns:
                            col_type = str(df[col].dtype)
                            if 'int' in col_type:
                                sql_type = 'INTEGER'
                            elif 'float' in col_type:
                                sql_type = 'DECIMAL'
                            elif 'datetime' in col_type:
                                sql_type = 'TIMESTAMP'
                            elif 'object' in col_type:
                                sql_type = 'VARCHAR'
                            elif 'bool' in col_type:
                                sql_type = 'BOOLEAN'
                            else:
                                sql_type = col_type.upper()
                            
                            columns.append({
                                'name': col,
                                'type': sql_type,
                                'isPrimary': col.endswith('_id') and col == f'{name.rstrip("s")}_id',
                                'isForeign': col.endswith('_id'),
                                'nullable': df[col].isnull().any(),
                            })
                        
                        schema_tables.append({
                            'name': name,
                            'displayName': name.replace('_', ' ').title(),
                            'columns': columns,
                            'rowCount': len(df),
                            'group': 'loaded_data',
                            'description': f'Loaded data: {name}',
                            'isFromCache': True,
                        })
            
            # Determine data source status
            if not has_db_data and dataframe_cache:
                data_source = 'csv_fallback'
            elif not has_db_data and not dataframe_cache:
                data_source = 'no_data'
            
            return Response({
                'tables': schema_tables,
                'dataSource': data_source,
                'hasDbData': has_db_data,
                'isDemo': not request.user.is_authenticated,
                'message': self._get_data_source_message(data_source, has_db_data),
            })
        except Exception as e:
            logger.error(f"[Analyst] Schema fetch failed: {str(e)}")
            return Response(
                {"error": f"Failed to fetch schema: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_data_source_message(self, data_source: str, has_db_data: bool) -> str:
        """Generate user-friendly message about data source"""
        if data_source == 'database' and has_db_data:
            return "Connected to database with real data / 已連接資料庫（真實數據）"
        elif data_source == 'csv_fallback':
            return "Using CSV demo data (no database records found) / 使用 CSV 示範數據（資料庫無記錄）"
        elif data_source == 'no_data':
            return "No data available. Please load data first. / 無可用數據，請先載入數據"
        return "Schema loaded / 結構已載入"


class AnalystDataStatusView(APIView):
    """
    Get the status of data loaded in the analyst assistant.
    Shows whether using DB data, CSV fallback, or no data.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnalystDataThrottle]
    serializer_class = AnalystDataResponseSerializer
    
    def get(self, request):
        """Check data status and source"""
        try:
            from accounting.models import Invoice, InvoiceLine, Contact
            
            # Check database for actual data
            db_stats = {
                'invoices': Invoice.objects.count(),
                'invoice_lines': InvoiceLine.objects.count(),
                'contacts': Contact.objects.count(),
            }
            has_db_data = any(v > 0 for v in db_stats.values())
            
            # Check cache
            cache_stats = {}
            for name, df in dataframe_cache.items():
                if df is not None and not df.empty:
                    cache_stats[name] = {
                        'rows': len(df),
                        'columns': df.columns.tolist(),
                        'dtypes': {col: str(df[col].dtype) for col in df.columns},
                    }
            
            # Determine data source
            if has_db_data:
                data_source = 'database'
                source_message = '已連接資料庫（真實數據）/ Connected to database with real data'
            elif cache_stats:
                data_source = 'csv_fallback'
                source_message = '使用 CSV 示範數據 / Using CSV demo data (no DB records)'
            else:
                data_source = 'no_data'
                source_message = '無可用數據，請先載入 / No data available. Call /start first.'
            
            return Response({
                'dataSource': data_source,
                'hasDbData': has_db_data,
                'dbStats': db_stats,
                'cacheStats': cache_stats,
                'message': source_message,
                'availableColumns': cache_stats.get('analysis_data', {}).get('columns', []),
                'recommendations': self._get_recommendations(data_source, has_db_data),
            })
        except Exception as e:
            logger.error(f"[Analyst] Data status check failed: {str(e)}")
            return Response(
                {"error": f"Failed to check data status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_recommendations(self, data_source: str, has_db_data: bool) -> list:
        """Generate recommendations based on data status"""
        recommendations = []
        if data_source == 'no_data':
            recommendations.append("Call GET /api/v1/analyst-assistant/start/ to load data")
            recommendations.append("Or add records to accounting tables (Invoice, InvoiceLine, Contact)")
        elif data_source == 'csv_fallback':
            recommendations.append("Add records to accounting tables to use real data")
            recommendations.append("Current analysis is based on demo CSV data")
        elif data_source == 'database':
            recommendations.append("Database data loaded successfully")
            recommendations.append("You can query real business data")
        return recommendations


class AnalystQueryView(APIView):
    """
    Process analyst queries with AI.
    Rate limited and logged for security.
    """
    permission_classes = [AllowAny]  # Allow demo mode
    throttle_classes = [AnalystQueryThrottle, AnonAnalystThrottle]
    serializer_class = AnalystQuerySerializer
    
    def post(self, request):
        start_time = time.time()
        serializer = AnalystQuerySerializer(data=request.data)
        
        if serializer.is_valid():
            query = serializer.validated_data["query"]
            
            # Log the query (sanitized)
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            logger.info(f"[Analyst] Query from user {user_id}: {query[:100]}...")
            
            try:
                result = handle_query_logic(query)
                
                # Log result type and timing
                elapsed = time.time() - start_time
                result_type = result.get('type', 'unknown')
                logger.info(f"[Analyst] Query completed for user {user_id}: type={result_type}, time={elapsed:.2f}s")
                
                return Response(result)
            except Exception as e:
                logger.error(f"[Analyst] Query failed for user {user_id}: {str(e)}")
                return Response(
                    {"type": "error", "message": "Query processing failed. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
