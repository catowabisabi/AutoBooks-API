"""
File Upload Validation Module
檔案上傳驗證模組

Provides comprehensive validation for uploaded files including:
- File size limits
- MIME type validation
- File extension validation
- Basic content inspection
"""

import os
import sys

# python-magic has Windows compatibility issues, use fallback
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    magic = None  # type: ignore
    HAS_MAGIC = False
    
from typing import List, Optional, Tuple
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
import logging

logger = logging.getLogger('file_upload')


# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB default
MAX_CSV_SIZE = 50 * 1024 * 1024   # 50MB for CSV files
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB for images

# Allowed MIME types by category
ALLOWED_MIME_TYPES = {
    'documents': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
    ],
    'spreadsheets': [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ],
    'images': [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ],
    'data': [
        'application/json',
        'text/xml',
        'application/xml',
    ]
}

# Flatten for easy lookup
ALL_ALLOWED_MIMES = set()
for mimes in ALLOWED_MIME_TYPES.values():
    ALL_ALLOWED_MIMES.update(mimes)

# Extension to MIME mapping
EXTENSION_MIME_MAP = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.csv': 'text/csv',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.json': 'application/json',
    '.xml': 'application/xml',
}

# Dangerous file signatures (magic bytes)
DANGEROUS_SIGNATURES = [
    b'MZ',           # Windows executable
    b'\x7fELF',      # Linux executable
    b'#!/',          # Shell script
    b'<?php',        # PHP script
    b'<script',      # JavaScript in HTML
]


