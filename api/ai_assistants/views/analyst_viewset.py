from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from ai_assistants.serializers.analyst_serializer import AnalystQuerySerializer
from ai_assistants.services.analyst_service import handle_query_logic, dataframe_cache
from ai_assistants.services.analyst_service import load_all_datasets
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
    Returns table names, columns, and metadata.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnalystDataThrottle]
    
    def get(self, request):
        """Get the schema of loaded data"""
        try:
            schema_tables = []
            
            # Get schema from dataframe_cache
            for name, df in dataframe_cache.items():
                if df is not None and not df.empty:
                    columns = []
                    for col in df.columns:
                        col_type = str(df[col].dtype)
                        is_primary = col.endswith('_id') and col.startswith(name.rstrip('s'))
                        is_foreign = col.endswith('_id') and not is_primary
                        
                        # Map pandas dtype to SQL-like type
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
                            'isPrimary': is_primary,
                            'isForeign': is_foreign,
                            'nullable': df[col].isnull().any(),
                        })
                    
                    # Determine group based on name
                    group = 'data'
                    if 'invoice' in name.lower() or 'sales' in name.lower():
                        group = 'sales'
                    elif 'customer' in name.lower() or 'contact' in name.lower():
                        group = 'crm'
                    elif 'product' in name.lower() or 'inventory' in name.lower():
                        group = 'inventory'
                    elif 'payment' in name.lower() or 'expense' in name.lower():
                        group = 'finance'
                    
                    schema_tables.append({
                        'name': name,
                        'columns': columns,
                        'rowCount': len(df),
                        'group': group,
                    })
            
            # If no data loaded, try to load it
            if not schema_tables:
                load_all_datasets()
                return self.get(request)  # Retry after loading
            
            return Response({
                'tables': schema_tables,
                'isDemo': not request.user.is_authenticated,
            })
        except Exception as e:
            logger.error(f"[Analyst] Schema fetch failed: {str(e)}")
            return Response(
                {"error": "Failed to fetch schema"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalystQueryView(APIView):
    """
    Process analyst queries with AI.
    Rate limited and logged for security.
    """
    permission_classes = [AllowAny]  # Allow demo mode
    throttle_classes = [AnalystQueryThrottle, AnonAnalystThrottle]
    
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
