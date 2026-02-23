# Wisematic ERP Core

**企業資源規劃系統核心服務 - 基於 Django 的 RESTful API 後端服務**
*Enterprise Resource Planning Core Service - Django-based RESTful API Backend*

---

## 專案概述 / Project Overview

Wisematic ERP Core 是一個全功能的企業資源規劃系統，提供以下核心模組：
*Wisematic ERP Core is a full-featured Enterprise Resource Planning system with the following core modules:*

| 模組 Module | 說明 Description |
|---|---|
| 👥 使用者管理 | User Management |
| 🏢 人力資源管理系統 | Human Resource Management System (HRMS) |
| 📊 專案管理 | Project Management |
| 📄 文件管理 | Document Management |
| 📈 數據分析 | Analytics |
| 🤖 AI 助理 | AI Assistants |
| 💾 核心資料管理 | Core Data Management |

---

## 技術棧 / Tech Stack

| 項目 | 說明 |
|---|---|
| 後端框架 Backend Framework | Django + Django REST Framework |
| 程式語言 Language | Python 3.10+ |
| 容器化 Containerization | Docker |
| 編排工具 Orchestration | Kubernetes (K8s) |
| 部署工具 Deployment | Skaffold |
| 雲端服務 Cloud | AWS (ECR, ALB, ACM) |
| 資料庫 Database | PostgreSQL / MySQL |

---

## 系統需求 / System Requirements

- Python 3.10 或以上 / Python 3.10 or above
- Conda 或 virtualenv / Conda or virtualenv
- Docker（用於容器化部署 / for containerized deployment）
- Kubernetes（用於生產部署 / for production deployment）
- AWS CLI（用於雲端部署 / for cloud deployment）

---

## 本機開發環境設定 / Local Development Setup

### 1. 建立虛擬環境 / Create Virtual Environment

```bash
# 建立新環境 / Create new environment
conda create -n wisematic-erp python=3.10 -y

# 啟動環境 / Activate environment
conda activate wisematic-erp
```

### 2. 安裝依賴套件 / Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. 環境變數設定 / Environment Variables

```bash
# 複製範例檔案 / Copy example file
copy .env.example .env
```

需要設定的環境變數 / Required environment variables:

| 變數 Variable | 說明 Description |
|---|---|
| `DATABASE_URL` | 資料庫連線字串 / Database connection string |
| `SECRET_KEY` | Django 密鑰 / Django secret key |
| `DEBUG` | 開發模式開關 / Debug mode toggle |
| `ALLOWED_HOSTS` | 允許的主機名稱 / Allowed hostnames |
| `AWS_ACCESS_KEY_ID` | AWS 存取金鑰 / AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS 秘密金鑰 / AWS secret key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud 憑證路徑 / GCP credentials path |

### 4. 資料庫設定與遷移 / Database Setup & Migration

```bash
# 進入 api 目錄 / Enter api directory
cd api

# 建立資料庫遷移檔 / Create migration files
python manage.py makemigrations

# 執行資料庫遷移 / Run migrations
python manage.py migrate

# 建立超級使用者 / Create superuser
python manage.py createsuperuser
```

### 5. 啟動開發伺服器 / Start Development Server

```bash
# 啟動 Django 開發伺服器 / Start Django development server
python manage.py runserver

# 或指定 IP 和 Port / Or specify IP and port
python manage.py runserver 0.0.0.0:8000
```

伺服器啟動後，訪問 / After starting, visit:

| 端點 Endpoint | URL |
|---|---|
| API 根路徑 / API Root | http://localhost:8000/api/v1/ |
| 健康檢查 / Health Check | http://localhost:8000/api/v1/health/ |
| Django Admin | http://localhost:8000/admin/ |

---

## Docker 容器化部署 / Docker Deployment

### 建置與執行 / Build & Run

```bash
# 建置映像 / Build image
docker build -t wisematic-erp-core .

# 執行容器 / Run container
docker run -p 8000:8000 wisematic-erp-core
```

### Docker Compose

```bash
docker-compose up -d
```

---

## Kubernetes 部署 / Kubernetes Deployment

### 使用 Skaffold / Using Skaffold

```bash
# 開發模式（自動重新載入）/ Development mode (auto-reload)
skaffold dev

# 部署到 Kubernetes / Deploy to Kubernetes
skaffold run

# 刪除部署 / Remove deployment
skaffold delete
```

### 手動部署 / Manual kubectl Deployment

```bash
# 建立 namespace / Create namespace
kubectl create namespace wisematic

# 部署應用 / Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 查看部署狀態 / Check deployment status
kubectl get pods -n wisematic
kubectl get svc -n wisematic
kubectl get ingress -n wisematic
```

---

## 專案結構 / Project Structure

```
wisematic-erp-core/
├── api/                          # Django 應用程式碼 / Django application code
│   ├── core/                     # 核心設定 / Core settings
│   ├── users/                    # 使用者管理 / User management
│   ├── hrms/                     # 人力資源管理 / HRMS
│   ├── projects/                 # 專案管理 / Project management
│   ├── documents/                # 文件管理 / Document management
│   ├── analytics/                # 數據分析 / Analytics
│   ├── ai_assistants/            # AI 助理 / AI Assistants
│   ├── coredata/                 # 核心資料 / Core data
│   ├── health/                   # 健康檢查 / Health check
│   └── manage.py                 # Django 管理指令 / Django management
├── k8s/                          # Kubernetes 配置 / Kubernetes configs
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── Dockerfile
├── requirements.txt
├── skaffold.yaml
├── makefile
└── .gitignore
```

---

## 常用指令 / Common Commands

### Django 管理指令 / Django Management Commands

