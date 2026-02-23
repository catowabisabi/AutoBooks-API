# Wisematic ERP Core

企業資源規劃系統核心服務 - 基於 Django 的 RESTful API 後端服務

## 專案概述

Wisematic ERP Core 是一個全功能的企業資源規劃系統，提供以下核心模組：

- 👥 **使用者管理** (Users)
- 🏢 **人力資源管理系統** (HRMS)
- 📊 **專案管理** (Projects)
- 📄 **文件管理** (Documents)
- 📈 **數據分析** (Analytics)
- 🤖 **AI 助理** (AI Assistants)
- 💾 **核心資料管理** (Core Data)

## 技術棧

- **後端框架**: Django + Django REST Framework
- **程式語言**: Python 3.10+
- **容器化**: Docker
- **編排工具**: Kubernetes (K8s)
- **部署工具**: Skaffold
- **雲端服務**: AWS (ECR, ALB, ACM)
- **資料庫**: PostgreSQL/MySQL (請查看 settings.py)

## 系統需求

- Python 3.10 或以上
- Conda 或 virtualenv
- Docker (用於容器化部署)
- Kubernetes 環境 (用於生產部署)
- AWS CLI (用於雲端部署)

## 本機開發環境設定

### 1. 使用 Conda 建立虛擬環境

```bash
# 建立新環境
conda create -n wisematic-erp python=3.10 -y

# 啟動環境
conda activate wisematic-erp
```

### 2. 安裝依賴套件

```bash
# 安裝 Python 套件
pip install -r requirements.txt
```

### 3. 環境變數設定

複製環境變數範例檔案並進行配置：

```bash
# 如果有 .env.example
copy .env.example .env
```

需要設定的環境變數（請根據實際情況調整）：
- `DATABASE_URL` - 資料庫連線字串
- `SECRET_KEY` - Django 密鑰
- `DEBUG` - 開發模式開關
- `ALLOWED_HOSTS` - 允許的主機名稱
- `AWS_ACCESS_KEY_ID` - AWS 存取金鑰
- `AWS_SECRET_ACCESS_KEY` - AWS 秘密金鑰
- Google Cloud 憑證路徑（如需要）

### 4. 資料庫設定與遷移

```bash
# 進入 api 目錄
cd api

# 建立資料庫遷移檔
python manage.py makemigrations

# 執行資料庫遷移
python manage.py migrate

# 建立超級使用者（管理員帳號）
python manage.py createsuperuser
```

### 5. 啟動開發伺服器

```bash
# 啟動 Django 開發伺服器
python manage.py runserver

# 或指定 IP 和 Port
python manage.py runserver 0.0.0.0:8000
```

伺服器啟動後，訪問：
- API 根路徑: http://localhost:8000/api/v1/
- 健康檢查: http://localhost:8000/api/v1/health/
- Django Admin: http://localhost:8000/admin/

## Docker 容器化部署

### 建置 Docker 映像

```bash
# 建置映像
docker build -t wisematic-erp-core .

# 執行容器
docker run -p 8000:8000 wisematic-erp-core
```

### 使用 Docker Compose（如適用）

```bash
docker-compose up -d
```

## Kubernetes 部署

### 使用 Skaffold 部署

```bash
# 開發模式（自動重新載入）
skaffold dev

# 部署到 Kubernetes
skaffold run

# 刪除部署
skaffold delete
```

### 手動 kubectl 部署

```bash
# 設定 namespace
kubectl create namespace wisematic

# 部署應用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 查看部署狀態
kubectl get pods -n wisematic
kubectl get svc -n wisematic
kubectl get ingress -n wisematic
```

## 專案結構

```
wisematic-erp-core/
├── api/                          # Django 應用程式碼
│   ├── core/                     # 核心設定
│   ├── users/                    # 使用者管理
│   ├── hrms/                     # 人力資源管理
│   ├── projects/                 # 專案管理
│   ├── documents/                # 文件管理
│   ├── analytics/                # 數據分析
│   ├── ai_assistants/            # AI 助理
│   ├── coredata/                 # 核心資料
│   ├── health/                   # 健康檢查
│   └── manage.py                 # Django 管理指令
├── k8s/                          # Kubernetes 配置
│   ├── deployment.yaml           # 部署配置
│   ├── service.yaml              # 服務配置
│   └── ingress.yaml              # Ingress 配置
├── Dockerfile                    # Docker 建置檔
├── requirements.txt              # Python 依賴套件
├── skaffold.yaml                 # Skaffold 配置
├── makefile                      # Make 自動化腳本
└── .gitignore                    # Git 忽略清單
```

