from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ai_assistants.serializers.analyst_serializer import AnalystQuerySerializer
from ai_assistants.services.analyst_service import handle_query_logic, dataframe_cache
from ai_assistants.services.analyst_service import load_all_datasets


class StartDatasetLoadView(APIView):
    def get(self, request):
        try:
            result = load_all_datasets()
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalystDataView(APIView):
    def get(self, request):
        df = dataframe_cache.get("analysis_data")
        if df is not None:
            return Response(df.to_dict(orient="records"))
        return Response({"error": "No analysis data found. Call /start first."}, status=status.HTTP_404_NOT_FOUND)


class AnalystQueryView(APIView):
    def post(self, request):
        serializer = AnalystQuerySerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data["query"]
            result = handle_query_logic(query)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
