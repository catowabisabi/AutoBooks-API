"""
API Schema Extensions
統一定義所有視圖的 API 文檔標籤和說明
Centralized API documentation tags and descriptions for all views
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


# ============================================================
# Accounting ViewSets Schema Extensions
# 會計模組視圖的 Schema 擴展
# ============================================================

FiscalYearViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Accounting'],
        summary='列出財政年度 / List fiscal years',
        description='獲取所有財政年度列表。\n\nGet all fiscal years list.'
    ),
    create=extend_schema(
        tags=['Accounting'],
        summary='創建財政年度 / Create fiscal year',
        description='創建新的財政年度。\n\nCreate a new fiscal year.'
    ),
    retrieve=extend_schema(
        tags=['Accounting'],
        summary='獲取財政年度 / Get fiscal year',
        description='根據 ID 獲取財政年度詳情。\n\nGet fiscal year details by ID.'
    ),
    update=extend_schema(
        tags=['Accounting'],
        summary='更新財政年度 / Update fiscal year',
        description='更新財政年度資訊。\n\nUpdate fiscal year information.'
    ),
    partial_update=extend_schema(
        tags=['Accounting'],
        summary='部分更新財政年度 / Partial update fiscal year',
        description='部分更新財政年度資訊。\n\nPartially update fiscal year information.'
    ),
    destroy=extend_schema(
        tags=['Accounting'],
        summary='刪除財政年度 / Delete fiscal year',
        description='刪除財政年度。\n\nDelete fiscal year.'
    ),
)

AccountingPeriodViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Accounting'],
        summary='列出會計期間 / List accounting periods',
        description='獲取所有會計期間列表。\n\nGet all accounting periods list.'
    ),
    create=extend_schema(
        tags=['Accounting'],
        summary='創建會計期間 / Create accounting period',
        description='創建新的會計期間。\n\nCreate a new accounting period.'
    ),
    retrieve=extend_schema(
        tags=['Accounting'],
        summary='獲取會計期間 / Get accounting period',
        description='根據 ID 獲取會計期間詳情。\n\nGet accounting period details by ID.'
    ),
    update=extend_schema(
        tags=['Accounting'],
        summary='更新會計期間 / Update accounting period',
        description='更新會計期間資訊。\n\nUpdate accounting period information.'
    ),
    partial_update=extend_schema(
        tags=['Accounting'],
        summary='部分更新會計期間 / Partial update accounting period',
        description='部分更新會計期間資訊。\n\nPartially update accounting period information.'
    ),
    destroy=extend_schema(
        tags=['Accounting'],
        summary='刪除會計期間 / Delete accounting period',
        description='刪除會計期間。\n\nDelete accounting period.'
    ),
)

CurrencyViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Accounting'],
        summary='列出貨幣 / List currencies',
        description='獲取所有貨幣列表。\n\nGet all currencies list.'
    ),
    create=extend_schema(
        tags=['Accounting'],
        summary='創建貨幣 / Create currency',
        description='創建新的貨幣。\n\nCreate a new currency.'
    ),
    retrieve=extend_schema(
        tags=['Accounting'],
        summary='獲取貨幣 / Get currency',
        description='根據 ID 獲取貨幣詳情。\n\nGet currency details by ID.'
    ),
    update=extend_schema(
        tags=['Accounting'],
        summary='更新貨幣 / Update currency',
        description='更新貨幣資訊。\n\nUpdate currency information.'
    ),
    partial_update=extend_schema(
        tags=['Accounting'],
        summary='部分更新貨幣 / Partial update currency',
        description='部分更新貨幣資訊。\n\nPartially update currency information.'
    ),
    destroy=extend_schema(
        tags=['Accounting'],
        summary='刪除貨幣 / Delete currency',
        description='刪除貨幣。\n\nDelete currency.'
    ),
)

TaxRateViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Accounting'],
        summary='列出稅率 / List tax rates',
        description='獲取所有稅率列表。\n\nGet all tax rates list.'
    ),
    create=extend_schema(
        tags=['Accounting'],
        summary='創建稅率 / Create tax rate',
        description='創建新的稅率。\n\nCreate a new tax rate.'
    ),
    retrieve=extend_schema(
        tags=['Accounting'],
        summary='獲取稅率 / Get tax rate',
        description='根據 ID 獲取稅率詳情。\n\nGet tax rate details by ID.'
    ),
    update=extend_schema(
        tags=['Accounting'],
        summary='更新稅率 / Update tax rate',
        description='更新稅率資訊。\n\nUpdate tax rate information.'
    ),
    partial_update=extend_schema(
        tags=['Accounting'],
        summary='部分更新稅率 / Partial update tax rate',
        description='部分更新稅率資訊。\n\nPartially update tax rate information.'
    ),
    destroy=extend_schema(
        tags=['Accounting'],
        summary='刪除稅率 / Delete tax rate',
        description='刪除稅率。\n\nDelete tax rate.'
    ),
)

AccountViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Accounting'],
        summary='列出會計科目 / List accounts',
        description='獲取所有會計科目列表，支援篩選。\n\nGet all accounts list with filtering support.'
    ),
    create=extend_schema(
        tags=['Accounting'],
        summary='創建會計科目 / Create account',
        description='創建新的會計科目。\n\nCreate a new account.'
    ),
    retrieve=extend_schema(
        tags=['Accounting'],
        summary='獲取會計科目 / Get account',
        description='根據 ID 獲取會計科目詳情。\n\nGet account details by ID.'
    ),
    update=extend_schema(
        tags=['Accounting'],
        summary='更新會計科目 / Update account',
        description='更新會計科目資訊。\n\nUpdate account information.'
    ),
    partial_update=extend_schema(
        tags=['Accounting'],
        summary='部分更新會計科目 / Partial update account',
        description='部分更新會計科目資訊。\n\nPartially update account information.'
    ),
    destroy=extend_schema(
        tags=['Accounting'],
        summary='刪除會計科目 / Delete account',
        description='刪除會計科目。\n\nDelete account.'
    ),
)

# ============================================================
# Journal Entry Schema Extensions
# 日記帳模組
# ============================================================

JournalEntryViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Journals'],
        summary='列出日記帳分錄 / List journal entries',
        description='獲取所有日記帳分錄列表。\n\nGet all journal entries list.'
    ),
    create=extend_schema(
        tags=['Journals'],
        summary='創建日記帳分錄 / Create journal entry',
        description='創建新的日記帳分錄。\n\nCreate a new journal entry.'
    ),
    retrieve=extend_schema(
        tags=['Journals'],
        summary='獲取日記帳分錄 / Get journal entry',
        description='根據 ID 獲取日記帳分錄詳情。\n\nGet journal entry details by ID.'
    ),
    update=extend_schema(
        tags=['Journals'],
        summary='更新日記帳分錄 / Update journal entry',
        description='更新日記帳分錄資訊。\n\nUpdate journal entry information.'
    ),
    partial_update=extend_schema(
        tags=['Journals'],
        summary='部分更新日記帳分錄 / Partial update journal entry',
        description='部分更新日記帳分錄資訊。\n\nPartially update journal entry information.'
    ),
    destroy=extend_schema(
        tags=['Journals'],
        summary='刪除日記帳分錄 / Delete journal entry',
        description='刪除日記帳分錄。\n\nDelete journal entry.'
    ),
)

# ============================================================
# Contact Schema Extensions
# 聯絡人模組
# ============================================================

ContactViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Contacts'],
        summary='列出聯絡人 / List contacts',
        description='獲取所有客戶和供應商聯絡人列表。\n\nGet all customer and supplier contacts list.'
    ),
    create=extend_schema(
        tags=['Contacts'],
        summary='創建聯絡人 / Create contact',
        description='創建新的聯絡人（客戶或供應商）。\n\nCreate a new contact (customer or supplier).'
    ),
    retrieve=extend_schema(
        tags=['Contacts'],
        summary='獲取聯絡人 / Get contact',
        description='根據 ID 獲取聯絡人詳情。\n\nGet contact details by ID.'
    ),
    update=extend_schema(
        tags=['Contacts'],
        summary='更新聯絡人 / Update contact',
        description='更新聯絡人資訊。\n\nUpdate contact information.'
    ),
    partial_update=extend_schema(
        tags=['Contacts'],
        summary='部分更新聯絡人 / Partial update contact',
        description='部分更新聯絡人資訊。\n\nPartially update contact information.'
    ),
    destroy=extend_schema(
        tags=['Contacts'],
        summary='刪除聯絡人 / Delete contact',
        description='刪除聯絡人。\n\nDelete contact.'
    ),
)

# ============================================================
# Invoice Schema Extensions
# 發票模組
# ============================================================

InvoiceViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Invoices'],
        summary='列出發票 / List invoices',
        description='獲取所有發票列表，支援篩選和分頁。\n\nGet all invoices list with filtering and pagination.'
    ),
    create=extend_schema(
        tags=['Invoices'],
        summary='創建發票 / Create invoice',
        description='創建新的銷售或採購發票。\n\nCreate a new sales or purchase invoice.'
    ),
    retrieve=extend_schema(
        tags=['Invoices'],
        summary='獲取發票 / Get invoice',
        description='根據 ID 獲取發票詳情，包含行項目。\n\nGet invoice details by ID, including line items.'
    ),
    update=extend_schema(
        tags=['Invoices'],
        summary='更新發票 / Update invoice',
        description='更新發票資訊。\n\nUpdate invoice information.'
    ),
    partial_update=extend_schema(
        tags=['Invoices'],
        summary='部分更新發票 / Partial update invoice',
        description='部分更新發票資訊。\n\nPartially update invoice information.'
    ),
    destroy=extend_schema(
        tags=['Invoices'],
        summary='刪除發票 / Delete invoice',
        description='刪除發票。\n\nDelete invoice.'
    ),
)

# ============================================================
# Payment Schema Extensions
# 付款模組
# ============================================================

PaymentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Payments'],
        summary='列出付款 / List payments',
        description='獲取所有付款記錄列表。\n\nGet all payment records list.'
    ),
    create=extend_schema(
        tags=['Payments'],
        summary='創建付款 / Create payment',
        description='創建新的付款記錄。\n\nCreate a new payment record.'
    ),
    retrieve=extend_schema(
        tags=['Payments'],
        summary='獲取付款 / Get payment',
        description='根據 ID 獲取付款詳情。\n\nGet payment details by ID.'
    ),
    update=extend_schema(
        tags=['Payments'],
        summary='更新付款 / Update payment',
        description='更新付款資訊。\n\nUpdate payment information.'
    ),
    partial_update=extend_schema(
        tags=['Payments'],
        summary='部分更新付款 / Partial update payment',
        description='部分更新付款資訊。\n\nPartially update payment information.'
    ),
    destroy=extend_schema(
        tags=['Payments'],
        summary='刪除付款 / Delete payment',
        description='刪除付款記錄。\n\nDelete payment record.'
    ),
)

# ============================================================
# Expense Schema Extensions
# 支出模組
# ============================================================

ExpenseViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Expenses'],
        summary='列出支出 / List expenses',
        description='獲取所有支出記錄列表。\n\nGet all expense records list.'
    ),
    create=extend_schema(
        tags=['Expenses'],
        summary='創建支出 / Create expense',
        description='創建新的支出記錄。\n\nCreate a new expense record.'
    ),
    retrieve=extend_schema(
        tags=['Expenses'],
        summary='獲取支出 / Get expense',
        description='根據 ID 獲取支出詳情。\n\nGet expense details by ID.'
    ),
    update=extend_schema(
        tags=['Expenses'],
        summary='更新支出 / Update expense',
        description='更新支出資訊。\n\nUpdate expense information.'
    ),
    partial_update=extend_schema(
        tags=['Expenses'],
        summary='部分更新支出 / Partial update expense',
        description='部分更新支出資訊。\n\nPartially update expense information.'
    ),
    destroy=extend_schema(
        tags=['Expenses'],
        summary='刪除支出 / Delete expense',
        description='刪除支出記錄。\n\nDelete expense record.'
    ),
)

# ============================================================
# Project Schema Extensions
# 專案模組
# ============================================================

ProjectViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出專案 / List projects',
        description='獲取所有專案列表，支援篩選。\n\nGet all projects list with filtering support.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='創建專案 / Create project',
        description='創建新的專案。\n\nCreate a new project.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取專案 / Get project',
        description='根據 ID 獲取專案詳情。\n\nGet project details by ID.'
    ),
    update=extend_schema(
        tags=['Projects'],
        summary='更新專案 / Update project',
        description='更新專案資訊。\n\nUpdate project information.'
    ),
    partial_update=extend_schema(
        tags=['Projects'],
        summary='部分更新專案 / Partial update project',
        description='部分更新專案資訊。\n\nPartially update project information.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='刪除專案 / Delete project',
        description='刪除專案。\n\nDelete project.'
    ),
)

ProjectDocumentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Projects'],
        summary='列出專案文件 / List project documents',
        description='獲取專案關聯的所有文件。\n\nGet all documents linked to project.'
    ),
    create=extend_schema(
        tags=['Projects'],
        summary='關聯專案文件 / Link project document',
        description='將文件關聯到專案。\n\nLink document to project.'
    ),
    retrieve=extend_schema(
        tags=['Projects'],
        summary='獲取專案文件 / Get project document',
        description='獲取專案文件詳情。\n\nGet project document details.'
    ),
    destroy=extend_schema(
        tags=['Projects'],
        summary='移除專案文件關聯 / Unlink project document',
        description='移除專案與文件的關聯。\n\nRemove document link from project.'
    ),
)

# ============================================================
# Receipt Schema Extensions
# 收據模組
# ============================================================

ReceiptViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Receipts'],
        summary='列出收據 / List receipts',
        description='獲取所有收據列表，支援多種篩選條件。\n\nGet all receipts list with multiple filtering options.'
    ),
    create=extend_schema(
        tags=['Receipts'],
        summary='上傳收據 / Upload receipt',
        description='上傳新的收據圖片或文件。\n\nUpload a new receipt image or document.'
    ),
    retrieve=extend_schema(
        tags=['Receipts'],
        summary='獲取收據 / Get receipt',
        description='根據 ID 獲取收據詳情，包含提取的欄位。\n\nGet receipt details by ID, including extracted fields.'
    ),
    update=extend_schema(
        tags=['Receipts'],
        summary='更新收據 / Update receipt',
        description='更新收據資訊。\n\nUpdate receipt information.'
    ),
    partial_update=extend_schema(
        tags=['Receipts'],
        summary='部分更新收據 / Partial update receipt',
        description='部分更新收據資訊。\n\nPartially update receipt information.'
    ),
    destroy=extend_schema(
        tags=['Receipts'],
        summary='刪除收據 / Delete receipt',
        description='刪除收據。\n\nDelete receipt.'
    ),
)

# ============================================================
# Financial Report Schema Extensions
# 財務報表模組
# ============================================================

ReportViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Reports'],
        summary='列出報表 / List reports',
        description='獲取所有財務報表列表。\n\nGet all financial reports list.'
    ),
    create=extend_schema(
        tags=['Reports'],
        summary='生成報表 / Generate report',
        description='生成新的財務報表。\n\nGenerate a new financial report.'
    ),
    retrieve=extend_schema(
        tags=['Reports'],
        summary='獲取報表 / Get report',
        description='根據 ID 獲取報表詳情和數據。\n\nGet report details and data by ID.'
    ),
    destroy=extend_schema(
        tags=['Reports'],
        summary='刪除報表 / Delete report',
        description='刪除財務報表。\n\nDelete financial report.'
    ),
)

FinancialReportViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Reports'],
        summary='列出財務報表 / List financial reports',
        description='獲取所有已生成的財務報表。\n\nGet all generated financial reports.'
    ),
    create=extend_schema(
        tags=['Reports'],
        summary='創建財務報表 / Create financial report',
        description='創建新的財務報表。\n\nCreate a new financial report.'
    ),
    retrieve=extend_schema(
        tags=['Reports'],
        summary='獲取財務報表 / Get financial report',
        description='獲取財務報表詳細數據。\n\nGet financial report detailed data.'
    ),
    update=extend_schema(
        tags=['Reports'],
        summary='更新財務報表 / Update financial report',
        description='更新財務報表。\n\nUpdate financial report.'
    ),
    partial_update=extend_schema(
        tags=['Reports'],
        summary='部分更新財務報表 / Partial update financial report',
        description='部分更新財務報表。\n\nPartially update financial report.'
    ),
    destroy=extend_schema(
        tags=['Reports'],
        summary='刪除財務報表 / Delete financial report',
        description='刪除財務報表。\n\nDelete financial report.'
    ),
)
