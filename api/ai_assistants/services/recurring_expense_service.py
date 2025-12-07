"""
Recurring Expense Detection Service
重複費用檢測服務

Features / 功能:
- Detect recurring expenses / 檢測重複費用
- Predict future expenses / 預測未來費用
- Auto-categorize recurring items / 自動分類重複項目
- Generate recurring expense reports / 生成重複費用報表
"""

import json
from datetime import datetime, timedelta, date
from decimal import Decimal
from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple
from django.db import models
from django.db.models import Avg, Count, Sum, Q, F
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from django.conf import settings

from ai_assistants.models import Receipt, ReceiptStatus


class RecurringPattern:
    """Recurring pattern types"""
    WEEKLY = 'WEEKLY'
    BI_WEEKLY = 'BI_WEEKLY'
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    ANNUAL = 'ANNUAL'


class RecurringExpenseService:
    """
    Service for detecting and managing recurring expenses
    檢測和管理重複費用的服務
    """
    
    def __init__(self, user=None):
        self.user = user
        self.min_occurrences = 3  # Minimum times to consider recurring
    
    def detect_recurring_expenses(self, user, months: int = 12) -> List[Dict[str, Any]]:
        """
        Detect recurring expenses for a user
        檢測用戶的重複費用
        """
        start_date = timezone.now().date() - timedelta(days=months * 30)
        
        receipts = Receipt.objects.filter(
            uploaded_by=user,
            status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED],
            receipt_date__gte=start_date,
            vendor_name__isnull=False
        ).exclude(
            vendor_name=''
        ).order_by('vendor_name', 'receipt_date')
        
        # Group by vendor
        vendor_receipts = defaultdict(list)
        for receipt in receipts:
            vendor_receipts[receipt.vendor_name.lower()].append(receipt)
        
        recurring_expenses = []
        
        for vendor_name, vendor_list in vendor_receipts.items():
            if len(vendor_list) >= self.min_occurrences:
                pattern = self._analyze_pattern(vendor_list)
                if pattern:
                    recurring_expenses.append(pattern)
        
        # Sort by confidence
        recurring_expenses.sort(key=lambda x: x['confidence'], reverse=True)
        
        return recurring_expenses
    
    def _analyze_pattern(self, receipts: List[Receipt]) -> Optional[Dict[str, Any]]:
        """
        Analyze a list of receipts to detect recurring pattern
        分析收據列表以檢測重複模式
        """
        if len(receipts) < self.min_occurrences:
            return None
        
        # Sort by date
        sorted_receipts = sorted(receipts, key=lambda r: r.receipt_date or timezone.now().date())
        
        # Calculate intervals between receipts
        intervals = []
        for i in range(1, len(sorted_receipts)):
            if sorted_receipts[i].receipt_date and sorted_receipts[i-1].receipt_date:
                delta = (sorted_receipts[i].receipt_date - sorted_receipts[i-1].receipt_date).days
                if delta > 0:
                    intervals.append(delta)
        
        if not intervals:
            return None
        
        # Analyze amount consistency
        amounts = [float(r.total_amount) for r in sorted_receipts if r.total_amount]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        amount_variance = self._calculate_variance(amounts) if len(amounts) > 1 else 0
        
        # Detect pattern type and confidence
        pattern_type, avg_interval, confidence = self._detect_pattern_type(intervals)
        
        if confidence < 0.5:
            return None
        
        # Get categories
        categories = [r.category for r in sorted_receipts]
        most_common_category = max(set(categories), key=categories.count) if categories else None
        
        return {
            'vendor_name': sorted_receipts[0].vendor_name,
            'pattern_type': pattern_type,
            'average_interval_days': avg_interval,
            'average_amount': round(avg_amount, 2),
            'amount_variance': round(amount_variance, 2),
            'total_occurrences': len(sorted_receipts),
            'first_occurrence': str(sorted_receipts[0].receipt_date),
            'last_occurrence': str(sorted_receipts[-1].receipt_date),
            'most_common_category': most_common_category,
            'confidence': round(confidence, 2),
            'estimated_monthly_cost': self._estimate_monthly_cost(pattern_type, avg_amount, avg_interval),
            'estimated_annual_cost': self._estimate_annual_cost(pattern_type, avg_amount, avg_interval),
            'next_expected_date': self._predict_next_date(sorted_receipts[-1].receipt_date, avg_interval),
            'receipt_ids': [str(r.id) for r in sorted_receipts[-5:]]  # Last 5
        }
    
    def _detect_pattern_type(self, intervals: List[int]) -> Tuple[str, float, float]:
        """
        Detect the type of recurring pattern
        檢測重複模式的類型
        """
        if not intervals:
            return None, 0, 0
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Define pattern ranges (days)
        patterns = [
            (RecurringPattern.WEEKLY, 7, 2),        # 5-9 days
            (RecurringPattern.BI_WEEKLY, 14, 3),    # 11-17 days
            (RecurringPattern.MONTHLY, 30, 5),      # 25-35 days
            (RecurringPattern.QUARTERLY, 90, 15),   # 75-105 days
            (RecurringPattern.ANNUAL, 365, 30),     # 335-395 days
        ]
        
        best_pattern = None
        best_confidence = 0
        
        for pattern_type, expected, tolerance in patterns:
            if abs(avg_interval - expected) <= tolerance:
                # Calculate consistency
                variance = self._calculate_variance(intervals)
                consistency = 1 - min(variance / (expected * 0.3), 1)  # Normalize
                
                # Calculate how many match the pattern
                matches = sum(1 for i in intervals if abs(i - expected) <= tolerance)
                match_ratio = matches / len(intervals)
                
                confidence = (consistency * 0.5 + match_ratio * 0.5)
                
                if confidence > best_confidence:
                    best_pattern = pattern_type
                    best_confidence = confidence
        
        if best_pattern is None:
            # Try to detect irregular but consistent pattern
            variance = self._calculate_variance(intervals)
            if variance < avg_interval * 0.2:  # Low variance
                return 'IRREGULAR', avg_interval, 0.6
        
        return best_pattern, avg_interval, best_confidence
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values"""
        if len(values) < 2:
            return 0
        avg = sum(values) / len(values)
        return sum((x - avg) ** 2 for x in values) / len(values)
    
    def _estimate_monthly_cost(self, pattern_type: str, avg_amount: float, avg_interval: float) -> float:
        """Estimate monthly cost based on pattern"""
        if pattern_type == RecurringPattern.WEEKLY:
            return avg_amount * 4.33  # ~4.33 weeks per month
        elif pattern_type == RecurringPattern.BI_WEEKLY:
            return avg_amount * 2.17
        elif pattern_type == RecurringPattern.MONTHLY:
            return avg_amount
        elif pattern_type == RecurringPattern.QUARTERLY:
            return avg_amount / 3
        elif pattern_type == RecurringPattern.ANNUAL:
            return avg_amount / 12
        else:
            # Calculate based on average interval
            if avg_interval > 0:
                return avg_amount * (30 / avg_interval)
            return avg_amount
    
    def _estimate_annual_cost(self, pattern_type: str, avg_amount: float, avg_interval: float) -> float:
        """Estimate annual cost based on pattern"""
        monthly = self._estimate_monthly_cost(pattern_type, avg_amount, avg_interval)
        return round(monthly * 12, 2)
    
    def _predict_next_date(self, last_date: date, avg_interval: float) -> str:
        """Predict the next expected date"""
        if not last_date:
            return None
        next_date = last_date + timedelta(days=int(avg_interval))
        return str(next_date)
    
    def predict_future_expenses(self, user, months_ahead: int = 3) -> Dict[str, Any]:
        """
        Predict future expenses based on recurring patterns
        根據重複模式預測未來費用
        """
        recurring = self.detect_recurring_expenses(user)
        
        predictions = []
        total_predicted = 0
        
        today = timezone.now().date()
        end_date = today + timedelta(days=months_ahead * 30)
        
        for expense in recurring:
            if expense['confidence'] < 0.6:
                continue
            
            # Calculate expected occurrences
            interval = expense['average_interval_days']
            last_date = datetime.strptime(expense['last_occurrence'], '%Y-%m-%d').date()
            
            expected_dates = []
            current_date = last_date
            
            while current_date < end_date:
                current_date += timedelta(days=int(interval))
                if today <= current_date <= end_date:
                    expected_dates.append(str(current_date))
            
            if expected_dates:
                expected_total = len(expected_dates) * expense['average_amount']
                total_predicted += expected_total
                
                predictions.append({
                    'vendor_name': expense['vendor_name'],
                    'category': expense['most_common_category'],
                    'pattern_type': expense['pattern_type'],
                    'expected_amount': expense['average_amount'],
                    'expected_dates': expected_dates,
                    'expected_count': len(expected_dates),
                    'expected_total': round(expected_total, 2),
                    'confidence': expense['confidence']
                })
        
        # Group by month
        monthly_breakdown = defaultdict(float)
        for pred in predictions:
            for date_str in pred['expected_dates']:
                month_key = date_str[:7]  # YYYY-MM
                monthly_breakdown[month_key] += pred['expected_amount']
        
        return {
            'prediction_period': f'{today} to {end_date}',
            'total_predicted': round(total_predicted, 2),
            'predictions': predictions,
            'monthly_breakdown': dict(monthly_breakdown),
            'recurring_vendors_count': len(predictions)
        }
    
    def get_recurring_summary(self, user, months: int = 12) -> Dict[str, Any]:
        """
        Get summary of recurring expenses
        獲取重複費用摘要
        """
        recurring = self.detect_recurring_expenses(user, months)
        
        summary = {
            'total_recurring_items': len(recurring),
            'total_estimated_monthly': sum(e['estimated_monthly_cost'] for e in recurring),
            'total_estimated_annual': sum(e['estimated_annual_cost'] for e in recurring),
            'by_category': defaultdict(lambda: {'count': 0, 'monthly_cost': 0}),
            'by_pattern': defaultdict(int),
            'top_recurring': recurring[:5] if recurring else [],
            'analysis_period_months': months
        }
        
        for expense in recurring:
            category = expense['most_common_category'] or 'OTHER'
            summary['by_category'][category]['count'] += 1
            summary['by_category'][category]['monthly_cost'] += expense['estimated_monthly_cost']
            
            summary['by_pattern'][expense['pattern_type']] += 1
        
        # Convert to regular dict
        summary['by_category'] = dict(summary['by_category'])
        summary['by_pattern'] = dict(summary['by_pattern'])
        
        # Round totals
        summary['total_estimated_monthly'] = round(summary['total_estimated_monthly'], 2)
        summary['total_estimated_annual'] = round(summary['total_estimated_annual'], 2)
        
        return summary
    
    def ai_analyze_recurring(self, user, months: int = 12) -> Dict[str, Any]:
        """
        Use AI to analyze recurring expenses and provide recommendations
        使用AI分析重複費用並提供建議
        """
        recurring = self.detect_recurring_expenses(user, months)
        summary = self.get_recurring_summary(user, months)
        
        if not recurring:
            return {
                'status': 'NO_DATA',
                'message': '沒有足夠的資料來分析重複費用',
                'recommendations': []
            }
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""作為財務顧問，分析以下重複費用資料並提供建議：

重複費用摘要：
- 重複項目數量：{summary['total_recurring_items']}
- 估計月度支出：${summary['total_estimated_monthly']:.2f}
- 估計年度支出：${summary['total_estimated_annual']:.2f}

按類別分佈：
{json.dumps(summary['by_category'], indent=2, ensure_ascii=False)}

按頻率分佈：
{json.dumps(summary['by_pattern'], indent=2, ensure_ascii=False)}

主要重複費用（前5名）：
{json.dumps([{{
    'vendor': e['vendor_name'],
    'monthly': e['estimated_monthly_cost'],
    'category': e['most_common_category'],
    'pattern': e['pattern_type']
}} for e in recurring[:5]], indent=2, ensure_ascii=False)}

請提供JSON格式的分析：
{{
    "summary": "整體分析摘要（繁體中文）",
    "insights": ["重要發現1", "重要發現2"],
    "cost_optimization": ["節省建議1", "節省建議2"],
    "risks": ["潛在風險或異常"],
    "recommendations": [
        {{"type": "HIGH_PRIORITY", "suggestion": "建議內容"}},
        {{"type": "MEDIUM_PRIORITY", "suggestion": "建議內容"}}
    ],
    "predicted_trend": "費用趨勢預測"
}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            
            try:
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].split("```")[0]
                else:
                    json_str = result_text
                
                analysis = json.loads(json_str.strip())
                analysis['raw_summary'] = summary
                return analysis
                
            except json.JSONDecodeError:
                return {
                    'status': 'ANALYSIS_COMPLETE',
                    'summary': result_text,
                    'raw_summary': summary
                }
                
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'raw_summary': summary
            }


# Convenience functions
def detect_recurring(user, months: int = 12) -> List[Dict[str, Any]]:
    """
    Detect recurring expenses for a user
    """
    service = RecurringExpenseService(user=user)
    return service.detect_recurring_expenses(user, months)


def predict_expenses(user, months_ahead: int = 3) -> Dict[str, Any]:
    """
    Predict future expenses
    """
    service = RecurringExpenseService(user=user)
    return service.predict_future_expenses(user, months_ahead)


def get_recurring_report(user, months: int = 12) -> Dict[str, Any]:
    """
    Get comprehensive recurring expense report
    """
    service = RecurringExpenseService(user=user)
    return service.get_recurring_summary(user, months)
