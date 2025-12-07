"""
AI Request Controls Module
AI 請求控制模組

Provides:
- Temperature and max_tokens validation
- User quota management
- Request audit logging
- Cost estimation
"""

import time
import hashlib
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from threading import Lock
from datetime import datetime, timedelta
from django.conf import settings
import logging

logger = logging.getLogger('ai_requests')


# Configuration
DEFAULT_TEMPERATURE = 0.7
MAX_TEMPERATURE = 1.5
MIN_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 2048
MAX_MAX_TOKENS = 8192
MIN_MAX_TOKENS = 50

# Quota settings (per day)
DEFAULT_DAILY_QUOTA = 100  # requests per day
DEFAULT_DAILY_TOKEN_QUOTA = 100000  # tokens per day
QUOTA_RESET_HOUR = 0  # Reset at midnight

# Cost estimation (per 1K tokens)
COST_PER_1K_INPUT = 0.0015  # GPT-4o-mini
COST_PER_1K_OUTPUT = 0.0075


@dataclass
class AIRequestConfig:
    """Configuration for AI request"""
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    model: str = "gpt-4o-mini"
    
    def validate(self) -> 'AIRequestConfig':
        """Validate and clamp values"""
        # Clamp temperature
        if self.temperature < MIN_TEMPERATURE:
            logger.warning(f"Temperature {self.temperature} below min, clamping to {MIN_TEMPERATURE}")
            self.temperature = MIN_TEMPERATURE
        elif self.temperature > MAX_TEMPERATURE:
            logger.warning(f"Temperature {self.temperature} above max, clamping to {MAX_TEMPERATURE}")
            self.temperature = MAX_TEMPERATURE
        
        # Clamp max_tokens
        if self.max_tokens < MIN_MAX_TOKENS:
            logger.warning(f"max_tokens {self.max_tokens} below min, clamping to {MIN_MAX_TOKENS}")
            self.max_tokens = MIN_MAX_TOKENS
        elif self.max_tokens > MAX_MAX_TOKENS:
            logger.warning(f"max_tokens {self.max_tokens} above max, clamping to {MAX_MAX_TOKENS}")
            self.max_tokens = MAX_MAX_TOKENS
        
        return self


@dataclass
class UserQuotaInfo:
    """Track user's quota usage"""
    user_id: str
    request_count: int = 0
    token_count: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    daily_request_limit: int = DEFAULT_DAILY_QUOTA
    daily_token_limit: int = DEFAULT_DAILY_TOKEN_QUOTA
    
    def should_reset(self) -> bool:
        """Check if quota should be reset (daily)"""
        now = datetime.now()
        if self.last_reset.date() < now.date():
            return True
        return False
    
    def reset(self) -> None:
        """Reset quota counters"""
        self.request_count = 0
        self.token_count = 0
        self.last_reset = datetime.now()
        logger.info(f"Quota reset for user {self.user_id}")
    
    def can_make_request(self) -> bool:
        """Check if user can make another request"""
        if self.should_reset():
            self.reset()
        return self.request_count < self.daily_request_limit
    
    def can_use_tokens(self, tokens: int) -> bool:
        """Check if user has enough token quota"""
        if self.should_reset():
            self.reset()
        return (self.token_count + tokens) <= self.daily_token_limit
    
    def consume(self, tokens: int = 0) -> None:
        """Record request and token usage"""
        if self.should_reset():
            self.reset()
        self.request_count += 1
        self.token_count += tokens
    
    def get_remaining(self) -> Dict[str, int]:
        """Get remaining quota"""
        if self.should_reset():
            self.reset()
        return {
            'requests_remaining': self.daily_request_limit - self.request_count,
            'tokens_remaining': self.daily_token_limit - self.token_count,
            'requests_used': self.request_count,
            'tokens_used': self.token_count,
        }


