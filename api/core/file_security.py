"""
File Upload Security
=====================
Security utilities for file upload validation:
- MIME type detection
- File size limits
- Antivirus scanning hook
- File content validation
"""

import os
import hashlib
import logging
import tempfile
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class FileRiskLevel(Enum):
    """Risk levels for file uploads"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


@dataclass
class FileValidationResult:
    """Result of file validation"""
    is_valid: bool
    risk_level: FileRiskLevel
    detected_mime: str
    file_hash: str
    file_size: int
    errors: List[str]
    warnings: List[str]
    scan_result: Optional[Dict[str, Any]] = None


# Default allowed MIME types
DEFAULT_ALLOWED_MIME_TYPES = {
    # Images
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    'image/bmp': ['.bmp'],
    'image/tiff': ['.tiff', '.tif'],
    
    # Documents
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.ms-powerpoint': ['.ppt'],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    
    # Text
    'text/plain': ['.txt'],
    'text/csv': ['.csv'],
    'text/html': ['.html', '.htm'],
    'application/json': ['.json'],
    'application/xml': ['.xml'],
    
    # Archives (with caution)
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
    'application/x-7z-compressed': ['.7z'],
}

# Blocked extensions (high risk)
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif',
    '.js', '.vbs', '.wsf', '.wsh', '.ps1', '.psm1',
    '.jar', '.dll', '.sys', '.drv',
    '.php', '.asp', '.aspx', '.jsp', '.cgi',
    '.sh', '.bash', '.zsh', '.ksh',
}

# Default file size limits (in bytes)
DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILE_SIZE_BY_TYPE = {
    'image': 10 * 1024 * 1024,  # 10MB for images
    'document': 50 * 1024 * 1024,  # 50MB for documents
    'archive': 100 * 1024 * 1024,  # 100MB for archives
}


def detect_mime_type(file_content: bytes, filename: str = '') -> str:
    """
    Detect MIME type using file content (magic bytes).
    Falls back to extension if detection fails.
    """
    # Try python-magic if available
    try:
        import magic
        mime = magic.Magic(mime=True)
        detected = mime.from_buffer(file_content[:2048])
        return detected
    except ImportError:
        logger.warning("python-magic not installed, using fallback MIME detection")
    except Exception as e:
        logger.warning(f"Magic MIME detection failed: {e}")
    
    # Fallback: check magic bytes manually
    magic_bytes = {
        b'\xFF\xD8\xFF': 'image/jpeg',
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/zip',  # Also covers docx, xlsx, etc.
        b'\xD0\xCF\x11\xE0': 'application/msword',  # OLE compound document
        b'RIFF': 'audio/wav',
        b'\x00\x00\x00': 'video/mp4',  # Often starts with ftyp
    }
    
    for magic, mime_type in magic_bytes.items():
        if file_content.startswith(magic):
            return mime_type
    
    # Final fallback: extension-based detection
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        for mime_type, extensions in DEFAULT_ALLOWED_MIME_TYPES.items():
            if ext in extensions:
                return mime_type
    
    return 'application/octet-stream'


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


def check_extension_safety(filename: str) -> Tuple[bool, str]:
    """
    Check if file extension is safe.
    Returns (is_safe, message).
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in BLOCKED_EXTENSIONS:
        return False, f"Extension '{ext}' is blocked for security reasons"
    
    # Double extension check (e.g., .jpg.exe)
    parts = filename.lower().split('.')
    if len(parts) > 2:
        for part in parts[1:]:
            if f'.{part}' in BLOCKED_EXTENSIONS:
                return False, f"Double extension detected with blocked extension '.{part}'"
    
    return True, "Extension is allowed"


def scan_with_clamav(file_path: str) -> Dict[str, Any]:
    """
    Scan file with ClamAV antivirus.
    Requires clamav-daemon to be running.
    """
    result = {
        'scanned': False,
        'clean': None,
        'threat': None,
        'error': None,
    }
    
    try:
        # Try clamdscan (daemon mode) first - faster
        process = subprocess.run(
            ['clamdscan', '--no-summary', file_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        result['scanned'] = True
        
        if process.returncode == 0:
            result['clean'] = True
        elif process.returncode == 1:
            result['clean'] = False
            # Parse threat name from output
            for line in process.stdout.split('\n'):
                if 'FOUND' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        result['threat'] = parts[1].strip().replace(' FOUND', '')
                    break
        else:
            result['error'] = process.stderr or 'Unknown scan error'
            
    except FileNotFoundError:
        # ClamAV not installed
        result['error'] = 'ClamAV not installed'
        logger.warning("ClamAV not found - skipping antivirus scan")
    except subprocess.TimeoutExpired:
        result['error'] = 'Scan timeout'
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"ClamAV scan failed: {e}")
    
    return result


def validate_file_content(file_content: bytes, filename: str) -> List[str]:
    """
    Perform additional content validation checks.
    Returns list of warnings/errors.
    """
    warnings = []
    
    # Check for null bytes in text files
    ext = os.path.splitext(filename)[1].lower()
    text_extensions = {'.txt', '.csv', '.json', '.xml', '.html'}
    if ext in text_extensions and b'\x00' in file_content:
        warnings.append("Binary content detected in text file")
    
    # Check for embedded scripts in documents
    script_patterns = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'onload=',
        b'onerror=',
    ]
    for pattern in script_patterns:
        if pattern in file_content.lower():
            warnings.append(f"Potential embedded script detected: {pattern.decode()}")
    
    # Check for PHP/ASP tags in uploaded files
    dangerous_patterns = [
        b'<?php',
        b'<%',
        b'<asp:',
    ]
    for pattern in dangerous_patterns:
        if pattern in file_content.lower():
            warnings.append(f"Server-side code pattern detected: {pattern.decode()}")
    
    return warnings


