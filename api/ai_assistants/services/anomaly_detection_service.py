"""
Anomaly Detection Service
異常檢測服務

Features / 功能:
- Detect unusual transaction amounts / 檢測異常金額
- Detect duplicate receipts / 檢測重複收據
- Detect unusual patterns / 檢測異常模式
- AI-powered anomaly analysis / AI驅動的異常分析
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from django.db import models
from django.db.models import Avg, StdDev, Count, Sum, Q
from django.utils import timezone
from django.conf import settings

from ai_assistants.models import Receipt, ReceiptStatus, ExpenseCategory


class AnomalyType:
    """Anomaly type constants"""
    UNUSUAL_AMOUNT = 'UNUSUAL_AMOUNT'
    DUPLICATE_RECEIPT = 'DUPLICATE_RECEIPT'
    UNUSUAL_VENDOR = 'UNUSUAL_VENDOR'
    UNUSUAL_CATEGORY = 'UNUSUAL_CATEGORY'
    UNUSUAL_TIME = 'UNUSUAL_TIME'
    SUSPICIOUS_PATTERN = 'SUSPICIOUS_PATTERN'
    MISSING_INFO = 'MISSING_INFO'
    TAX_ANOMALY = 'TAX_ANOMALY'


class AnomalySeverity:
    """Anomaly severity levels"""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class AnomalyDetectionService:
    """
    Service for detecting anomalies in receipts and transactions
    收據和交易異常檢測服務
    """
    
    def __init__(self, user=None, threshold_multiplier: float = 2.0):
        self.user = user
        self.threshold_multiplier = threshold_multiplier
    
    def detect_all_anomalies(self, receipt: Receipt) -> List[Dict[str, Any]]:
        """
        Run all anomaly detection checks on a receipt
        對收據執行所有異常檢測
        """
        anomalies = []
        
        # Amount anomaly
        amount_anomaly = self.detect_amount_anomaly(receipt)
        if amount_anomaly:
            anomalies.append(amount_anomaly)
        
        # Duplicate check
        duplicates = self.detect_duplicate_receipt(receipt)
        if duplicates:
            anomalies.append(duplicates)
        
        # Missing info check
        missing_info = self.detect_missing_info(receipt)
        if missing_info:
            anomalies.append(missing_info)
        
        # Tax anomaly
        tax_anomaly = self.detect_tax_anomaly(receipt)
        if tax_anomaly:
            anomalies.append(tax_anomaly)
        
        # Weekend/Holiday check
        time_anomaly = self.detect_unusual_time(receipt)
        if time_anomaly:
            anomalies.append(time_anomaly)
        
        # Category pattern check
        category_anomaly = self.detect_unusual_category(receipt)
        if category_anomaly:
            anomalies.append(category_anomaly)
        
        return anomalies
    
    def detect_amount_anomaly(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect if the receipt amount is unusually high or low
        檢測金額是否異常
        """
        # Get statistics for this category
        stats = Receipt.objects.filter(
            category=receipt.category,
            status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED],
            total_amount__gt=0
        ).aggregate(
            avg_amount=Avg('total_amount'),
            std_amount=StdDev('total_amount'),
            count=Count('id'),
            max_amount=models.Max('total_amount'),
            min_amount=models.Min('total_amount')
        )
        
        if not stats['avg_amount'] or stats['count'] < 5:
            return None
        
        avg = float(stats['avg_amount'])
        std = float(stats['std_amount'] or avg * 0.5)
        amount = float(receipt.total_amount)
        
        # Check if outside threshold
        upper_threshold = avg + (std * self.threshold_multiplier)
        lower_threshold = max(0, avg - (std * self.threshold_multiplier))
        
        if amount > upper_threshold:
            deviation = (amount - avg) / std if std > 0 else 0
            return {
                'type': AnomalyType.UNUSUAL_AMOUNT,
                'severity': self._get_amount_severity(deviation),
                'title': '金額異常高 / Unusually High Amount',
                'description': f'此收據金額 ${amount:.2f} 高於同類別平均 ${avg:.2f} 的 {deviation:.1f} 個標準差',
                'details': {
                    'amount': amount,
                    'average': avg,
                    'std_deviation': std,
                    'threshold': upper_threshold,
                    'deviation_factor': deviation
                },
                'recommendation': '請確認此筆費用是否正確，建議審核後再核准'
            }
        elif amount < lower_threshold and amount > 0:
            deviation = (avg - amount) / std if std > 0 else 0
            return {
                'type': AnomalyType.UNUSUAL_AMOUNT,
                'severity': AnomalySeverity.LOW,
                'title': '金額異常低 / Unusually Low Amount',
                'description': f'此收據金額 ${amount:.2f} 低於同類別平均 ${avg:.2f}',
                'details': {
                    'amount': amount,
                    'average': avg,
                    'threshold': lower_threshold
                },
                'recommendation': '請確認收據是否完整'
            }
        
        return None
    
    def detect_duplicate_receipt(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect potential duplicate receipts
        檢測可能重複的收據
        """
        # Look for receipts with same vendor, amount, date
        duplicates = Receipt.objects.filter(
            ~Q(id=receipt.id),
            vendor_name__iexact=receipt.vendor_name,
            total_amount=receipt.total_amount,
            receipt_date=receipt.receipt_date
        ).exclude(
            status__in=[ReceiptStatus.REJECTED, ReceiptStatus.ERROR]
        )
        
        if duplicates.exists():
            return {
                'type': AnomalyType.DUPLICATE_RECEIPT,
                'severity': AnomalySeverity.HIGH,
                'title': '可能重複收據 / Possible Duplicate Receipt',
                'description': f'發現 {duplicates.count()} 筆相同供應商、金額、日期的收據',
                'details': {
                    'duplicate_ids': list(duplicates.values_list('id', flat=True)),
                    'vendor': receipt.vendor_name,
                    'amount': float(receipt.total_amount),
                    'date': str(receipt.receipt_date)
                },
                'recommendation': '請檢查是否為重複上傳或重複報銷'
            }
        
        # Also check for same receipt number
        if receipt.receipt_number:
            same_number = Receipt.objects.filter(
                ~Q(id=receipt.id),
                receipt_number=receipt.receipt_number
            ).exclude(
                status__in=[ReceiptStatus.REJECTED, ReceiptStatus.ERROR]
            )
            
            if same_number.exists():
                return {
                    'type': AnomalyType.DUPLICATE_RECEIPT,
                    'severity': AnomalySeverity.CRITICAL,
                    'title': '收據編號重複 / Duplicate Receipt Number',
                    'description': f'收據編號 {receipt.receipt_number} 已存在於系統中',
                    'details': {
                        'receipt_number': receipt.receipt_number,
                        'existing_ids': list(same_number.values_list('id', flat=True))
                    },
                    'recommendation': '請確認是否為同一張收據重複上傳'
                }
        
        return None
    
    def detect_missing_info(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect missing critical information
        檢測缺少的關鍵資訊
        """
        missing_fields = []
        
        if not receipt.vendor_name:
            missing_fields.append('供應商名稱 / Vendor Name')
        if not receipt.receipt_date:
            missing_fields.append('收據日期 / Receipt Date')
        if not receipt.total_amount or receipt.total_amount <= 0:
            missing_fields.append('金額 / Amount')
        if not receipt.receipt_number:
            missing_fields.append('收據編號 / Receipt Number')
        
        if missing_fields:
            severity = AnomalySeverity.HIGH if len(missing_fields) > 2 else AnomalySeverity.MEDIUM
            return {
                'type': AnomalyType.MISSING_INFO,
                'severity': severity,
                'title': '資訊不完整 / Missing Information',
                'description': f'缺少以下欄位: {", ".join(missing_fields)}',
                'details': {
                    'missing_fields': missing_fields,
                    'confidence_score': receipt.ai_confidence_score
                },
                'recommendation': '請補充缺少的資訊或人工審核收據圖片'
            }
        
        return None
    
    def detect_tax_anomaly(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect tax calculation anomalies
        檢測稅額計算異常
        """
        if receipt.total_amount <= 0:
            return None
        
        total = float(receipt.total_amount)
        tax = float(receipt.tax_amount or 0)
        tax_rate = float(receipt.tax_rate or 5)
        
        # Calculate expected tax
        expected_tax = (total / (1 + tax_rate / 100)) * (tax_rate / 100)
        
        # Allow 5% tolerance
        tolerance = expected_tax * 0.05
        
        if abs(tax - expected_tax) > tolerance and tax > 0:
            return {
                'type': AnomalyType.TAX_ANOMALY,
                'severity': AnomalySeverity.MEDIUM,
                'title': '稅額計算異常 / Tax Calculation Anomaly',
                'description': f'實際稅額 ${tax:.2f} 與預期稅額 ${expected_tax:.2f} 有差異',
                'details': {
                    'actual_tax': tax,
                    'expected_tax': expected_tax,
                    'tax_rate': tax_rate,
                    'total_amount': total,
                    'difference': abs(tax - expected_tax)
                },
                'recommendation': '請確認稅率設定是否正確'
            }
        
        return None
    
    def detect_unusual_time(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect receipts on unusual dates (weekends, holidays)
        檢測異常時間的收據
        """
        if not receipt.receipt_date:
            return None
        
        # Check if weekend
        weekday = receipt.receipt_date.weekday()
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            day_name = '星期六' if weekday == 5 else '星期日'
            return {
                'type': AnomalyType.UNUSUAL_TIME,
                'severity': AnomalySeverity.LOW,
                'title': '週末消費 / Weekend Transaction',
                'description': f'此收據日期為{day_name}',
                'details': {
                    'date': str(receipt.receipt_date),
                    'day_of_week': weekday
                },
                'recommendation': '週末費用可能需要額外說明用途'
            }
        
        return None
    
    def detect_unusual_category(self, receipt: Receipt) -> Optional[Dict[str, Any]]:
        """
        Detect if category pattern is unusual for this vendor
        檢測供應商分類是否異常
        """
        if not receipt.vendor_name:
            return None
        
        # Get most common category for this vendor
        vendor_stats = Receipt.objects.filter(
            vendor_name__iexact=receipt.vendor_name,
            status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED]
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        if not vendor_stats:
            return None
        
        most_common = vendor_stats[0]
        
        if most_common['category'] != receipt.category and most_common['count'] >= 3:
            return {
                'type': AnomalyType.UNUSUAL_CATEGORY,
                'severity': AnomalySeverity.LOW,
                'title': '分類與歷史不符 / Unusual Category',
                'description': f'此供應商通常分類為 {most_common["category"]}，但此收據分類為 {receipt.category}',
                'details': {
                    'current_category': receipt.category,
                    'common_category': most_common['category'],
                    'historical_count': most_common['count'],
                    'vendor': receipt.vendor_name
                },
                'recommendation': '請確認分類是否正確'
            }
        
        return None
    
    def _get_amount_severity(self, deviation: float) -> str:
        """
        Get severity level based on deviation
        根據偏差計算嚴重程度
        """
        if deviation > 4:
            return AnomalySeverity.CRITICAL
        elif deviation > 3:
            return AnomalySeverity.HIGH
        elif deviation > 2:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW
    
    def get_anomaly_summary(self, user, days: int = 30) -> Dict[str, Any]:
        """
        Get summary of anomalies for a user over a period
        獲取用戶一段時間內的異常摘要
        """
        start_date = timezone.now().date() - timedelta(days=days)
        
        receipts = Receipt.objects.filter(
            uploaded_by=user,
            created_at__date__gte=start_date
        )
        
        summary = {
            'total_receipts': receipts.count(),
            'anomalies_found': 0,
            'by_type': {},
            'by_severity': {
                AnomalySeverity.LOW: 0,
                AnomalySeverity.MEDIUM: 0,
                AnomalySeverity.HIGH: 0,
                AnomalySeverity.CRITICAL: 0
            },
            'period_days': days,
            'recommendations': []
        }
        
        for receipt in receipts:
            anomalies = self.detect_all_anomalies(receipt)
            summary['anomalies_found'] += len(anomalies)
            
            for anomaly in anomalies:
                # Count by type
                anomaly_type = anomaly['type']
                if anomaly_type not in summary['by_type']:
                    summary['by_type'][anomaly_type] = 0
                summary['by_type'][anomaly_type] += 1
                
                # Count by severity
                severity = anomaly['severity']
                summary['by_severity'][severity] += 1
        
        # Generate recommendations
        if summary['by_type'].get(AnomalyType.DUPLICATE_RECEIPT, 0) > 0:
            summary['recommendations'].append('建議檢查重複上傳的收據')
        if summary['by_type'].get(AnomalyType.MISSING_INFO, 0) > 3:
            summary['recommendations'].append('建議改善收據拍攝品質以提高OCR識別率')
        if summary['by_severity'][AnomalySeverity.CRITICAL] > 0:
            summary['recommendations'].append('有關鍵異常需要立即處理')
        
        return summary
    
    def ai_analyze_anomalies(self, receipt: Receipt, anomalies: List[Dict]) -> Dict[str, Any]:
        """
        Use AI to provide detailed analysis of anomalies
        使用AI提供詳細的異常分析
        """
        if not anomalies:
            return {
                'status': 'CLEAN',
                'message': '未發現異常',
                'risk_score': 0.0
            }
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""作為會計專家，分析以下收據異常情況並提供風險評估：

收據資訊：
- 供應商：{receipt.vendor_name}
- 金額：{receipt.total_amount} {receipt.currency}
- 日期：{receipt.receipt_date}
- 分類：{receipt.category}

發現的異常：
{json.dumps(anomalies, indent=2, ensure_ascii=False, default=str)}

請提供JSON格式的分析結果：
{{
    "risk_score": 0.0-1.0,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "summary": "簡短摘要",
    "analysis": "詳細分析",
    "recommendations": ["建議1", "建議2"],
    "should_flag_for_review": true/false
}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            
            try:
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].split("```")[0]
                else:
                    json_str = result_text
                
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                return {
                    'status': 'WARNING',
                    'risk_score': 0.5,
                    'analysis': result_text
                }
                
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'risk_score': 0.5,
                'should_flag_for_review': True
            }


# Convenience functions
def detect_receipt_anomalies(receipt: Receipt, user=None) -> List[Dict[str, Any]]:
    """
    Convenience function to detect all anomalies for a receipt
    """
    service = AnomalyDetectionService(user=user)
    return service.detect_all_anomalies(receipt)


def get_anomaly_summary(user, days: int = 30) -> Dict[str, Any]:
    """
    Convenience function to get anomaly summary
    """
    service = AnomalyDetectionService(user=user)
    return service.get_anomaly_summary(user, days)
