from django.db import models

# Import models from the models directory
from documents.models.document import Document

# Make models available at the module level
__all__ = ['Document']