class QuotaManager:
    """
    Thread-safe quota manager for all users
    線程安全的配額管理器
    """
    
    def __init__(self):
        self._quotas: Dict[str, UserQuotaInfo] = {}
        self._lock = Lock()
    
    def get_quota(self, user_id: str) -> UserQuotaInfo:
        """Get or create quota info for user"""
        with self._lock:
            if user_id not in self._quotas:
                self._quotas[user_id] = UserQuotaInfo(user_id=user_id)
            return self._quotas[user_id]
    
    def check_quota(self, user_id: str, estimated_tokens: int = 0) -> Dict[str, Any]:
        """
        Check if user has quota available.
        
        Returns:
            Dict with 'allowed' (bool) and 'reason' if not allowed
        """
        quota = self.get_quota(user_id)
        
        if not quota.can_make_request():
            return {
                'allowed': False,
                'reason': 'Daily request limit reached',
                'remaining': quota.get_remaining()
            }
        
        if estimated_tokens > 0 and not quota.can_use_tokens(estimated_tokens):
            return {
                'allowed': False,
                'reason': 'Daily token limit reached',
                'remaining': quota.get_remaining()
            }
        
        return {
            'allowed': True,
            'remaining': quota.get_remaining()
        }
    
    def consume_quota(self, user_id: str, tokens: int = 0) -> Dict[str, int]:
        """Record usage and return remaining quota"""
        quota = self.get_quota(user_id)
        quota.consume(tokens)
        return quota.get_remaining()
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all users (admin)"""
        with self._lock:
            return {
                user_id: quota.get_remaining()
                for user_id, quota in self._quotas.items()
            }


# Global quota manager instance
quota_manager = QuotaManager()


@dataclass
class AuditLogEntry:
    """Audit log entry for AI requests"""
    timestamp: datetime
    user_id: str
    action: str
    model: str
    input_tokens: int
    output_tokens: int
    temperature: float
    max_tokens: int
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    request_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'action': self.action,
            'model': self.model,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message,
            'request_hash': self.request_hash,
            'estimated_cost': self.estimate_cost(),
        }
    
    def estimate_cost(self) -> float:
        """Estimate cost in USD"""
        input_cost = (self.input_tokens / 1000) * COST_PER_1K_INPUT
        output_cost = (self.output_tokens / 1000) * COST_PER_1K_OUTPUT
        return round(input_cost + output_cost, 6)


class AuditLogger:
    """
    Audit logger for AI requests
    AI 請求審計日誌記錄器
    """
    
    def __init__(self, max_entries: int = 10000):
        self._entries: list = []
        self._lock = Lock()
        self._max_entries = max_entries
    
    def log(self, entry: AuditLogEntry) -> None:
        """Add audit log entry"""
        with self._lock:
            self._entries.append(entry)
            
            # Trim if too many entries
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]
        
        # Also log to standard logger
        log_data = entry.to_dict()
        logger.info(f"AI Request: {json.dumps(log_data)}")
    
    def log_request(
        self,
        user_id: str,
        action: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        temperature: float,
        max_tokens: int,
        duration_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> AuditLogEntry:
        """Create and log an audit entry"""
        # Create hash of prompt for deduplication
        request_hash = None
        if prompt:
            request_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            user_id=user_id,
            action=action,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            request_hash=request_hash,
        )
        
        self.log(entry)
        return entry
    
    def get_user_logs(
        self, 
        user_id: str, 
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Get logs for a specific user"""
        with self._lock:
            user_entries = [e for e in self._entries if e.user_id == user_id]
            
            if since:
                user_entries = [e for e in user_entries if e.timestamp >= since]
            
            return [e.to_dict() for e in user_entries[-limit:]]
    
    def get_stats(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get aggregate statistics"""
        with self._lock:
            entries = self._entries
            
            if since:
                entries = [e for e in entries if e.timestamp >= since]
            
            if not entries:
                return {'total_requests': 0}
            
            total_input = sum(e.input_tokens for e in entries)
            total_output = sum(e.output_tokens for e in entries)
            total_cost = sum(e.estimate_cost() for e in entries)
            success_count = sum(1 for e in entries if e.success)
            
            return {
                'total_requests': len(entries),
                'success_count': success_count,
                'error_count': len(entries) - success_count,
                'total_input_tokens': total_input,
                'total_output_tokens': total_output,
                'total_tokens': total_input + total_output,
                'estimated_total_cost_usd': round(total_cost, 4),
                'avg_duration_ms': sum(e.duration_ms for e in entries) / len(entries),
            }


# Global audit logger instance
audit_logger = AuditLogger()


class AIRequestController:
    """
    Main controller for AI requests
    管理 AI 請求的主控制器
    """
    
    def __init__(self):
        self.quota_manager = quota_manager
        self.audit_logger = audit_logger
    
    def validate_config(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> AIRequestConfig:
        """Validate and return a config object"""
        config = AIRequestConfig(
            temperature=temperature or DEFAULT_TEMPERATURE,
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
            model=model or "gpt-4o-mini",
        )
        return config.validate()
    
    def check_request(
        self, 
        user_id: str, 
        estimated_tokens: int = 0
    ) -> Dict[str, Any]:
        """Check if request is allowed"""
        return self.quota_manager.check_quota(user_id, estimated_tokens)
    
    def record_request(
        self,
        user_id: str,
        action: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        temperature: float,
        max_tokens: int,
        duration_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> AuditLogEntry:
        """Record a completed request"""
        # Update quota
        total_tokens = input_tokens + output_tokens
        self.quota_manager.consume_quota(user_id, total_tokens)
        
        # Log the request
        return self.audit_logger.log_request(
            user_id=user_id,
            action=action,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            prompt=prompt,
        )
    
    def get_user_quota(self, user_id: str) -> Dict[str, Any]:
        """Get user's current quota status"""
        return self.quota_manager.check_quota(user_id)
    
    def get_user_audit_logs(
        self, 
        user_id: str, 
        days: int = 7
    ) -> list:
        """Get user's recent audit logs"""
        since = datetime.now() - timedelta(days=days)
        return self.audit_logger.get_user_logs(user_id, since)
    
    def get_admin_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get admin statistics"""
        since = datetime.now() - timedelta(days=days)
        return self.audit_logger.get_stats(since)


# Global controller instance
ai_request_controller = AIRequestController()


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count.
    Rule of thumb: ~4 characters per token for English, ~2 for CJK
    """
    # Count CJK characters
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - cjk_chars
    
    estimated = (cjk_chars / 2) + (other_chars / 4)
    return int(estimated) + 10  # Add buffer
