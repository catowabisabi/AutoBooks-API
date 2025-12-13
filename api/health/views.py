from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
import datetime


@extend_schema(
    tags=['Health'],
    summary='健康檢查 / Health Check',
    description='檢查系統是否正常運行。無需認證。\n\nCheck if the system is running normally. No authentication required.',
    responses=inline_serializer(
        name='HealthCheckResponse',
        fields={
            'status': serializers.CharField(),
            'message': serializers.CharField(),
            'timestamp': serializers.CharField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "status": "ok",
        "message": "ERP service is up and running",
        "timestamp": datetime.datetime.now().isoformat(),
    }, status=200)