```bash
# 建立新應用 / Create new app
python manage.py startapp <app_name>

# 收集靜態檔案 / Collect static files
python manage.py collectstatic

# 備份資料庫 / Backup database
python manage.py dumpdata > backup.json

# 載入資料 / Load data
python manage.py loaddata backup.json

# 執行測試 / Run tests
python manage.py test

# 開啟 Django Shell / Open Django shell
python manage.py shell
```

### Make 指令 / Make Commands

```bash
make help    # 查看可用指令 / Show available commands
make build   # 執行建置 / Run build
make test    # 執行測試 / Run tests
```

---

## API 文件 / API Documentation

### 健康檢查 / Health Check

```
GET /api/v1/health/
```

### 主要端點 / Main Endpoints

| 端點 Endpoint | 說明 Description |
|---|---|
| `/api/v1/users/` | 使用者管理 / User management |
| `/api/v1/hrms/` | 人力資源管理 / HRMS |
| `/api/v1/projects/` | 專案管理 / Project management |
| `/api/v1/documents/` | 文件管理 / Document management |
| `/api/v1/analytics/` | 數據分析 / Analytics |
| `/api/v1/ai-assistants/` | AI 助理 / AI Assistants |

---

## 生產環境部署 / Production Deployment

### AWS ECR 推送映像 / Push Image to AWS ECR

```bash
# 登入 AWS ECR / Login to AWS ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 935364008466.dkr.ecr.us-east-2.amazonaws.com

# 標記映像 / Tag image
docker tag wisematic-erp-core:latest 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core:latest

# 推送映像 / Push image
docker push 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core:latest
```

### 生產環境 URL / Production URLs

| 說明 Description | URL |
|---|---|
| 主域名 / Main Domain | https://erp-core.wisematic.click |
| 健康檢查 / Health Check | https://erp-core.wisematic.click/api/v1/health/ |

---

## 疑難排解 / Troubleshooting

### 常見問題 / Common Issues

**1. 資料庫連線失敗 / Database Connection Failed**
- 確認資料庫是否正在運行 / Check if database is running
- 確認環境變數中的資料庫連線字串正確 / Verify `DATABASE_URL` is correct
- 查看 `api/core/settings.py` 中的 `DATABASES` 設定 / Review `DATABASES` in settings

**2. 缺少環境變數 / Missing Environment Variables**
- 確保 `.env` 檔案存在且配置正確 / Ensure `.env` file exists and is configured
- 檢查所有必要的環境變數是否已設定 / Check all required variables are set

**3. 依賴套件安裝失敗 / Dependency Installation Failed**
- 更新 pip: `pip install --upgrade pip`
- 使用 conda 安裝: `conda install <package_name>`

**4. Google Cloud 憑證錯誤 / Google Cloud Credentials Error**
- 確保 `.json` 憑證檔案路徑正確 / Ensure credentials JSON path is correct
- 設定環境變數: `GOOGLE_APPLICATION_CREDENTIALS`

### 查看日誌 / View Logs

```bash
# Django 開發伺服器日誌 / Django development server logs
python manage.py runserver --verbosity 2

# Kubernetes Pod 日誌 / Kubernetes Pod logs
kubectl logs -f <pod-name> -n wisematic

# Docker 容器日誌 / Docker container logs
docker logs -f <container-id>
```

---

## 開發指南 / Development Guide

### 程式碼風格 / Code Style

- 遵循 PEP 8 規範 / Follow PEP 8 guidelines
- 使用有意義的變數和函數命名 / Use meaningful variable and function names
- 編寫文件字串和註解 / Write docstrings and comments

### Git 工作流程 / Git Workflow

```bash
# 建立新分支 / Create new branch
git checkout -b feature/new-feature

# 提交變更 / Commit changes
git add .
git commit -m "feat: describe your change"

# 推送到遠端 / Push to remote
git push origin feature/new-feature
```

### 測試 / Testing

```bash
# 執行所有測試 / Run all tests
python manage.py test

# 執行特定應用測試 / Run specific app tests
python manage.py test users

# 生成覆蓋率報告 / Generate coverage report
coverage run --source='.' manage.py test
coverage report
```

---

## 安全注意事項 / Security Notes

> ⚠️ 不要將 `.env` 檔案提交到版本控制 / Never commit `.env` to version control
>
> ⚠️ 不要在程式碼中硬編碼密鑰和憑證 / Never hardcode secrets or credentials in code
>
> ⚠️ 定期更新依賴套件以修補安全漏洞 / Regularly update dependencies to patch vulnerabilities
>
> ⚠️ 生產環境必須關閉 DEBUG 模式 / Always disable DEBUG mode in production
>
> ⚠️ 使用強密碼和金鑰 / Use strong passwords and keys

---

## 貢獻指南 / Contributing

1. Fork 此專案 / Fork this repository
2. 建立功能分支 / Create your feature branch: `git checkout -b feature/AmazingFeature`
3. 提交變更 / Commit your changes: `git commit -m 'feat: add some AmazingFeature'`
4. 推送到分支 / Push to the branch: `git push origin feature/AmazingFeature`
5. 開啟 Pull Request / Open a Pull Request

---

## 授權 / License

*請根據實際情況填寫授權資訊 / Please fill in the license information accordingly*

---

## 聯絡方式 / Contact

| | |
|---|---|
| 專案維護者 Project Maintainer | *填寫聯絡資訊 / Fill in contact info* |
| 問題回報 Issue Tracker | *填寫 Issue tracker 連結 / Fill in issue tracker link* |
| 電子郵件 Email | *填寫電子郵件 / Fill in email* |

---

## 更新日誌 / Changelog

```
[版本號 Version] - YYYY-MM-DD
- 新增功能 Added
- 修復 Bug Fixed
- 改進項目 Improved
```
