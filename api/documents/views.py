from django.shortcuts import render

# Import views from the views directory
from documents.views.document_viewset import DocumentViewSet

# Make views available at the module level
__all__ = ['DocumentViewSet']
