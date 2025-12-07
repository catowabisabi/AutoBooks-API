"""
Observability Module
可觀測性模組

Provides structured logging and metrics for:
- Data load times
- AI API call durations
- Token usage tracking
- Error monitoring
- Performance metrics
"""

import time
import json
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import logging

# Configure structured logger
logger = logging.getLogger('analyst.metrics')


@dataclass
class MetricEvent:
    """Structured metric event"""
    timestamp: str
    event_type: str
    duration_ms: float
    success: bool
    component: str
    action: str
    user_id: Optional[str] = None
    company_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class MetricsCollector:
    """
    Collects and stores metrics for observability.
    收集和存儲用於可觀測性的指標。
    """
    
    def __init__(self, max_events: int = 10000):
        self._events: list = []
        self._max_events = max_events
    
    def record(self, event: MetricEvent) -> None:
        """Record a metric event"""
        self._events.append(event)
        
        # Trim if too many events
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        # Log to structured logger
        logger.info(event.to_json())
    
    def get_events(
        self, 
        event_type: Optional[str] = None,
        component: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Get filtered events"""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if component:
            events = [e for e in events if e.component == component]
        
        if since:
            since_str = since.isoformat()
            events = [e for e in events if e.timestamp >= since_str]
        
        return [e.to_dict() for e in events[-limit:]]
    
    def get_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for recent events"""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        
        recent = [e for e in self._events if e.timestamp >= cutoff]
        
        if not recent:
            return {'total_events': 0}
        
        # Group by component
        by_component: Dict[str, list] = {}
        for event in recent:
            if event.component not in by_component:
                by_component[event.component] = []
            by_component[event.component].append(event)
        
        summary = {
            'total_events': len(recent),
            'success_count': sum(1 for e in recent if e.success),
            'error_count': sum(1 for e in recent if not e.success),
            'components': {}
        }
        
        for component, events in by_component.items():
            durations = [e.duration_ms for e in events]
            summary['components'][component] = {
                'count': len(events),
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'success_rate': sum(1 for e in events if e.success) / len(events) * 100,
            }
        
        return summary


# Global metrics collector
metrics_collector = MetricsCollector()


@contextmanager
def measure_time(
    event_type: str,
    component: str,
    action: str,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Context manager for timing operations.
    
    Usage:
        with measure_time('api_call', 'analyst', 'query_data') as timer:
            result = do_something()
            timer.set_detail('rows', len(result))
    """
    start_time = time.time()
    result = {'success': True, 'error_message': None, 'extra_details': {}}
    
    class Timer:
        def set_success(self, success: bool):
            result['success'] = success
        
        def set_error(self, error: str):
            result['success'] = False
            result['error_message'] = error
        
        def set_detail(self, key: str, value: Any):
            result['extra_details'][key] = value
    
    timer = Timer()
    
    try:
        yield timer
    except Exception as e:
        result['success'] = False
        result['error_message'] = str(e)
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        
        # Merge details
        final_details = details or {}
        final_details.update(result['extra_details'])
        
        event = MetricEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            duration_ms=duration_ms,
            success=result['success'],
            component=component,
            action=action,
            user_id=user_id,
            company_id=company_id,
            details=final_details if final_details else None,
            error_message=result['error_message'],
        )
        
        metrics_collector.record(event)


def track_performance(
    event_type: str,
    component: str,
    include_args: bool = False
):
    """
    Decorator for tracking function performance.
    
    Usage:
        @track_performance('database', 'accounting')
        def load_invoices():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            action = func.__name__
            details = {}
            
            if include_args:
                details['args_count'] = len(args)
                details['kwargs_keys'] = list(kwargs.keys())
            
            start_time = time.time()
            success = True
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                event = MetricEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type=event_type,
                    duration_ms=duration_ms,
                    success=success,
                    component=component,
                    action=action,
                    details=details if details else None,
                    error_message=error_msg,
                )
                
                metrics_collector.record(event)
        
        return wrapper
    return decorator


def track_data_load(func: Callable) -> Callable:
    """Decorator specifically for data load operations"""
    return track_performance('data_load', 'analyst')(func)


def track_ai_call(func: Callable) -> Callable:
    """Decorator specifically for AI API calls"""
    return track_performance('ai_call', 'openai')(func)


def track_database(func: Callable) -> Callable:
    """Decorator specifically for database operations"""
    return track_performance('database', 'accounting')(func)


# Token usage tracking
class TokenUsageTracker:
    """
    Track token usage across AI calls.
    追蹤 AI 呼叫的 token 使用量。
    """
    
    def __init__(self):
        self._daily_usage: Dict[str, Dict[str, int]] = {}
    
    def record(
        self, 
        user_id: str, 
        input_tokens: int, 
        output_tokens: int,
        model: str = "gpt-4o-mini"
    ) -> None:
        """Record token usage"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"{today}:{user_id}"
        
        if key not in self._daily_usage:
            self._daily_usage[key] = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'calls': 0,
                'date': today,
                'user_id': user_id,
            }
        
        self._daily_usage[key]['input_tokens'] += input_tokens
        self._daily_usage[key]['output_tokens'] += output_tokens
        self._daily_usage[key]['total_tokens'] += input_tokens + output_tokens
        self._daily_usage[key]['calls'] += 1
        
        logger.info(json.dumps({
            'event': 'token_usage',
            'user_id': user_id,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
        }))
    
    def get_user_usage(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get user's token usage for recent days"""
        from datetime import timedelta
        
        usage = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            key = f"{date}:{user_id}"
            
            if key in self._daily_usage:
                usage.append(self._daily_usage[key])
            else:
                usage.append({
                    'date': date,
                    'user_id': user_id,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'calls': 0,
                })
        
        return {
            'user_id': user_id,
            'days': days,
            'usage': usage,
            'total_tokens': sum(u['total_tokens'] for u in usage),
            'total_calls': sum(u['calls'] for u in usage),
        }
    
    def get_all_usage(self, days: int = 7) -> Dict[str, Any]:
        """Get all users' token usage for recent days"""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        recent = {
            k: v for k, v in self._daily_usage.items() 
            if v['date'] >= cutoff
        }
        
        total_tokens = sum(u['total_tokens'] for u in recent.values())
        total_calls = sum(u['calls'] for u in recent.values())
        
        return {
            'days': days,
            'total_tokens': total_tokens,
            'total_calls': total_calls,
            'daily_breakdown': list(recent.values()),
        }


# Global token tracker
token_tracker = TokenUsageTracker()


# Health check endpoint helper
def get_health_metrics() -> Dict[str, Any]:
    """Get health check metrics"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics_collector.get_summary(minutes=5),
        'token_usage': token_tracker.get_all_usage(days=1),
    }
