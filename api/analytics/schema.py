"""
Analytics Schema Extensions
數據分析模組 API 文檔標籤和說明
"""
from drf_spectacular.utils import extend_schema, extend_schema_view


DashboardViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Analytics'],
        summary='列出儀表板 / List dashboards',
        description='獲取所有儀表板列表。\n\nGet all dashboards list.'
    ),
    create=extend_schema(
        tags=['Analytics'],
        summary='創建儀表板 / Create dashboard',
        description='創建新的儀表板。\n\nCreate a new dashboard.'
    ),
    retrieve=extend_schema(
        tags=['Analytics'],
        summary='獲取儀表板 / Get dashboard',
        description='根據 ID 獲取儀表板詳情。\n\nGet dashboard details by ID.'
    ),
    update=extend_schema(
        tags=['Analytics'],
        summary='更新儀表板 / Update dashboard',
        description='更新儀表板資訊。\n\nUpdate dashboard information.'
    ),
    partial_update=extend_schema(
        tags=['Analytics'],
        summary='部分更新儀表板 / Partial update dashboard',
        description='部分更新儀表板資訊。\n\nPartially update dashboard information.'
    ),
    destroy=extend_schema(
        tags=['Analytics'],
        summary='刪除儀表板 / Delete dashboard',
        description='刪除儀表板。\n\nDelete dashboard.'
    ),
    default=extend_schema(
        tags=['Analytics'],
        summary='獲取預設儀表板 / Get default dashboard',
        description='獲取預設儀表板。\n\nGet default dashboard.'
    ),
)

ChartViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Analytics'],
        summary='列出圖表 / List charts',
        description='獲取所有圖表列表。\n\nGet all charts list.'
    ),
    create=extend_schema(
        tags=['Analytics'],
        summary='創建圖表 / Create chart',
        description='創建新的圖表。\n\nCreate a new chart.'
    ),
    retrieve=extend_schema(
        tags=['Analytics'],
        summary='獲取圖表 / Get chart',
        description='根據 ID 獲取圖表詳情。\n\nGet chart details by ID.'
    ),
    update=extend_schema(
        tags=['Analytics'],
        summary='更新圖表 / Update chart',
        description='更新圖表資訊。\n\nUpdate chart information.'
    ),
    partial_update=extend_schema(
        tags=['Analytics'],
        summary='部分更新圖表 / Partial update chart',
        description='部分更新圖表資訊。\n\nPartially update chart information.'
    ),
    destroy=extend_schema(
        tags=['Analytics'],
        summary='刪除圖表 / Delete chart',
        description='刪除圖表。\n\nDelete chart.'
    ),
)

AnalyticsSalesViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Analytics'],
        summary='列出銷售分析 / List sales analytics',
        description='獲取所有銷售分析資料。\n\nGet all sales analytics data.'
    ),
    create=extend_schema(
        tags=['Analytics'],
        summary='創建銷售分析 / Create sales analytics',
        description='創建新的銷售分析記錄。\n\nCreate a new sales analytics record.'
    ),
    retrieve=extend_schema(
        tags=['Analytics'],
        summary='獲取銷售分析 / Get sales analytics',
        description='根據 ID 獲取銷售分析詳情。\n\nGet sales analytics details by ID.'
    ),
    update=extend_schema(
        tags=['Analytics'],
        summary='更新銷售分析 / Update sales analytics',
        description='更新銷售分析資訊。\n\nUpdate sales analytics information.'
    ),
    partial_update=extend_schema(
        tags=['Analytics'],
        summary='部分更新銷售分析 / Partial update sales analytics',
        description='部分更新銷售分析資訊。\n\nPartially update sales analytics information.'
    ),
    destroy=extend_schema(
        tags=['Analytics'],
        summary='刪除銷售分析 / Delete sales analytics',
        description='刪除銷售分析記錄。\n\nDelete sales analytics record.'
    ),
    yearly_summary=extend_schema(
        tags=['Analytics'],
        summary='年度銷售摘要 / Yearly sales summary',
        description='獲取年度銷售摘要資料。\n\nGet yearly sales summary data.'
    ),
    trends=extend_schema(
        tags=['Analytics'],
        summary='銷售趨勢 / Sales trends',
        description='獲取銷售趨勢圖表資料。\n\nGet sales trends chart data.'
    ),
)

KPIMetricViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Analytics'],
        summary='列出 KPI 指標 / List KPI metrics',
        description='獲取所有 KPI 指標列表。\n\nGet all KPI metrics list.'
    ),
    create=extend_schema(
        tags=['Analytics'],
        summary='創建 KPI 指標 / Create KPI metric',
        description='創建新的 KPI 指標。\n\nCreate a new KPI metric.'
    ),
    retrieve=extend_schema(
        tags=['Analytics'],
        summary='獲取 KPI 指標 / Get KPI metric',
        description='根據 ID 獲取 KPI 指標詳情。\n\nGet KPI metric details by ID.'
    ),
    update=extend_schema(
        tags=['Analytics'],
        summary='更新 KPI 指標 / Update KPI metric',
        description='更新 KPI 指標資訊。\n\nUpdate KPI metric information.'
    ),
    partial_update=extend_schema(
        tags=['Analytics'],
        summary='部分更新 KPI 指標 / Partial update KPI metric',
        description='部分更新 KPI 指標資訊。\n\nPartially update KPI metric information.'
    ),
    destroy=extend_schema(
        tags=['Analytics'],
        summary='刪除 KPI 指標 / Delete KPI metric',
        description='刪除 KPI 指標。\n\nDelete KPI metric.'
    ),
    by_category=extend_schema(
        tags=['Analytics'],
        summary='按類別分組 KPI / KPIs by category',
        description='獲取按類別分組的 KPI 指標。\n\nGet KPI metrics grouped by category.'
    ),
    update_value=extend_schema(
        tags=['Analytics'],
        summary='更新 KPI 值 / Update KPI value',
        description='更新 KPI 當前值。\n\nUpdate KPI current value.'
    ),
)

ReportScheduleViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Analytics'],
        summary='列出報表排程 / List report schedules',
        description='獲取所有報表排程列表。\n\nGet all report schedules list.'
    ),
    create=extend_schema(
        tags=['Analytics'],
        summary='創建報表排程 / Create report schedule',
        description='創建新的報表排程。\n\nCreate a new report schedule.'
    ),
    retrieve=extend_schema(
        tags=['Analytics'],
        summary='獲取報表排程 / Get report schedule',
        description='根據 ID 獲取報表排程詳情。\n\nGet report schedule details by ID.'
    ),
    update=extend_schema(
        tags=['Analytics'],
        summary='更新報表排程 / Update report schedule',
        description='更新報表排程資訊。\n\nUpdate report schedule information.'
    ),
    partial_update=extend_schema(
        tags=['Analytics'],
        summary='部分更新報表排程 / Partial update report schedule',
        description='部分更新報表排程資訊。\n\nPartially update report schedule information.'
    ),
    destroy=extend_schema(
        tags=['Analytics'],
        summary='刪除報表排程 / Delete report schedule',
        description='刪除報表排程。\n\nDelete report schedule.'
    ),
)

AnalyticsDashboardViewSchema = extend_schema(
    tags=['Analytics'],
    summary='分析儀表板總覽 / Analytics dashboard overview',
    description='獲取分析儀表板總覽資料，包含當月銷售、YTD 統計、KPI 指標等。\n\nGet analytics dashboard overview data including current month sales, YTD stats, KPI metrics.'
)
