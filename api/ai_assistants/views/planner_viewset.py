from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import numpy as np
from ai_assistants.serializers.planner_serializer import PlannerQuerySerializer
from ai_assistants.services.planner_service import handle_query_logic, dataframe_cache
from ai_assistants.services.planner_service import load_all_datasets


class StartDatasetLoadView(APIView):
    def get(self, request):
        try:
            result = load_all_datasets()
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlannerDataView(APIView):
    def get(self, request):
        df = dataframe_cache.get("planner_data")
        if df is not None:
            # Replace NaN, Infinity, -Infinity with None before serialization
            df_copy = df.copy()
            # Replace infinite values with None
            df_copy = df_copy.replace([float('inf'), float('-inf')], None)
            # Replace NaN values with None
            df_copy = df_copy.replace({pd.NA: None, np.nan: None})
            return Response(df_copy.to_dict(orient="records"))
        return Response({"error": "No planner data found. Call /start first."}, status=status.HTTP_404_NOT_FOUND)


class PlannerQueryView(APIView):
    def post(self, request):
        serializer = PlannerQuerySerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data["query"]
            result = handle_query_logic(query)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
