"""
Report Cache Service
====================
Caching layer for large report data using Django cache framework.
Supports Redis for production and local memory for development.
"""

import hashlib
import json
from datetime import timedelta
from typing import Dict, Optional, Any
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from ..models import Report, ReportStatus


class ReportCacheService:
    """
    Service for caching report data.
    Uses Django's cache framework which can be configured for Redis in production.
    """
    
    # Cache key prefixes
    PREFIX_REPORT_DATA = 'report:data:'
    PREFIX_REPORT_SUMMARY = 'report:summary:'
    PREFIX_REPORT_STATUS = 'report:status:'
    
    # Default cache TTL (24 hours)
    DEFAULT_TTL = 60 * 60 * 24
    
    # Large report threshold (cache for longer)
    LARGE_REPORT_THRESHOLD = 100000  # 100KB
    LARGE_REPORT_TTL = 60 * 60 * 48  # 48 hours
    
    def __init__(self):
        pass
    
    # =================================================================
    # Cache Key Generation
    # =================================================================
    
    def _get_report_data_key(self, report_id: str) -> str:
        """Generate cache key for report data"""
        return f"{self.PREFIX_REPORT_DATA}{report_id}"
    
    def _get_report_summary_key(self, report_id: str) -> str:
        """Generate cache key for report summary"""
        return f"{self.PREFIX_REPORT_SUMMARY}{report_id}"
    
    def _get_report_status_key(self, report_id: str) -> str:
        """Generate cache key for report generation status"""
        return f"{self.PREFIX_REPORT_STATUS}{report_id}"
    
    def _generate_filter_hash(self, filters: Dict) -> str:
        """Generate a hash of filter parameters for cache key"""
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        return hashlib.md5(filter_str.encode()).hexdigest()[:16]
    
    # =================================================================
    # Report Data Caching
    # =================================================================
    
    def get_cached_report_data(self, report: Report) -> Optional[Dict]:
        """
        Get cached report data if available and valid.
        Returns None if not cached or expired.
        """
        if not report.cache_key:
            return None
        
        # Check if cache is still valid
        if report.cache_expires_at and timezone.now() > report.cache_expires_at:
            self.invalidate_report_cache(report)
            return None
        
        cached = cache.get(report.cache_key)
        if cached:
            # Verify data hash if available
            if report.data_hash:
                cached_hash = self._calculate_hash(cached)
                if cached_hash != report.data_hash:
                    # Data mismatch, invalidate
                    self.invalidate_report_cache(report)
                    return None
            return cached
        
        return None
    
    def cache_report_data(
        self,
        report: Report,
        data: Dict,
        ttl: Optional[int] = None
    ) -> str:
        """
        Cache report data and return the cache key.
        Automatically adjusts TTL based on data size.
        """
        cache_key = self._get_report_data_key(str(report.id))
        
        # Calculate TTL based on data size
        data_size = len(json.dumps(data, default=str))
        if ttl is None:
            ttl = self.LARGE_REPORT_TTL if data_size > self.LARGE_REPORT_THRESHOLD else self.DEFAULT_TTL
        
        # Store in cache
        cache.set(cache_key, data, ttl)
        
        # Update report with cache info
        report.cache_key = cache_key
        report.cache_expires_at = timezone.now() + timedelta(seconds=ttl)
        report.data_hash = self._calculate_hash(data)
        report.save(update_fields=['cache_key', 'cache_expires_at', 'data_hash'])
        
        return cache_key
    
    def invalidate_report_cache(self, report: Report) -> None:
        """Invalidate cached data for a report"""
        if report.cache_key:
            cache.delete(report.cache_key)
        
        # Also delete summary cache
        cache.delete(self._get_report_summary_key(str(report.id)))
        
        report.cache_key = ''
        report.cache_expires_at = None
        report.save(update_fields=['cache_key', 'cache_expires_at'])
    
    # =================================================================
    # Report Summary Caching
    # =================================================================
    
    def get_cached_summary(self, report: Report) -> Optional[Dict]:
        """Get cached summary totals"""
        key = self._get_report_summary_key(str(report.id))
        return cache.get(key)
    
    def cache_summary(self, report: Report, summary: Dict, ttl: int = None) -> None:
        """Cache summary totals (lighter weight than full data)"""
        key = self._get_report_summary_key(str(report.id))
        cache.set(key, summary, ttl or self.DEFAULT_TTL)
    
    # =================================================================
    # Generation Status Tracking
    # =================================================================
    
    def set_generation_status(
        self,
        report_id: str,
        status: str,
        progress: int = 0,
        message: str = ''
    ) -> None:
        """
        Set report generation status for real-time progress tracking.
        Short TTL since this is temporary status.
        """
        key = self._get_report_status_key(report_id)
        cache.set(key, {
            'status': status,
            'progress': progress,
            'message': message,
            'updated_at': timezone.now().isoformat()
        }, timeout=300)  # 5 minute TTL
    
    def get_generation_status(self, report_id: str) -> Optional[Dict]:
        """Get current generation status"""
        key = self._get_report_status_key(report_id)
        return cache.get(key)
    
    def clear_generation_status(self, report_id: str) -> None:
        """Clear generation status after completion"""
        key = self._get_report_status_key(report_id)
        cache.delete(key)
    
    # =================================================================
    # Query Result Caching
    # =================================================================
    
    def cache_query_result(
        self,
        query_hash: str,
        result: Any,
        ttl: int = 3600
    ) -> None:
        """
        Cache expensive query results.
        Useful for aggregate queries used in multiple reports.
        """
        key = f"report:query:{query_hash}"
        cache.set(key, result, ttl)
    
    def get_cached_query_result(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        key = f"report:query:{query_hash}"
        return cache.get(key)
    
    # =================================================================
    # Bulk Operations
    # =================================================================
    
    def invalidate_tenant_reports(self, tenant_id: str) -> None:
        """
        Invalidate all cached reports for a tenant.
        Called when underlying data changes significantly.
        """
        # Note: This requires cache backend that supports pattern deletion
        # For Redis: redis.delete(*redis.keys(f"report:*:{tenant_id}:*"))
        # For now, we rely on individual cache expiration
        pass
    
    def invalidate_by_date_range(
        self,
        tenant_id: str,
        start_date,
        end_date
    ) -> int:
        """
        Invalidate cached reports that overlap with a date range.
        Called when journal entries are posted/modified.
        Returns count of invalidated reports.
        """
        from ..models import Report
        
        reports = Report.objects.filter(
            tenant_id=tenant_id,
            cache_key__isnull=False
        ).filter(
            # Reports that overlap with the modified date range
            period_start__lte=end_date,
            period_end__gte=start_date
        )
        
        count = 0
        for report in reports:
            self.invalidate_report_cache(report)
            count += 1
        
        return count
    
    def warm_cache(self, report: Report) -> bool:
        """
        Pre-warm cache for a report.
        Called before anticipated access or during off-peak hours.
        """
        if report.cached_data:
            return self.cache_report_data(report, report.cached_data) is not None
        return False
    
    # =================================================================
    # Cache Statistics
    # =================================================================
    
    def get_cache_stats(self, tenant_id: Optional[str] = None) -> Dict:
        """
        Get cache statistics for monitoring.
        """
        from ..models import Report
        
        query = Report.objects.all()
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        
        total = query.count()
        cached = query.exclude(cache_key='').exclude(cache_key__isnull=True).count()
        expired = query.filter(
            cache_expires_at__lt=timezone.now()
        ).exclude(cache_key='').count()
        
        return {
            'total_reports': total,
            'cached_reports': cached,
            'expired_cache': expired,
            'cache_hit_rate': (cached - expired) / total if total > 0 else 0
        }
    
    # =================================================================
    # Helper Methods
    # =================================================================
    
    def _calculate_hash(self, data: Dict) -> str:
        """Calculate SHA256 hash of data for verification"""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data in bytes"""
        return len(json.dumps(data, default=str).encode('utf-8'))
