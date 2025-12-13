"""
Custom Schema Generator for API Documentation
自定義 Schema 生成器，用於 API 文檔
"""
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView


# Tag mapping from path segments to proper tag names
TAG_MAPPING = {
    'auth': 'Authentication',
    'token': 'Authentication',
    'google': 'Authentication',
    'users': 'Users',
    'user': 'Users',
    'settings': 'Settings',
    'api-keys': 'Settings',
    'rag': 'Settings',
    'accounting': 'Accounting',
    'invoices': 'Invoices',
    'payments': 'Payments',
    'expenses': 'Expenses',
    'journals': 'Journals',
    'contacts': 'Contacts',
    'receipts': 'Receipts',
    'financial-reports': 'Reports',
    'reports': 'Reports',
    'projects': 'Projects',
    'project-documents': 'Projects',
    'ai': 'AI Assistants',
    'assistants': 'AI Assistants',
    'ai-assistants': 'AI Assistants',
    'tasks': 'AI Tasks',
    'ai-tasks': 'AI Tasks',
    'sessions': 'AI Assistants',
    'messages': 'AI Assistants',
    'feedback': 'AI Assistants',
    'documents': 'Documents',
    'folders': 'Documents',
    'hrms': 'HRMS',
    'employees': 'HRMS',
    'departments': 'HRMS',
    'designations': 'HRMS',
    'analytics': 'Analytics',
    'dashboards': 'Analytics',
    'charts': 'Analytics',
    'business': 'Business',
    'clients': 'Business',
    'partners': 'Business',
    'tenants': 'Tenants',
    'health': 'Health',
    'coredata': 'Core Data',
    'subscriptions': 'Subscriptions',
    'fiscal-years': 'Accounting',
    'accounting-periods': 'Accounting',
    'currencies': 'Accounting',
    'tax-rates': 'Accounting',
    'accounts': 'Accounting',
    'accounting-assistant': 'Receipts',
}


class CustomAutoSchema(AutoSchema):
    """
    Custom schema generator that ensures all endpoints have proper tags
    自定義 schema 生成器，確保所有端點都有正確的標籤
    """
    
    def get_tags(self):
        """Override to ensure no 'api' tags are generated"""
        tags = super().get_tags()
        
        # If the tag is 'api', try to infer a better tag from the path
        if tags and 'api' in tags:
            tags = [tag for tag in tags if tag != 'api']
            
        # If no tags left, infer from path
        if not tags:
            tags = self._infer_tags_from_path()
            
        return tags or ['Core']
    
    def _infer_tags_from_path(self):
        """Infer tags from the URL path"""
        path_parts = self.path.strip('/').split('/')
        
        # Skip 'api' and 'v1' prefixes
        relevant_parts = []
        skip_next = False
        for i, part in enumerate(path_parts):
            if skip_next:
                skip_next = False
                continue
            if part in ('api', 'v1'):
                continue
            # Skip parameter placeholders like {id}
            if part.startswith('{') and part.endswith('}'):
                continue
            relevant_parts.append(part.lower())
        
        # Try to find a matching tag from the path parts
        for part in relevant_parts:
            if part in TAG_MAPPING:
                return [TAG_MAPPING[part]]
        
        # If still no match, use the first relevant part
        if relevant_parts:
            return [relevant_parts[0].replace('-', ' ').title()]
        
        return ['Core']


def postprocess_schema_remove_api_tag(result, generator, request, public):
    """
    Postprocessing hook to remove 'api' tags and replace with proper category
    """
    paths = result.get('paths', {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            tags = details.get('tags', [])
            if 'api' in tags:
                # Remove 'api' and infer proper tag
                new_tags = [t for t in tags if t != 'api']
                
                if not new_tags:
                    # Infer from path
                    path_parts = path.strip('/').split('/')
                    for part in path_parts:
                        part_lower = part.lower()
                        if part_lower in TAG_MAPPING:
                            new_tags = [TAG_MAPPING[part_lower]]
                            break
                    
                    if not new_tags:
                        # Find first meaningful part
                        for part in path_parts:
                            if part not in ('api', 'v1', '') and not (part.startswith('{') and part.endswith('}')):
                                new_tags = [part.replace('-', ' ').title()]
                                break
                
                details['tags'] = new_tags if new_tags else ['Core']
    
    return result