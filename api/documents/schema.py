"""
Documents Schema Extensions
文件管理模組 API 文檔標籤和說明
"""
from drf_spectacular.utils import extend_schema, extend_schema_view


DocumentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Documents'],
        summary='列出文件 / List documents',
        description='獲取所有文件列表，按上傳時間排序。\n\nGet all documents list, sorted by upload time.'
    ),
    create=extend_schema(
        tags=['Documents'],
        summary='上傳文件 / Upload document',
        description='上傳新的文件。\n\nUpload a new document.'
    ),
    retrieve=extend_schema(
        tags=['Documents'],
        summary='獲取文件 / Get document',
        description='根據 ID 獲取文件詳情。\n\nGet document details by ID.'
    ),
    update=extend_schema(
        tags=['Documents'],
        summary='更新文件 / Update document',
        description='更新文件資訊。\n\nUpdate document information.'
    ),
    partial_update=extend_schema(
        tags=['Documents'],
        summary='部分更新文件 / Partial update document',
        description='部分更新文件資訊。\n\nPartially update document information.'
    ),
    destroy=extend_schema(
        tags=['Documents'],
        summary='刪除文件 / Delete document',
        description='刪除文件。\n\nDelete document.'
    ),
    extract_text=extend_schema(
        tags=['Documents'],
        summary='提取文字 / Extract text',
        description='使用 OCR 從文件中提取文字。\n\nExtract text from document using OCR.'
    ),
    extract_data=extend_schema(
        tags=['Documents'],
        summary='提取數據 / Extract data',
        description='從 OCR 文字中提取結構化數據。\n\nExtract structured data from OCR text.'
    ),
    translate=extend_schema(
        tags=['Documents'],
        summary='翻譯文件 / Translate document',
        description='將文件內容翻譯成指定語言。\n\nTranslate document content to specified language.'
    ),
)
