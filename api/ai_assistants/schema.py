"""
AI Assistants Schema Extensions
AI 助理模組 API 文檔標籤和說明
"""
from drf_spectacular.utils import extend_schema, extend_schema_view


AIAgentViewSetSchema = extend_schema_view(
    chat=extend_schema(
        tags=['AI Assistants'],
        summary='AI 對話 / AI Chat',
        description='與 AI 代理進行對話並執行操作。\n\nChat with AI agent and execute actions.'
    ),
    list=extend_schema(
        tags=['AI Assistants'],
        summary='列出 AI 代理 / List AI agents',
        description='獲取可用的 AI 代理列表。\n\nGet available AI agents list.'
    ),
    actions=extend_schema(
        tags=['AI Assistants'],
        summary='操作歷史 / Action history',
        description='獲取 AI 操作歷史記錄。\n\nGet AI action history records.'
    ),
    rollback=extend_schema(
        tags=['AI Assistants'],
        summary='回滾操作 / Rollback action',
        description='回滾指定的 AI 操作。\n\nRollback specified AI action.'
    ),
    sessions=extend_schema(
        tags=['AI Assistants'],
        summary='對話會話 / Conversation sessions',
        description='獲取對話會話列表。\n\nGet conversation sessions list.'
    ),
    tools=extend_schema(
        tags=['AI Assistants'],
        summary='可用工具 / Available tools',
        description='獲取 AI 可用的工具列表。\n\nGet AI available tools list.'
    ),
)

BrainstormViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['AI Assistants'],
        summary='列出腦力激盪會議 / List brainstorm sessions',
        description='獲取所有腦力激盪會議列表。\n\nGet all brainstorm sessions list.'
    ),
    create=extend_schema(
        tags=['AI Assistants'],
        summary='創建腦力激盪會議 / Create brainstorm session',
        description='創建新的腦力激盪會議。\n\nCreate a new brainstorm session.'
    ),
    retrieve=extend_schema(
        tags=['AI Assistants'],
        summary='獲取腦力激盪會議 / Get brainstorm session',
        description='根據 ID 獲取腦力激盪會議詳情。\n\nGet brainstorm session details by ID.'
    ),
    update=extend_schema(
        tags=['AI Assistants'],
        summary='更新腦力激盪會議 / Update brainstorm session',
        description='更新腦力激盪會議資訊。\n\nUpdate brainstorm session information.'
    ),
    partial_update=extend_schema(
        tags=['AI Assistants'],
        summary='部分更新腦力激盪會議 / Partial update brainstorm session',
        description='部分更新腦力激盪會議資訊。\n\nPartially update brainstorm session information.'
    ),
    destroy=extend_schema(
        tags=['AI Assistants'],
        summary='刪除腦力激盪會議 / Delete brainstorm session',
        description='刪除腦力激盪會議。\n\nDelete brainstorm session.'
    ),
)

AIDocumentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['AI Assistants'],
        summary='列出 AI 文件 / List AI documents',
        description='獲取 AI 處理的文件列表。\n\nGet AI processed documents list.'
    ),
    create=extend_schema(
        tags=['AI Assistants'],
        summary='上傳 AI 文件 / Upload AI document',
        description='上傳文件供 AI 分析。\n\nUpload document for AI analysis.'
    ),
    retrieve=extend_schema(
        tags=['AI Assistants'],
        summary='獲取 AI 文件 / Get AI document',
        description='獲取 AI 文件詳情和分析結果。\n\nGet AI document details and analysis results.'
    ),
    destroy=extend_schema(
        tags=['AI Assistants'],
        summary='刪除 AI 文件 / Delete AI document',
        description='刪除 AI 文件。\n\nDelete AI document.'
    ),
    analyze=extend_schema(
        tags=['AI Assistants'],
        summary='AI 分析文件 / AI analyze document',
        description='使用 AI 分析文件內容。\n\nAnalyze document content using AI.'
    ),
)

AsyncTaskViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['AI Tasks'],
        summary='列出非同步任務 / List async tasks',
        description='獲取所有非同步任務列表。\n\nGet all async tasks list.'
    ),
    retrieve=extend_schema(
        tags=['AI Tasks'],
        summary='獲取任務狀態 / Get task status',
        description='根據 ID 獲取任務狀態和結果。\n\nGet task status and result by ID.'
    ),
    cancel=extend_schema(
        tags=['AI Tasks'],
        summary='取消任務 / Cancel task',
        description='取消正在執行的任務。\n\nCancel running task.'
    ),
    retry=extend_schema(
        tags=['AI Tasks'],
        summary='重試任務 / Retry task',
        description='重試失敗的任務。\n\nRetry failed task.'
    ),
)

FeedbackViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['AI Assistants'],
        summary='列出反饋 / List feedback',
        description='獲取所有 AI 反饋記錄。\n\nGet all AI feedback records.'
    ),
    create=extend_schema(
        tags=['AI Assistants'],
        summary='提交反饋 / Submit feedback',
        description='提交 AI 回應的反饋。\n\nSubmit feedback for AI response.'
    ),
    retrieve=extend_schema(
        tags=['AI Assistants'],
        summary='獲取反饋 / Get feedback',
        description='根據 ID 獲取反饋詳情。\n\nGet feedback details by ID.'
    ),
)
