"""
Root API View
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, inline_serializer


@extend_schema(
    tags=['Health'],
    summary='API 狀態 / API Status',
    description='根端點，返回 API 服務器運行狀態。無需認證。\n\nRoot endpoint, returns API server running status. No authentication required.',
    responses=inline_serializer(
        name='RootResponse',
        fields={
            'message': serializers.CharField(),
            'version': serializers.CharField(),
            'status': serializers.CharField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def root_view(request):
    """
    Root endpoint - Returns API status
    """
    return Response(
        {
            "message": "AutoBooks API server is running",
            "version": "1.0",
            "status": "active"
        },
        status=status.HTTP_200_OK
    )
