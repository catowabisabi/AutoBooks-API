"""
Root API View
"""
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


@extend_schema(exclude=True)  # 不在 API 文檔中顯示
@api_view(['GET'])
@permission_classes([AllowAny])
def root_view(request):
    """
    Root endpoint - Returns simple server status
    """
    return HttpResponse("Server is running", content_type="text/plain")
