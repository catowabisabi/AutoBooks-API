from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import datetime


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "status": "ok",
        "message": "ERP service is up and running",
        "timestamp": datetime.datetime.now().isoformat(),
    }, status=200)
