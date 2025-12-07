"""
Vendor Recognition Service
供應商智能辨識服務

Features / 功能:
- Recognize vendors from receipt data / 從收據識別供應商
- Auto-create Contact records / 自動建立聯絡人記錄
- Learn from historical data / 從歷史資料學習
- Suggest vendor matching / 建議供應商配對
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from accounting.models import Contact, Account, AccountType, AccountSubType
from ai_assistants.models import Receipt, ReceiptStatus


class VendorRecognitionService:
    """
    Service for recognizing and managing vendors from receipts
    從收據識別和管理供應商的服務
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def normalize_vendor_name(self, name: str) -> str:
        """
        Normalize vendor name for matching
        標準化供應商名稱用於配對
        """
        if not name:
            return ''
        
        # Convert to lowercase and strip
        normalized = name.lower().strip()
        
        # Remove common suffixes
        suffixes = [
            '有限公司', '股份有限公司', '公司', '企業', '商行', '店',
            'limited', 'ltd', 'inc', 'corp', 'co.', 'company',
            '分店', '門市', '專櫃'
        ]
        for suffix in suffixes:
            if normalized.endswith(suffix.lower()):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove special characters
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def find_matching_contact(self, vendor_name: str, tax_id: str = None) -> Optional[Contact]:
        """
        Find matching contact from existing database
        從現有資料庫找尋配對的聯絡人
        """
        if not vendor_name and not tax_id:
            return None
        
        # Try exact tax ID match first
        if tax_id:
            contact = Contact.objects.filter(tax_number=tax_id).first()
            if contact:
                return contact
        
        # Try exact name match
        if vendor_name:
            contact = Contact.objects.filter(
                Q(company_name__iexact=vendor_name) |
                Q(contact_name__iexact=vendor_name)
            ).first()
            if contact:
                return contact
        
        # Try normalized name match
        normalized = self.normalize_vendor_name(vendor_name)
        if normalized:
            contacts = Contact.objects.all()
            for contact in contacts:
                if (self.normalize_vendor_name(contact.company_name) == normalized or
                    self.normalize_vendor_name(contact.contact_name) == normalized):
                    return contact
        
        return None
    
    def suggest_matching_contacts(self, vendor_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest potentially matching contacts
        建議可能配對的聯絡人
        """
        if not vendor_name:
            return []
        
        suggestions = []
        normalized = self.normalize_vendor_name(vendor_name)
        
        # Search by partial name match
        contacts = Contact.objects.filter(
            Q(company_name__icontains=vendor_name) |
            Q(contact_name__icontains=vendor_name) |
            Q(company_name__icontains=normalized) |
            Q(contact_name__icontains=normalized)
        )[:limit]
        
        for contact in contacts:
            # Calculate similarity score
            similarity = self._calculate_similarity(vendor_name, contact.company_name or contact.contact_name)
            suggestions.append({
                'contact_id': str(contact.id),
                'company_name': contact.company_name,
                'contact_name': contact.contact_name,
                'tax_number': contact.tax_number,
                'similarity_score': similarity,
                'contact_type': contact.contact_type
            })
        
        # Sort by similarity
        suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return suggestions
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings
        計算兩個字串的相似度
        """
        if not str1 or not str2:
            return 0.0
        
        s1 = self.normalize_vendor_name(str1)
        s2 = self.normalize_vendor_name(str2)
        
        if s1 == s2:
            return 1.0
        
        # Simple Jaccard similarity on words
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    @transaction.atomic
    def create_contact_from_receipt(self, receipt: Receipt) -> Tuple[Optional[Contact], Optional[str]]:
        """
        Create a new contact from receipt vendor data
        從收據供應商資料建立新聯絡人
        """
        if not receipt.vendor_name:
            return None, "No vendor name in receipt"
        
        # Check if already exists
        existing = self.find_matching_contact(receipt.vendor_name, receipt.vendor_tax_id)
        if existing:
            return existing, "Contact already exists"
        
        try:
            # Get or create payable account
            payable_account = Account.objects.filter(
                account_subtype=AccountSubType.ACCOUNTS_PAYABLE.value
            ).first()
            
            contact = Contact.objects.create(
                contact_type='VENDOR',
                company_name=receipt.vendor_name,
                contact_name=receipt.vendor_name,
                phone=receipt.vendor_phone or '',
                address_line1=receipt.vendor_address or '',
                tax_number=receipt.vendor_tax_id or '',
                payable_account=payable_account,
                is_active=True,
                notes=f'Auto-created from receipt on {timezone.now().strftime("%Y-%m-%d")}'
            )
            
            return contact, None
            
        except Exception as e:
            return None, str(e)
    
    def update_contact_from_receipt(self, contact: Contact, receipt: Receipt) -> Contact:
        """
        Update contact information from receipt if more complete
        如果收據資訊更完整則更新聯絡人
        """
        updated = False
        
        # Update missing fields
        if not contact.phone and receipt.vendor_phone:
            contact.phone = receipt.vendor_phone
            updated = True
        
        if not contact.address_line1 and receipt.vendor_address:
            contact.address_line1 = receipt.vendor_address
            updated = True
        
        if not contact.tax_number and receipt.vendor_tax_id:
            contact.tax_number = receipt.vendor_tax_id
            updated = True
        
        if updated:
            contact.save()
        
        return contact
    
    def get_vendor_statistics(self, vendor_name: str = None, contact: Contact = None) -> Dict[str, Any]:
        """
        Get statistics for a vendor
        獲取供應商統計資料
        """
        if contact:
            receipts = Receipt.objects.filter(
                vendor_name__iexact=contact.company_name
            ).filter(
                status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED]
            )
        elif vendor_name:
            receipts = Receipt.objects.filter(
                vendor_name__iexact=vendor_name
            ).filter(
                status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED]
            )
        else:
            return {}
        
        from django.db.models import Avg, Sum, Min, Max, Count
        
        stats = receipts.aggregate(
            total_transactions=Count('id'),
            total_amount=Sum('total_amount'),
            avg_amount=Avg('total_amount'),
            min_amount=Min('total_amount'),
            max_amount=Max('total_amount'),
            first_transaction=Min('receipt_date'),
            last_transaction=Max('receipt_date')
        )
        
        # Get category breakdown
        category_breakdown = list(receipts.values('category').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        ).order_by('-count'))
        
        stats['category_breakdown'] = category_breakdown
        stats['most_common_category'] = category_breakdown[0]['category'] if category_breakdown else None
        
        return stats
    
    def learn_vendor_categories(self) -> Dict[str, str]:
        """
        Learn common categories for vendors from historical data
        從歷史資料學習供應商的常用分類
        """
        # Get vendor-category pairs with counts
        vendor_categories = Receipt.objects.filter(
            status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED],
            vendor_name__isnull=False
        ).exclude(
            vendor_name=''
        ).values('vendor_name', 'category').annotate(
            count=Count('id')
        ).order_by('vendor_name', '-count')
        
        # Build mapping
        vendor_mapping = {}
        for item in vendor_categories:
            vendor_name = self.normalize_vendor_name(item['vendor_name'])
            if vendor_name and vendor_name not in vendor_mapping:
                vendor_mapping[vendor_name] = item['category']
        
        return vendor_mapping
    
    def suggest_category_for_vendor(self, vendor_name: str) -> Optional[str]:
        """
        Suggest category based on vendor history
        根據供應商歷史建議分類
        """
        if not vendor_name:
            return None
        
        # Get most common category for this vendor
        normalized = self.normalize_vendor_name(vendor_name)
        
        result = Receipt.objects.filter(
            status__in=[ReceiptStatus.APPROVED, ReceiptStatus.POSTED]
        ).filter(
            Q(vendor_name__iexact=vendor_name) |
            Q(vendor_name__icontains=vendor_name)
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        return result['category'] if result else None
    
    def auto_process_vendor(self, receipt: Receipt) -> Dict[str, Any]:
        """
        Automatically process vendor: find/create contact, suggest category
        自動處理供應商：找尋/建立聯絡人，建議分類
        """
        result = {
            'vendor_name': receipt.vendor_name,
            'contact': None,
            'contact_created': False,
            'suggested_category': None,
            'vendor_stats': None
        }
        
        if not receipt.vendor_name:
            result['error'] = 'No vendor name'
            return result
        
        # Find or create contact
        contact = self.find_matching_contact(receipt.vendor_name, receipt.vendor_tax_id)
        
        if contact:
            # Update with any new info
            contact = self.update_contact_from_receipt(contact, receipt)
            result['contact'] = {
                'id': str(contact.id),
                'company_name': contact.company_name,
                'is_existing': True
            }
        else:
            # Create new contact
            contact, error = self.create_contact_from_receipt(receipt)
            if contact:
                result['contact'] = {
                    'id': str(contact.id),
                    'company_name': contact.company_name,
                    'is_existing': False
                }
                result['contact_created'] = True
            else:
                result['contact_error'] = error
        
        # Suggest category
        suggested = self.suggest_category_for_vendor(receipt.vendor_name)
        if suggested:
            result['suggested_category'] = suggested
        
        # Get vendor stats
        stats = self.get_vendor_statistics(vendor_name=receipt.vendor_name)
        result['vendor_stats'] = {
            'total_transactions': stats.get('total_transactions', 0),
            'total_amount': float(stats.get('total_amount', 0) or 0),
            'most_common_category': stats.get('most_common_category')
        }
        
        return result


# Convenience functions
def find_or_create_vendor(receipt: Receipt, user=None) -> Tuple[Optional[Contact], bool]:
    """
    Find or create vendor contact from receipt
    """
    service = VendorRecognitionService(user=user)
    contact = service.find_matching_contact(receipt.vendor_name, receipt.vendor_tax_id)
    
    if contact:
        service.update_contact_from_receipt(contact, receipt)
        return contact, False
    
    contact, error = service.create_contact_from_receipt(receipt)
    return contact, True if contact else False


def suggest_vendor_category(vendor_name: str) -> Optional[str]:
    """
    Suggest category for a vendor
    """
    service = VendorRecognitionService()
    return service.suggest_category_for_vendor(vendor_name)


def process_vendor_auto(receipt: Receipt) -> Dict[str, Any]:
    """
    Auto-process vendor from receipt
    """
    service = VendorRecognitionService()
    return service.auto_process_vendor(receipt)
