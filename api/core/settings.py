import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =================================================================
# Security Settings
# =================================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
DJANGO_ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(',') if h.strip()]
AUTH_USER_MODEL = 'users.User'

# =================================================================
# Application Definition
# =================================================================
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',

    # Local apps (feature-based)
    'core.apps.CoreConfig',
    'users',
    'hrms',
    'documents',
    'analytics',
    'ai_assistants',
    'coredata',
    'health',
    'accounting',  # Accounting module
    'business',    # Business operations - Audits, Tax Returns, Revenue, BMI
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.tenants.middleware.TenantMiddleware',  # Multi-tenant context
    'core.subscription_middleware.SubscriptionMiddleware',  # Subscription feature restrictions
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# =================================================================
# Database Configuration
# =================================================================
DATABASE_ENGINE = os.getenv('DATABASE_ENGINE', 'sqlite')

if DATABASE_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'wisematic_erp'),
            'USER': os.getenv('DATABASE_USER', 'postgres'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', ''),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
        }
    }
else:
    # Default to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =================================================================
# Authentication & JWT
# =================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =================================================================
# API Documentation (drf-spectacular)
# =================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'AutoBooks API',
    'DESCRIPTION': '''
# AutoBooks API 文件 / AutoBooks API Documentation

## 簡介 / Introduction

AutoBooks 是一個全功能的企業資源規劃系統（ERP），提供完整的後端 API 服務。

AutoBooks is a full-featured Enterprise Resource Planning (ERP) system providing comprehensive backend API services.

## 功能模組 / Feature Modules

| 模組 Module | 說明 Description |
|-------------|------------------|
| 🔐 認證 Authentication | 用戶登入、JWT Token 管理 / User login, JWT Token management |
| 👥 用戶管理 Users | 用戶帳號、設定、訂閱管理 / User accounts, settings, subscription management |
| 💰 會計 Accounting | 會計科目、日記帳、發票、支出 / Chart of accounts, journals, invoices, expenses |
| 🧾 收據 Receipts | 收據上傳、OCR 識別、欄位提取 / Receipt upload, OCR recognition, field extraction |
| 📊 報表 Reports | 財務報表生成與匯出 / Financial report generation and export |
| 📁 專案 Projects | 專案管理、文件關聯 / Project management, document linking |
| 🤖 AI 助理 AI Assistants | AI 對話、文件分析、腦力激盪 / AI chat, document analysis, brainstorming |
| 📄 文件管理 Documents | 文件上傳、儲存、管理 / Document upload, storage, management |
| 👔 人力資源 HRMS | 員工、部門、職位管理 / Employee, department, designation management |
| 📈 數據分析 Analytics | 儀表板、圖表、KPI 指標 / Dashboards, charts, KPI metrics |
| 🏢 業務營運 Business | 客戶、合作夥伴、營收追蹤 / Clients, partners, revenue tracking |
| 🏠 租戶管理 Tenants | 多租戶系統管理 / Multi-tenant system management |

## 認證方式 / Authentication

所有 API（除健康檢查外）都需要 JWT Bearer Token 認證。

All APIs (except health check) require JWT Bearer Token authentication.

```
Authorization: Bearer <your_jwt_token>
```

## 聯繫方式 / Contact

如有問題，請聯繫系統管理員。

For any issues, please contact the system administrator.
''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'docExpansion': 'list',
        'filter': True,
        'tagsSorter': 'alpha',
        'operationsSorter': 'alpha',
    },
    'SECURITY': [{'Bearer': []}],
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    # API 標籤分類和說明
    'TAGS': [
        {
            'name': 'Health',
            'description': '🏥 **健康檢查 / Health Check**\n\n系統健康狀態檢查端點，無需認證。\n\nSystem health status check endpoint, no authentication required.'
        },
        {
            'name': 'Authentication',
            'description': '🔐 **認證 / Authentication**\n\nJWT Token 認證相關端點，包含登入、Token 刷新、Google OAuth。\n\nJWT Token authentication endpoints, including login, token refresh, Google OAuth.'
        },
        {
            'name': 'Users',
            'description': '👥 **用戶管理 / User Management**\n\n用戶帳號的 CRUD 操作、個人資料管理、用戶設定。\n\nUser account CRUD operations, profile management, user settings.'
        },
        {
            'name': 'Subscriptions',
            'description': '💳 **訂閱管理 / Subscription Management**\n\n訂閱計劃和用戶訂閱管理。\n\nSubscription plans and user subscription management.'
        },
        {
            'name': 'Accounting',
            'description': '💰 **會計管理 / Accounting Management**\n\n會計科目、會計期間、財政年度、貨幣、稅率管理。\n\nChart of accounts, accounting periods, fiscal years, currencies, tax rates management.'
        },
        {
            'name': 'Journals',
            'description': '📒 **日記帳 / Journal Entries**\n\n會計分錄的建立、查詢、過帳操作。\n\nJournal entry creation, query, and posting operations.'
        },
        {
            'name': 'Invoices',
            'description': '🧾 **發票管理 / Invoice Management**\n\n銷售發票和採購發票的建立與管理。\n\nSales and purchase invoice creation and management.'
        },
        {
            'name': 'Payments',
            'description': '💵 **付款管理 / Payment Management**\n\n收款、付款記錄和發票沖銷。\n\nPayment receipts, payment records, and invoice allocation.'
        },
        {
            'name': 'Expenses',
            'description': '💸 **支出管理 / Expense Management**\n\n公司支出的記錄與分類管理。\n\nCompany expense recording and categorization.'
        },
        {
            'name': 'Contacts',
            'description': '📇 **聯絡人 / Contacts**\n\n客戶和供應商聯絡資訊管理。\n\nCustomer and supplier contact information management.'
        },
        {
            'name': 'Receipts',
            'description': '🧾 **收據處理 / Receipt Processing**\n\n收據上傳、OCR 自動識別、欄位提取與校正。\n\nReceipt upload, OCR auto-recognition, field extraction and correction.'
        },
        {
            'name': 'Reports',
            'description': '📊 **財務報表 / Financial Reports**\n\n資產負債表、損益表、現金流量表等財務報表生成與匯出。\n\nBalance sheet, income statement, cash flow statement generation and export.'
        },
        {
            'name': 'Projects',
            'description': '📁 **專案管理 / Project Management**\n\n專案的建立、追蹤、文件關聯管理。\n\nProject creation, tracking, and document linking.'
        },
        {
            'name': 'AI Assistants',
            'description': '🤖 **AI 助理 / AI Assistants**\n\n智能對話、文件分析、腦力激盪會議等 AI 功能。\n\nIntelligent chat, document analysis, brainstorming sessions and other AI features.'
        },
        {
            'name': 'AI Tasks',
            'description': '⚙️ **AI 任務 / AI Tasks**\n\n非同步 AI 任務的管理與狀態追蹤。\n\nAsynchronous AI task management and status tracking.'
        },
        {
            'name': 'Documents',
            'description': '📄 **文件管理 / Document Management**\n\n文件的上傳、下載、分類與權限管理。\n\nDocument upload, download, categorization, and permission management.'
        },
        {
            'name': 'HRMS',
            'description': '👔 **人力資源 / Human Resources**\n\n員工資料、部門結構、職位管理。\n\nEmployee data, department structure, designation management.'
        },
        {
            'name': 'Analytics',
            'description': '📈 **數據分析 / Analytics**\n\n儀表板、圖表、KPI 指標與報表排程。\n\nDashboards, charts, KPI metrics, and report scheduling.'
        },
        {
            'name': 'Business',
            'description': '🏢 **業務營運 / Business Operations**\n\n客戶管理、合作夥伴、營收追蹤、市場分析。\n\nClient management, partners, revenue tracking, market analysis.'
        },
        {
            'name': 'Tenants',
            'description': '🏠 **租戶管理 / Tenant Management**\n\n多租戶系統的租戶建立與管理。\n\nMulti-tenant system tenant creation and management.'
        },
        {
            'name': 'Core Data',
            'description': '💾 **核心資料 / Core Data**\n\n系統基礎資料，如行業分類、地區代碼等。\n\nSystem base data such as industry classifications, region codes, etc.'
        },
        {
            'name': 'Settings',
            'description': '⚙️ **系統設定 / System Settings**\n\nAPI 金鑰、RAG 知識庫等系統配置。\n\nAPI keys, RAG knowledge base, and other system configurations.'
        },
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60'))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# =================================================================
# CORS Settings
# =================================================================
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS', 
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins (Required for Django 4.x+)
# This is CRITICAL for VPS deployment - must include your domain
CSRF_TRUSTED_ORIGINS_ENV = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if CSRF_TRUSTED_ORIGINS_ENV:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_ENV.split(',') if origin.strip()]
else:
    # Default for development
    CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:8000', 'http://127.0.0.1:8000']

# For development only - remove in production
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

# =================================================================
# Static Files
# =================================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =================================================================
# AI API Keys (from environment)
# =================================================================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Google Application Credentials
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# =================================================================
# Google OAuth 2.0
# =================================================================
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:8000/api/v1/auth/google/callback/')

# =================================================================
# AWS Configuration
# =================================================================
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME', '')

# =================================================================
# Supabase Configuration
# =================================================================
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

# =================================================================
# Email Configuration
# =================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# =================================================================
# Redis Configuration (for caching)
# =================================================================
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Optional: Configure cache with Redis
if REDIS_URL and not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }

# =================================================================
# Sentry Error Tracking
# =================================================================
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
        environment=os.getenv('APP_ENV', 'development'),
    )

# =================================================================
# Logging Configuration
# =================================================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

# =================================================================
# Password Validation
# =================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =================================================================
# Internationalization
# =================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =================================================================
# Default Primary Key Field Type
# =================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