def validate_uploaded_file(
    file: UploadedFile,
    allowed_mime_types: Optional[Dict[str, List[str]]] = None,
    max_file_size: Optional[int] = None,
    enable_antivirus: bool = True,
    strict_mode: bool = False,
) -> FileValidationResult:
    """
    Comprehensive file validation.
    
    Args:
        file: Django UploadedFile object
        allowed_mime_types: Dict of MIME types to allowed extensions
        max_file_size: Maximum file size in bytes
        enable_antivirus: Whether to scan with ClamAV
        strict_mode: If True, any warning becomes an error
    
    Returns:
        FileValidationResult with validation details
    """
    allowed_mime_types = allowed_mime_types or DEFAULT_ALLOWED_MIME_TYPES
    max_file_size = max_file_size or DEFAULT_MAX_FILE_SIZE
    
    errors = []
    warnings = []
    risk_level = FileRiskLevel.SAFE
    scan_result = None
    
    # Read file content
    file.seek(0)
    file_content = file.read()
    file.seek(0)
    
    file_size = len(file_content)
    file_hash = calculate_file_hash(file_content)
    detected_mime = detect_mime_type(file_content, file.name)
    
    # 1. Extension check
    ext_safe, ext_message = check_extension_safety(file.name)
    if not ext_safe:
        errors.append(ext_message)
        risk_level = FileRiskLevel.BLOCKED
    
    # 2. File size check
    if file_size > max_file_size:
        errors.append(f"File size ({file_size} bytes) exceeds limit ({max_file_size} bytes)")
        risk_level = max(risk_level, FileRiskLevel.HIGH, key=lambda x: list(FileRiskLevel).index(x))
    
    # 3. MIME type validation
    if detected_mime not in allowed_mime_types:
        errors.append(f"File type '{detected_mime}' is not allowed")
        risk_level = max(risk_level, FileRiskLevel.HIGH, key=lambda x: list(FileRiskLevel).index(x))
    else:
        # Check extension matches MIME type
        ext = os.path.splitext(file.name)[1].lower()
        allowed_extensions = allowed_mime_types.get(detected_mime, [])
        if ext not in allowed_extensions:
            warnings.append(
                f"Extension '{ext}' doesn't match detected type '{detected_mime}' "
                f"(expected: {', '.join(allowed_extensions)})"
            )
            risk_level = max(risk_level, FileRiskLevel.MEDIUM, key=lambda x: list(FileRiskLevel).index(x))
    
    # 4. Content validation
    content_warnings = validate_file_content(file_content, file.name)
    warnings.extend(content_warnings)
    if content_warnings:
        risk_level = max(risk_level, FileRiskLevel.MEDIUM, key=lambda x: list(FileRiskLevel).index(x))
    
    # 5. Antivirus scan
    if enable_antivirus and not errors:
        # Write to temp file for scanning
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            scan_result = scan_with_clamav(tmp_path)
            if scan_result.get('scanned') and not scan_result.get('clean'):
                threat = scan_result.get('threat', 'Unknown threat')
                errors.append(f"Antivirus detected threat: {threat}")
                risk_level = FileRiskLevel.BLOCKED
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    # 6. Strict mode: warnings become errors
    if strict_mode and warnings:
        errors.extend(warnings)
        warnings = []
    
    # Determine final validity
    is_valid = len(errors) == 0 and risk_level != FileRiskLevel.BLOCKED
    
    return FileValidationResult(
        is_valid=is_valid,
        risk_level=risk_level,
        detected_mime=detected_mime,
        file_hash=file_hash,
        file_size=file_size,
        errors=errors,
        warnings=warnings,
        scan_result=scan_result,
    )


class SecureFileValidator:
    """
    Django file validator class for use in forms/serializers.
    """
    
    def __init__(
        self,
        allowed_mime_types: Optional[Dict[str, List[str]]] = None,
        max_file_size: Optional[int] = None,
        enable_antivirus: bool = True,
    ):
        self.allowed_mime_types = allowed_mime_types or DEFAULT_ALLOWED_MIME_TYPES
        self.max_file_size = max_file_size or DEFAULT_MAX_FILE_SIZE
        self.enable_antivirus = enable_antivirus
    
    def __call__(self, file: UploadedFile) -> None:
        """Validate file and raise ValidationError if invalid"""
        result = validate_uploaded_file(
            file,
            allowed_mime_types=self.allowed_mime_types,
            max_file_size=self.max_file_size,
            enable_antivirus=self.enable_antivirus,
        )
        
        if not result.is_valid:
            raise ValidationError(result.errors)
        
        # Log warnings
        if result.warnings:
            logger.warning(f"File upload warnings for {file.name}: {result.warnings}")


def log_upload_attempt(
    user_id: int,
    filename: str,
    result: FileValidationResult,
    ip_address: str = None,
) -> None:
    """Log file upload attempt for audit trail"""
    log_data = {
        'user_id': user_id,
        'filename': filename,
        'file_size': result.file_size,
        'file_hash': result.file_hash,
        'detected_mime': result.detected_mime,
        'is_valid': result.is_valid,
        'risk_level': result.risk_level.value,
        'errors': result.errors,
        'warnings': result.warnings,
        'ip_address': ip_address,
    }
    
    if result.is_valid:
        logger.info(f"File upload accepted: {log_data}")
    else:
        logger.warning(f"File upload rejected: {log_data}")