class FileValidationError(ValidationError):
    """Custom exception for file validation errors"""
    pass


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension"""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def get_mime_type(file: UploadedFile) -> str:
    """
    Detect MIME type using python-magic.
    Falls back to content_type if magic is not available.
    """
    # If magic is not available (e.g., on Windows), use content_type
    if not HAS_MAGIC:
        logger.debug("python-magic not available, using content_type")
        return file.content_type
        
    try:
        # Read first 2048 bytes for detection
        file.seek(0)
        header = file.read(2048)
        file.seek(0)
        
        mime = magic.from_buffer(header, mime=True)
        return mime
    except Exception as e:
        logger.warning(f"Magic detection failed: {e}, using content_type")
        return file.content_type


def validate_file_size(file: UploadedFile, max_size: Optional[int] = None) -> None:
    """
    Validate file size.
    
    Args:
        file: The uploaded file
        max_size: Maximum allowed size in bytes (optional)
    
    Raises:
        FileValidationError: If file is too large
    """
    if max_size is None:
        ext = get_file_extension(file.name)
        if ext == '.csv':
            max_size = MAX_CSV_SIZE
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            max_size = MAX_IMAGE_SIZE
        else:
            max_size = MAX_FILE_SIZE
    
    if file.size > max_size:
        max_mb = max_size / 1024 / 1024
        file_mb = file.size / 1024 / 1024
        raise FileValidationError(
            f"File too large: {file_mb:.1f}MB. Maximum allowed: {max_mb:.1f}MB"
        )


def validate_mime_type(
    file: UploadedFile, 
    allowed_types: Optional[List[str]] = None
) -> str:
    """
    Validate file MIME type.
    
    Args:
        file: The uploaded file
        allowed_types: List of allowed MIME types (optional)
    
    Returns:
        Detected MIME type
    
    Raises:
        FileValidationError: If MIME type is not allowed
    """
    if allowed_types is None:
        allowed_types = list(ALL_ALLOWED_MIMES)
    
    detected_mime = get_mime_type(file)
    
    # Also check declared content_type
    declared_mime = file.content_type
    
    # Verify detected MIME is allowed
    if detected_mime not in allowed_types:
        raise FileValidationError(
            f"File type not allowed: {detected_mime}. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
    
    # Warn if declared and detected don't match (could be spoofing)
    if declared_mime != detected_mime:
        logger.warning(
            f"MIME type mismatch: declared={declared_mime}, detected={detected_mime}"
        )
    
    return detected_mime


def validate_extension(file: UploadedFile, allowed_extensions: Optional[List[str]] = None) -> str:
    """
    Validate file extension.
    
    Args:
        file: The uploaded file
        allowed_extensions: List of allowed extensions (optional)
    
    Returns:
        File extension
    
    Raises:
        FileValidationError: If extension is not allowed
    """
    if allowed_extensions is None:
        allowed_extensions = list(EXTENSION_MIME_MAP.keys())
    
    ext = get_file_extension(file.name)
    
    if ext not in allowed_extensions:
        raise FileValidationError(
            f"File extension not allowed: {ext}. "
            f"Allowed extensions: {', '.join(allowed_extensions)}"
        )
    
    return ext


def validate_extension_mime_match(file: UploadedFile) -> None:
    """
    Verify that file extension matches detected MIME type.
    
    Raises:
        FileValidationError: If there's a mismatch
    """
    ext = get_file_extension(file.name)
    detected_mime = get_mime_type(file)
    
    expected_mime = EXTENSION_MIME_MAP.get(ext)
    
    if expected_mime and expected_mime != detected_mime:
        # Some flexibility for similar types
        similar_types = {
            ('text/plain', 'text/csv'),
            ('text/plain', 'text/markdown'),
            ('application/xml', 'text/xml'),
        }
        
        if (detected_mime, expected_mime) not in similar_types and \
           (expected_mime, detected_mime) not in similar_types:
            raise FileValidationError(
                f"Extension/content mismatch: extension is {ext} "
                f"but content is {detected_mime}"
            )


def validate_no_dangerous_content(file: UploadedFile) -> None:
    """
    Check for dangerous file signatures.
    
    Raises:
        FileValidationError: If dangerous content is detected
    """
    file.seek(0)
    header = file.read(256)
    file.seek(0)
    
    for sig in DANGEROUS_SIGNATURES:
        if header.startswith(sig) or sig in header:
            raise FileValidationError(
                "File contains potentially dangerous content"
            )


def validate_upload(
    file: UploadedFile,
    max_size: Optional[int] = None,
    allowed_types: Optional[List[str]] = None,
    allowed_extensions: Optional[List[str]] = None,
    check_content: bool = True
) -> Tuple[str, str]:
    """
    Comprehensive file validation.
    
    Args:
        file: The uploaded file
        max_size: Maximum file size in bytes
        allowed_types: Allowed MIME types
        allowed_extensions: Allowed file extensions
        check_content: Whether to check for dangerous content
    
    Returns:
        Tuple of (extension, mime_type)
    
    Raises:
        FileValidationError: If validation fails
    """
    # Log the upload attempt
    logger.info(f"Validating upload: {file.name} ({file.size} bytes)")
    
    try:
        # 1. Validate size
        validate_file_size(file, max_size)
        
        # 2. Validate extension
        ext = validate_extension(file, allowed_extensions)
        
        # 3. Validate MIME type
        mime_type = validate_mime_type(file, allowed_types)
        
        # 4. Verify extension/MIME match
        validate_extension_mime_match(file)
        
        # 5. Check for dangerous content
        if check_content:
            validate_no_dangerous_content(file)
        
        logger.info(f"Upload validated: {file.name} ({ext}, {mime_type})")
        return ext, mime_type
        
    except FileValidationError:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise FileValidationError(f"File validation failed: {e}")


# Django validator for use in models/serializers
def django_file_validator(file: UploadedFile) -> None:
    """Django-compatible validator"""
    validate_upload(file)


# Category-specific validators
def validate_document(file: UploadedFile) -> Tuple[str, str]:
    """Validate document upload"""
    return validate_upload(
        file,
        allowed_types=ALLOWED_MIME_TYPES['documents']
    )


def validate_spreadsheet(file: UploadedFile) -> Tuple[str, str]:
    """Validate spreadsheet upload"""
    return validate_upload(
        file,
        max_size=MAX_CSV_SIZE,
        allowed_types=ALLOWED_MIME_TYPES['spreadsheets']
    )


def validate_image(file: UploadedFile) -> Tuple[str, str]:
    """Validate image upload"""
    return validate_upload(
        file,
        max_size=MAX_IMAGE_SIZE,
        allowed_types=ALLOWED_MIME_TYPES['images']
    )


def validate_data_file(file: UploadedFile) -> Tuple[str, str]:
    """Validate data file upload (CSV, JSON, XML)"""
    return validate_upload(
        file,
        max_size=MAX_CSV_SIZE,
        allowed_types=ALLOWED_MIME_TYPES['spreadsheets'] + ALLOWED_MIME_TYPES['data']
    )
