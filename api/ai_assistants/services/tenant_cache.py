"""
Tenant-Isolated DataFrame Cache
多租戶 DataFrame 緩存

Provides secure, isolated caching for analyst dataframes per user/tenant.
"""

import time
import threading
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logger = logging.getLogger('analyst.cache')


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    
    def touch(self):
        """Update last access time"""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def is_expired(self, ttl: float) -> bool:
        """Check if entry is expired"""
        return time.time() - self.created_at > ttl


class TenantCache:
    """
    Thread-safe, tenant-isolated cache with TTL and size limits.
    
    Features:
    - Per-user/tenant isolation
    - TTL (Time To Live) for entries
    - Maximum cache size limit
    - LRU eviction policy
    - Thread-safe operations
    """
    
    # Default configuration
    DEFAULT_TTL = 3600  # 1 hour
    DEFAULT_MAX_SIZE = 100 * 1024 * 1024  # 100MB per tenant
    DEFAULT_MAX_ENTRIES = 50  # Max entries per tenant
    GLOBAL_MAX_SIZE = 1024 * 1024 * 1024  # 1GB total
    
    def __init__(
        self,
        ttl: float = DEFAULT_TTL,
        max_size_per_tenant: int = DEFAULT_MAX_SIZE,
        max_entries_per_tenant: int = DEFAULT_MAX_ENTRIES,
        global_max_size: int = GLOBAL_MAX_SIZE
    ):
        self.ttl = ttl
        self.max_size_per_tenant = max_size_per_tenant
        self.max_entries_per_tenant = max_entries_per_tenant
        self.global_max_size = global_max_size
        
        # Tenant -> { key -> CacheEntry }
        self._cache: Dict[str, OrderedDict[str, CacheEntry]] = {}
        self._lock = threading.RLock()
        self._total_size = 0
        
        logger.info(f"TenantCache initialized: ttl={ttl}s, max_size={max_size_per_tenant/1024/1024:.1f}MB/tenant")
    
    def _get_tenant_id(self, user_id: Optional[int]) -> str:
        """Get tenant identifier from user ID"""
        if user_id is None:
            return "anonymous"
        return f"user_{user_id}"
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate memory size of data"""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            return data.memory_usage(deep=True).sum()
        elif isinstance(data, dict):
            return len(str(data))
        else:
            return len(str(data))
    
    def _evict_lru(self, tenant_id: str) -> None:
        """Evict least recently used entries for tenant"""
        if tenant_id not in self._cache:
            return
        
        tenant_cache = self._cache[tenant_id]
        
        # Sort by last_accessed and remove oldest
        if len(tenant_cache) > 0:
            oldest_key = next(iter(tenant_cache))
            entry = tenant_cache.pop(oldest_key)
            self._total_size -= entry.size_bytes
            logger.debug(f"Evicted LRU entry: {tenant_id}/{oldest_key}")
    
    def _cleanup_expired(self, tenant_id: str) -> None:
        """Remove expired entries for tenant"""
        if tenant_id not in self._cache:
            return
        
        expired_keys = [
            key for key, entry in self._cache[tenant_id].items()
            if entry.is_expired(self.ttl)
        ]
        
        for key in expired_keys:
            entry = self._cache[tenant_id].pop(key)
            self._total_size -= entry.size_bytes
            logger.debug(f"Expired entry removed: {tenant_id}/{key}")
    
    def get(self, user_id: Optional[int], key: str) -> Optional[Any]:
        """
        Get cached data for user.
        
        Args:
            user_id: User ID (None for anonymous)
            key: Cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        tenant_id = self._get_tenant_id(user_id)
        
        with self._lock:
            if tenant_id not in self._cache:
                return None
            
            if key not in self._cache[tenant_id]:
                return None
            
            entry = self._cache[tenant_id][key]
            
            # Check expiration
            if entry.is_expired(self.ttl):
                self._cache[tenant_id].pop(key)
                self._total_size -= entry.size_bytes
                logger.debug(f"Cache miss (expired): {tenant_id}/{key}")
                return None
            
            # Update access time and move to end (LRU)
            entry.touch()
            self._cache[tenant_id].move_to_end(key)
            
            logger.debug(f"Cache hit: {tenant_id}/{key}")
            return entry.data
    
    def set(self, user_id: Optional[int], key: str, data: Any) -> bool:
        """
        Set cached data for user.
        
        Args:
            user_id: User ID (None for anonymous)
            key: Cache key
            data: Data to cache
        
        Returns:
            True if cached successfully
        """
        tenant_id = self._get_tenant_id(user_id)
        size_bytes = self._estimate_size(data)
        
        with self._lock:
            # Initialize tenant cache if needed
            if tenant_id not in self._cache:
                self._cache[tenant_id] = OrderedDict()
            
            # Clean up expired entries
            self._cleanup_expired(tenant_id)
            
            # Check size limits
            if size_bytes > self.max_size_per_tenant:
                logger.warning(f"Data too large for cache: {size_bytes} bytes")
                return False
            
            # Evict if necessary
            while len(self._cache[tenant_id]) >= self.max_entries_per_tenant:
                self._evict_lru(tenant_id)
            
            # Check global size limit
            while self._total_size + size_bytes > self.global_max_size:
                # Evict from any tenant
                for tid in list(self._cache.keys()):
                    if self._cache[tid]:
                        self._evict_lru(tid)
                        break
                else:
                    break
            
            # Remove existing entry if present
            if key in self._cache[tenant_id]:
                old_entry = self._cache[tenant_id].pop(key)
                self._total_size -= old_entry.size_bytes
            
            # Add new entry
            entry = CacheEntry(data=data, size_bytes=size_bytes)
            self._cache[tenant_id][key] = entry
            self._total_size += size_bytes
            
            logger.debug(f"Cache set: {tenant_id}/{key} ({size_bytes} bytes)")
            return True
    
    def delete(self, user_id: Optional[int], key: str) -> bool:
        """Delete cached data for user"""
        tenant_id = self._get_tenant_id(user_id)
        
        with self._lock:
            if tenant_id not in self._cache:
                return False
            
            if key not in self._cache[tenant_id]:
                return False
            
            entry = self._cache[tenant_id].pop(key)
            self._total_size -= entry.size_bytes
            
            logger.debug(f"Cache deleted: {tenant_id}/{key}")
            return True
    
    def clear_tenant(self, user_id: Optional[int]) -> None:
        """Clear all cache for a user"""
        tenant_id = self._get_tenant_id(user_id)
        
        with self._lock:
            if tenant_id in self._cache:
                for entry in self._cache[tenant_id].values():
                    self._total_size -= entry.size_bytes
                del self._cache[tenant_id]
                logger.info(f"Cache cleared for tenant: {tenant_id}")
    
    def clear_all(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()
            self._total_size = 0
            logger.info("Cache cleared completely")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            tenant_stats = {}
            for tenant_id, cache in self._cache.items():
                tenant_stats[tenant_id] = {
                    'entries': len(cache),
                    'size_bytes': sum(e.size_bytes for e in cache.values())
                }
            
            return {
                'total_tenants': len(self._cache),
                'total_entries': sum(len(c) for c in self._cache.values()),
                'total_size_bytes': self._total_size,
                'total_size_mb': self._total_size / 1024 / 1024,
                'tenants': tenant_stats
            }


# Global cache instance
_cache_instance: Optional[TenantCache] = None


def get_cache() -> TenantCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TenantCache()
    return _cache_instance


def get_cached_dataframe(user_id: Optional[int], key: str):
    """Convenience function to get cached dataframe"""
    return get_cache().get(user_id, key)


def set_cached_dataframe(user_id: Optional[int], key: str, df):
    """Convenience function to set cached dataframe"""
    return get_cache().set(user_id, key, df)


def clear_user_cache(user_id: Optional[int]):
    """Convenience function to clear user cache"""
    get_cache().clear_tenant(user_id)
