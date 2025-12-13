"""
Custom Schema Generator for API Documentation
"""
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView


class CustomAutoSchema(AutoSchema):
    """
    Custom schema generator that ensures all endpoints have proper tags
    """
    
    def get_tags(self):
        """Override to ensure no 'api' tags are generated"""
        tags = super().get_tags()
        
        # If the tag is 'api', try to infer a better tag from the path or class
        if 'api' in tags:
            tags = [tag for tag in tags if tag != 'api']
            
            # If no tags left, try to infer from path or class name
            if not tags:
                # Try to get tag from path
                path_parts = self.path.strip('/').split('/')
                if len(path_parts) >= 2 and path_parts[0] == 'api' and path_parts[1] == 'v1':
                    if len(path_parts) >= 3:
                        # Use the third part as tag (e.g., /api/v1/users/ -> Users)
                        tag = path_parts[2].replace('-', ' ').title()
                        # Handle specific mappings
                        tag_mapping = {
                            'Auth': 'Authentication',
                            'Docs': 'Health',  # swagger docs
                            'Schema': 'Health',  # schema endpoint
                        }
                        tags = [tag_mapping.get(tag, tag)]
                    else:
                        tags = ['Core']
                else:
                    tags = ['Core']
        
        return tags or ['Core']