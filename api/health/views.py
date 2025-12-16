from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from django.db import connection
from django.core.cache import cache
import datetime
import os

# Optional redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def check_database():
    """Check database connectivity"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok", "message": "Database connected"}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


def check_redis():
    """Check Redis connectivity (if configured)"""
    if not REDIS_AVAILABLE:
        return {"status": "not_configured", "message": "Redis module not installed"}
    
    redis_url = os.environ.get('REDIS_URL', os.environ.get('CELERY_BROKER_URL'))
    if not redis_url:
        return {"status": "not_configured", "message": "Redis not configured"}
    
    try:
        r = redis.from_url(redis_url)
        r.ping()
        return {"status": "ok", "message": "Redis connected"}
    except Exception as e:
        return {"status": "error", "message": f"Redis error: {str(e)}"}


def check_cache():
    """Check Django cache backend"""
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            return {"status": "ok", "message": "Cache working"}
        return {"status": "error", "message": "Cache read/write failed"}
    except Exception as e:
        return {"status": "error", "message": f"Cache error: {str(e)}"}


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


@extend_schema(
    tags=['Health'],
    summary='詳細健康檢查 / Detailed Health Check',
    description='檢查所有服務組件的狀態，包括資料庫、緩存等。無需認證。\n\nCheck status of all service components including database, cache, etc. No authentication required.',
    responses=inline_serializer(
        name='DetailedHealthCheckResponse',
        fields={
            'status': serializers.CharField(),
            'timestamp': serializers.CharField(),
            'services': serializers.DictField(),
            'version': serializers.CharField(),
        }
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def detailed_health_check(request):
    """Detailed health check with all service statuses"""
    
    # Check all services
    db_status = check_database()
    redis_status = check_redis()
    cache_status = check_cache()
    
    # Determine overall status
    services = {
        "api": {"status": "ok", "message": "API server running"},
        "database": db_status,
        "redis": redis_status,
        "cache": cache_status,
    }
    
    # Overall status is error if any critical service is down
    critical_services = [db_status]  # Database is critical
    overall_status = "ok"
    
    for service in critical_services:
        if service["status"] == "error":
            overall_status = "degraded"
            break
    
    # Check if all services are ok
    all_ok = all(s["status"] in ["ok", "not_configured"] for s in services.values())
    if not all_ok:
        overall_status = "degraded"
    
    return Response({
        "status": overall_status,
        "timestamp": datetime.datetime.now().isoformat(),
        "services": services,
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
    }, status=200 if overall_status == "ok" else 503)
