# 📋 Wisematic ERP Backend - TODO List

## 🎯 項目概覽
後端 Django API 開發任務清單

---

## 🔐 Phase 1: 安全性與環境配置

### 環境設置
- [ ] 建立 `.env` 檔案，移除 `settings.py` 中的硬編碼敏感資訊
- [ ] 建立 `.env.example` 作為範例
- [ ] 更新 `.gitignore` 確保不會提交敏感資訊
- [ ] 設置 Supabase/PostgreSQL 連接配置
- [ ] 設置 AWS 相關配置

### API Keys 管理
- [ ] 建立 `APIKeyStore` 模型，將 API keys 存入資料庫
- [ ] 實現 API key 加密存儲
- [ ] 建立 API key 管理端點

### 認證系統
- [ ] 整合 Google OAuth 2.0 登入
- [ ] 實現 JWT refresh token rotation
- [ ] 添加 rate limiting
- [ ] 實現 session 管理

---

## 🤖 Phase 2: AI Assistants API 端點

### Gemini API 整合
- [ ] 建立 Gemini 服務類
- [ ] 文件分析端點 (`/api/v1/ai/gemini/analyze/`)
- [ ] 文字生成端點 (`/api/v1/ai/gemini/generate/`)
- [ ] Vision 分析端點 (`/api/v1/ai/gemini/vision/`)

### ChatGPT (OpenAI) API 整合
- [ ] 建立 OpenAI 服務類
- [ ] 聊天完成端點 (`/api/v1/ai/openai/chat/`)
- [ ] 文字分析端點 (`/api/v1/ai/openai/analyze/`)
- [ ] 代碼生成端點 (`/api/v1/ai/openai/code/`)

### DeepSeek API 整合
- [ ] 建立 DeepSeek 服務類
- [ ] 聊天端點 (`/api/v1/ai/deepseek/chat/`)
- [ ] 代碼分析端點 (`/api/v1/ai/deepseek/code/`)

### AI 路由器
- [ ] 建立統一 AI 請求路由器
- [ ] 實現 fallback 機制（一個 API 失敗時切換到另一個）
- [ ] 實現 API 使用量追蹤

---

## 💰 Phase 3: 會計系統 (Accounting Module)

### 資料庫模型
- [ ] `Account` - 會計科目表 (Chart of Accounts)
- [ ] `JournalEntry` - 日記帳分錄
- [ ] `JournalEntryLine` - 日記帳分錄明細
- [ ] `Invoice` - 發票
- [ ] `InvoiceLine` - 發票明細
- [ ] `Payment` - 付款記錄
- [ ] `Expense` - 費用記錄
- [ ] `Receipt` - 收據
- [ ] `TaxRate` - 稅率
- [ ] `FiscalYear` - 會計年度
- [ ] `AccountingPeriod` - 會計期間

### API 端點
- [ ] CRUD `/api/v1/accounting/accounts/`
- [ ] CRUD `/api/v1/accounting/journal-entries/`
- [ ] CRUD `/api/v1/accounting/invoices/`
- [ ] CRUD `/api/v1/accounting/payments/`
- [ ] CRUD `/api/v1/accounting/expenses/`
- [ ] CRUD `/api/v1/accounting/receipts/`

### 報表生成
- [ ] 資產負債表 (Balance Sheet) PDF/Excel
- [ ] 損益表 (Income Statement) PDF/Excel
- [ ] 現金流量表 (Cash Flow Statement) PDF/Excel
- [ ] 試算表 (Trial Balance) PDF/Excel
- [ ] 應收帳款報表
- [ ] 應付帳款報表
- [ ] 自訂報表生成器

### AI 會計助理
- [ ] 收據/發票自動識別 OCR
- [ ] 自動分類交易
- [ ] 異常交易檢測
- [ ] 財務分析建議

---

## 👥 Phase 4: 完善現有模組

### Users 模組
- [ ] 完善 `/api/v1/users/` CRUD
- [ ] 用戶角色權限管理
- [ ] 用戶偏好設置

### HRMS 模組
- [ ] 完善 `/api/v1/departments/` CRUD
- [ ] 完善 `/api/v1/designations/` CRUD
- [ ] 完善 `/api/v1/projects/` CRUD
- [ ] 完善 `/api/v1/tasks/` CRUD
- [ ] 完善 `/api/v1/leave_applications/` CRUD
- [ ] 新增 `/api/v1/attendance/` 出勤管理
- [ ] 新增 `/api/v1/payroll/` 薪資管理

### Documents 模組
- [ ] 完善 `/api/v1/documents/` CRUD
- [ ] 文件版本控制
- [ ] 文件分享權限

### Analytics 模組
- [ ] 完善 `/api/v1/dashboards/` CRUD
- [ ] 完善 `/api/v1/charts/` CRUD
- [ ] 數據匯出功能

---

## 🗄️ Phase 5: 資料庫與部署

### 資料庫配置
- [ ] SQLite (開發環境)
- [ ] PostgreSQL/Supabase (生產環境)
- [ ] 資料庫遷移腳本
- [ ] 種子資料 (Seed Data)

### Coredata 端點
- [ ] `/api/v1/currency-list/` - 貨幣列表
- [ ] `/api/v1/country-list/` - 國家列表
- [ ] `/api/v1/timezone-list/` - 時區列表

### 部署準備
- [ ] Docker 配置優化
- [ ] Kubernetes 配置
- [ ] CI/CD Pipeline
- [ ] 環境變數文檔

---

## 📊 Phase 6: 測試與文檔

### 測試
- [ ] 單元測試
- [ ] API 整合測試
- [ ] 性能測試

### 文檔
- [ ] API 文檔 (Swagger/OpenAPI)
- [ ] 開發者指南
- [ ] 部署指南

---

## 🚀 優先順序

1. **最高** - 環境配置與安全性 (Phase 1)
2. **高** - 會計系統基礎 (Phase 3)
3. **中** - AI 整合 (Phase 2)
4. **中** - 完善現有模組 (Phase 4)
5. **低** - 測試與文檔 (Phase 6)

---

## 📝 備註

- 開發環境使用 SQLite
- 生產環境使用 Supabase PostgreSQL
- 所有 API keys 應存入資料庫並加密
- Google OAuth 將在後端實現以確保安全性