## 常用指令

### Django 管理指令

```bash
# 建立新應用
python manage.py startapp <app_name>

# 收集靜態檔案
python manage.py collectstatic

# 建立資料庫備份
python manage.py dumpdata > backup.json

# 載入資料
python manage.py loaddata backup.json

# 執行測試
python manage.py test

# 開啟 Django Shell
python manage.py shell
```

### Make 指令（查看 makefile）

```bash
# 查看可用指令
make help

# 執行建置
make build

# 執行測試
make test
```

## API 文件

### 健康檢查端點

- `GET /api/v1/health/` - 系統健康狀態檢查

### 主要 API 端點（待確認）

- `/api/v1/users/` - 使用者管理
- `/api/v1/hrms/` - 人力資源管理
- `/api/v1/projects/` - 專案管理
- `/api/v1/documents/` - 文件管理
- `/api/v1/analytics/` - 數據分析
- `/api/v1/ai-assistants/` - AI 助理

## 生產環境部署

### AWS ECR 推送映像

```bash
# 登入 AWS ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 935364008466.dkr.ecr.us-east-2.amazonaws.com

# 標記映像
docker tag wisematic-erp-core:latest 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core:latest

# 推送映像
docker push 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core:latest
```

### 生產環境 URL

- **主域名**: https://erp-core.wisematic.click
- **健康檢查**: https://erp-core.wisematic.click/api/v1/health/

## 疑難排解

### 常見問題

**1. 資料庫連線失敗**
- 檢查資料庫是否正在運行
- 確認環境變數中的資料庫連線字串正確
- 查看 `api/core/settings.py` 中的 DATABASES 設定

**2. 缺少環境變數**
- 確保 `.env` 檔案存在且配置正確
- 檢查是否所有必要的環境變數都已設定

**3. 依賴套件安裝失敗**
- 更新 pip: `pip install --upgrade pip`
- 使用 conda 安裝特定套件: `conda install <package_name>`

**4. Google Cloud 憑證錯誤**
- 確保 `angular-pipe-470016-q2-d299a52c8630.json` 檔案路徑正確
- 設定環境變數: `GOOGLE_APPLICATION_CREDENTIALS`

### 查看日誌

```bash
# Django 開發伺服器日誌
python manage.py runserver --verbosity 2

# Kubernetes Pod 日誌
kubectl logs -f <pod-name> -n wisematic

# Docker 容器日誌
docker logs -f <container-id>
```

## 開發指南

### 程式碼風格

- 遵循 PEP 8 規範
- 使用有意義的變數和函數命名
- 編寫文件字串和註解

### Git 工作流程

```bash
# 建立新分支
git checkout -b feature/new-feature

# 提交變更
git add .
git commit -m "描述變更內容"

# 推送到遠端
git push origin feature/new-feature
```

### 測試

```bash
# 執行所有測試
python manage.py test

# 執行特定應用測試
python manage.py test users

# 執行測試並生成覆蓋率報告
coverage run --source='.' manage.py test
coverage report
```

## 安全注意事項

- ⚠️ 不要將 `.env` 檔案提交到版本控制
- ⚠️ 不要在程式碼中硬編碼密鑰和憑證
- ⚠️ 定期更新依賴套件以修補安全漏洞
- ⚠️ 生產環境必須關閉 DEBUG 模式
- ⚠️ 使用強密碼和金鑰

## 貢獻指南

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 授權

[請根據實際情況填寫授權資訊]

## 聯絡方式

- 專案維護者: [填寫聯絡資訊]
- 問題回報: [填寫 Issue tracker 連結]
- 電子郵件: [填寫電子郵件]

## 更新日誌

### [版本號] - YYYY-MM-DD
- 新增功能
- 修復 Bug
- 改進項目

---

