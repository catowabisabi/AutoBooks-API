"""
Business Schema Extensions
業務營運模組 API 文檔標籤和說明
"""
from drf_spectacular.utils import extend_schema, extend_schema_view


CompanyViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出公司 / List companies',
        description='獲取所有公司列表。\n\nGet all companies list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建公司 / Create company',
        description='創建新的公司。\n\nCreate a new company.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取公司 / Get company',
        description='根據 ID 獲取公司詳情。\n\nGet company details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新公司 / Update company',
        description='更新公司資訊。\n\nUpdate company information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新公司 / Partial update company',
        description='部分更新公司資訊。\n\nPartially update company information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除公司 / Delete company',
        description='刪除公司。\n\nDelete company.'
    ),
    stats=extend_schema(
        tags=['Business'],
        summary='公司統計 / Company statistics',
        description='獲取公司統計資料。\n\nGet company statistics.'
    ),
)

AuditProjectViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出審計專案 / List audit projects',
        description='獲取所有審計專案列表。\n\nGet all audit projects list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建審計專案 / Create audit project',
        description='創建新的審計專案。\n\nCreate a new audit project.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取審計專案 / Get audit project',
        description='根據 ID 獲取審計專案詳情。\n\nGet audit project details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新審計專案 / Update audit project',
        description='更新審計專案資訊。\n\nUpdate audit project information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新審計專案 / Partial update audit project',
        description='部分更新審計專案資訊。\n\nPartially update audit project information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除審計專案 / Delete audit project',
        description='刪除審計專案。\n\nDelete audit project.'
    ),
    dashboard=extend_schema(
        tags=['Business'],
        summary='審計儀表板 / Audit dashboard',
        description='獲取審計專案儀表板資料。\n\nGet audit project dashboard data.'
    ),
    by_status=extend_schema(
        tags=['Business'],
        summary='按狀態分組審計 / Audits by status',
        description='獲取按狀態分組的審計專案。\n\nGet audit projects grouped by status.'
    ),
)

TaxReturnCaseViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出報稅案件 / List tax return cases',
        description='獲取所有報稅案件列表。\n\nGet all tax return cases list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建報稅案件 / Create tax return case',
        description='創建新的報稅案件。\n\nCreate a new tax return case.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取報稅案件 / Get tax return case',
        description='根據 ID 獲取報稅案件詳情。\n\nGet tax return case details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新報稅案件 / Update tax return case',
        description='更新報稅案件資訊。\n\nUpdate tax return case information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新報稅案件 / Partial update tax return case',
        description='部分更新報稅案件資訊。\n\nPartially update tax return case information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除報稅案件 / Delete tax return case',
        description='刪除報稅案件。\n\nDelete tax return case.'
    ),
    dashboard=extend_schema(
        tags=['Business'],
        summary='報稅儀表板 / Tax return dashboard',
        description='獲取報稅案件儀表板資料。\n\nGet tax return case dashboard data.'
    ),
    upcoming_deadlines=extend_schema(
        tags=['Business'],
        summary='即將到期案件 / Upcoming deadlines',
        description='獲取即將到期的報稅案件。\n\nGet tax return cases with upcoming deadlines.'
    ),
)

BillableHourViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出計費時數 / List billable hours',
        description='獲取所有計費時數記錄。\n\nGet all billable hours records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建計費時數 / Create billable hour',
        description='創建新的計費時數記錄。\n\nCreate a new billable hour record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取計費時數 / Get billable hour',
        description='根據 ID 獲取計費時數詳情。\n\nGet billable hour details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新計費時數 / Update billable hour',
        description='更新計費時數資訊。\n\nUpdate billable hour information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新計費時數 / Partial update billable hour',
        description='部分更新計費時數資訊。\n\nPartially update billable hour information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除計費時數 / Delete billable hour',
        description='刪除計費時數記錄。\n\nDelete billable hour record.'
    ),
    summary=extend_schema(
        tags=['Business'],
        summary='計費時數摘要 / Billable hours summary',
        description='獲取計費時數摘要統計。\n\nGet billable hours summary statistics.'
    ),
)

RevenueViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出營收 / List revenues',
        description='獲取所有營收記錄。\n\nGet all revenue records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建營收 / Create revenue',
        description='創建新的營收記錄。\n\nCreate a new revenue record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取營收 / Get revenue',
        description='根據 ID 獲取營收詳情。\n\nGet revenue details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新營收 / Update revenue',
        description='更新營收資訊。\n\nUpdate revenue information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新營收 / Partial update revenue',
        description='部分更新營收資訊。\n\nPartially update revenue information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除營收 / Delete revenue',
        description='刪除營收記錄。\n\nDelete revenue record.'
    ),
    dashboard=extend_schema(
        tags=['Business'],
        summary='營收儀表板 / Revenue dashboard',
        description='獲取營收儀表板資料。\n\nGet revenue dashboard data.'
    ),
    by_service=extend_schema(
        tags=['Business'],
        summary='按服務類型分組營收 / Revenue by service',
        description='獲取按服務類型分組的營收。\n\nGet revenue grouped by service type.'
    ),
)

BMIIPOPRRecordViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 BMI IPO/PR 記錄 / List BMI IPO/PR records',
        description='獲取所有 BMI IPO/PR 記錄。\n\nGet all BMI IPO/PR records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建 BMI IPO/PR 記錄 / Create BMI IPO/PR record',
        description='創建新的 BMI IPO/PR 記錄。\n\nCreate a new BMI IPO/PR record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 BMI IPO/PR 記錄 / Get BMI IPO/PR record',
        description='根據 ID 獲取 BMI IPO/PR 記錄詳情。\n\nGet BMI IPO/PR record details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 BMI IPO/PR 記錄 / Update BMI IPO/PR record',
        description='更新 BMI IPO/PR 記錄資訊。\n\nUpdate BMI IPO/PR record information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 BMI IPO/PR 記錄 / Partial update BMI IPO/PR record',
        description='部分更新 BMI IPO/PR 記錄資訊。\n\nPartially update BMI IPO/PR record information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 BMI IPO/PR 記錄 / Delete BMI IPO/PR record',
        description='刪除 BMI IPO/PR 記錄。\n\nDelete BMI IPO/PR record.'
    ),
    dashboard=extend_schema(
        tags=['Business'],
        summary='BMI IPO/PR 儀表板 / BMI IPO/PR dashboard',
        description='獲取 BMI IPO/PR 儀表板資料。\n\nGet BMI IPO/PR dashboard data.'
    ),
)

BusinessPartnerViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出業務合作夥伴 / List business partners',
        description='獲取所有業務合作夥伴列表。\n\nGet all business partners list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建業務合作夥伴 / Create business partner',
        description='創建新的業務合作夥伴。\n\nCreate a new business partner.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取業務合作夥伴 / Get business partner',
        description='根據 ID 獲取業務合作夥伴詳情。\n\nGet business partner details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新業務合作夥伴 / Update business partner',
        description='更新業務合作夥伴資訊。\n\nUpdate business partner information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新業務合作夥伴 / Partial update business partner',
        description='部分更新業務合作夥伴資訊。\n\nPartially update business partner information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除業務合作夥伴 / Delete business partner',
        description='刪除業務合作夥伴。\n\nDelete business partner.'
    ),
)

IPOTimelineProgressViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 IPO 時程進度 / List IPO timeline progress',
        description='獲取所有 IPO 時程進度記錄。\n\nGet all IPO timeline progress records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建 IPO 時程進度 / Create IPO timeline progress',
        description='創建新的 IPO 時程進度記錄。\n\nCreate a new IPO timeline progress record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 IPO 時程進度 / Get IPO timeline progress',
        description='根據 ID 獲取 IPO 時程進度詳情。\n\nGet IPO timeline progress details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 IPO 時程進度 / Update IPO timeline progress',
        description='更新 IPO 時程進度資訊。\n\nUpdate IPO timeline progress information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 IPO 時程進度 / Partial update IPO timeline progress',
        description='部分更新 IPO 時程進度資訊。\n\nPartially update IPO timeline progress information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 IPO 時程進度 / Delete IPO timeline progress',
        description='刪除 IPO 時程進度記錄。\n\nDelete IPO timeline progress record.'
    ),
)

IPODealFunnelViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 IPO 交易漏斗 / List IPO deal funnel',
        description='獲取所有 IPO 交易漏斗記錄。\n\nGet all IPO deal funnel records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建 IPO 交易漏斗 / Create IPO deal funnel',
        description='創建新的 IPO 交易漏斗記錄。\n\nCreate a new IPO deal funnel record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 IPO 交易漏斗 / Get IPO deal funnel',
        description='根據 ID 獲取 IPO 交易漏斗詳情。\n\nGet IPO deal funnel details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 IPO 交易漏斗 / Update IPO deal funnel',
        description='更新 IPO 交易漏斗資訊。\n\nUpdate IPO deal funnel information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 IPO 交易漏斗 / Partial update IPO deal funnel',
        description='部分更新 IPO 交易漏斗資訊。\n\nPartially update IPO deal funnel information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 IPO 交易漏斗 / Delete IPO deal funnel',
        description='刪除 IPO 交易漏斗記錄。\n\nDelete IPO deal funnel record.'
    ),
)

IPODealSizeViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 IPO 交易規模 / List IPO deal sizes',
        description='獲取所有 IPO 交易規模記錄。\n\nGet all IPO deal size records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建 IPO 交易規模 / Create IPO deal size',
        description='創建新的 IPO 交易規模記錄。\n\nCreate a new IPO deal size record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 IPO 交易規模 / Get IPO deal size',
        description='根據 ID 獲取 IPO 交易規模詳情。\n\nGet IPO deal size details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 IPO 交易規模 / Update IPO deal size',
        description='更新 IPO 交易規模資訊。\n\nUpdate IPO deal size information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 IPO 交易規模 / Partial update IPO deal size',
        description='部分更新 IPO 交易規模資訊。\n\nPartially update IPO deal size information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 IPO 交易規模 / Delete IPO deal size',
        description='刪除 IPO 交易規模記錄。\n\nDelete IPO deal size record.'
    ),
)

OverviewDashboardViewSchema = extend_schema(
    tags=['Business'],
    summary='業務總覽儀表板 / Business overview dashboard',
    description='獲取業務總覽儀表板資料，包含各項業務統計。\n\nGet business overview dashboard data with various business statistics.'
)


# =================================================================
# Financial PR & IPO Advisory ViewSets Schema Extensions
# =================================================================

ListedClientViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出上市客戶 / List listed clients',
        description='獲取所有上市客戶列表。\n\nGet all listed clients list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建上市客戶 / Create listed client',
        description='創建新的上市客戶。\n\nCreate a new listed client.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取上市客戶 / Get listed client',
        description='根據 ID 獲取上市客戶詳情。\n\nGet listed client details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新上市客戶 / Update listed client',
        description='更新上市客戶資訊。\n\nUpdate listed client information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新上市客戶 / Partial update listed client',
        description='部分更新上市客戶資訊。\n\nPartially update listed client information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除上市客戶 / Delete listed client',
        description='刪除上市客戶。\n\nDelete listed client.'
    ),
    summary=extend_schema(
        tags=['Business'],
        summary='上市客戶摘要 / Listed clients summary',
        description='獲取上市客戶摘要統計。\n\nGet listed clients summary statistics.'
    ),
)

AnnouncementViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出公告 / List announcements',
        description='獲取所有公告列表。\n\nGet all announcements list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建公告 / Create announcement',
        description='創建新的公告。\n\nCreate a new announcement.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取公告 / Get announcement',
        description='根據 ID 獲取公告詳情。\n\nGet announcement details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新公告 / Update announcement',
        description='更新公告資訊。\n\nUpdate announcement information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新公告 / Partial update announcement',
        description='部分更新公告資訊。\n\nPartially update announcement information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除公告 / Delete announcement',
        description='刪除公告。\n\nDelete announcement.'
    ),
    this_month=extend_schema(
        tags=['Business'],
        summary='本月公告 / This month announcements',
        description='獲取本月公告列表。\n\nGet announcements for this month.'
    ),
)

MediaCoverageViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出媒體報導 / List media coverage',
        description='獲取所有媒體報導列表。\n\nGet all media coverage list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建媒體報導 / Create media coverage',
        description='創建新的媒體報導。\n\nCreate a new media coverage.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取媒體報導 / Get media coverage',
        description='根據 ID 獲取媒體報導詳情。\n\nGet media coverage details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新媒體報導 / Update media coverage',
        description='更新媒體報導資訊。\n\nUpdate media coverage information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新媒體報導 / Partial update media coverage',
        description='部分更新媒體報導資訊。\n\nPartially update media coverage information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除媒體報導 / Delete media coverage',
        description='刪除媒體報導。\n\nDelete media coverage.'
    ),
    summary=extend_schema(
        tags=['Business'],
        summary='媒體報導摘要 / Media coverage summary',
        description='獲取媒體報導摘要統計。\n\nGet media coverage summary statistics.'
    ),
)

IPOMandateViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 IPO 委託 / List IPO mandates',
        description='獲取所有 IPO 委託列表。\n\nGet all IPO mandates list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建 IPO 委託 / Create IPO mandate',
        description='創建新的 IPO 委託。\n\nCreate a new IPO mandate.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 IPO 委託 / Get IPO mandate',
        description='根據 ID 獲取 IPO 委託詳情。\n\nGet IPO mandate details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 IPO 委託 / Update IPO mandate',
        description='更新 IPO 委託資訊。\n\nUpdate IPO mandate information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 IPO 委託 / Partial update IPO mandate',
        description='部分更新 IPO 委託資訊。\n\nPartially update IPO mandate information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 IPO 委託 / Delete IPO mandate',
        description='刪除 IPO 委託。\n\nDelete IPO mandate.'
    ),
    summary=extend_schema(
        tags=['Business'],
        summary='IPO 委託摘要 / IPO mandate summary',
        description='獲取 IPO 委託摘要統計。\n\nGet IPO mandate summary statistics.'
    ),
    deal_funnel=extend_schema(
        tags=['Business'],
        summary='IPO 交易漏斗 / IPO deal funnel',
        description='獲取 IPO 交易漏斗資料。\n\nGet IPO deal funnel data.'
    ),
)

ServiceRevenueViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出服務營收 / List service revenues',
        description='獲取所有服務營收記錄。\n\nGet all service revenue records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建服務營收 / Create service revenue',
        description='創建新的服務營收記錄。\n\nCreate a new service revenue record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取服務營收 / Get service revenue',
        description='根據 ID 獲取服務營收詳情。\n\nGet service revenue details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新服務營收 / Update service revenue',
        description='更新服務營收資訊。\n\nUpdate service revenue information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新服務營收 / Partial update service revenue',
        description='部分更新服務營收資訊。\n\nPartially update service revenue information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除服務營收 / Delete service revenue',
        description='刪除服務營收記錄。\n\nDelete service revenue record.'
    ),
    by_service=extend_schema(
        tags=['Business'],
        summary='按服務類型分組營收 / Revenue by service type',
        description='獲取按服務類型分組的營收。\n\nGet revenue grouped by service type.'
    ),
)

ActiveEngagementViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出活躍業務 / List active engagements',
        description='獲取所有活躍業務列表。\n\nGet all active engagements list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建業務 / Create engagement',
        description='創建新的業務。\n\nCreate a new engagement.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取業務 / Get engagement',
        description='根據 ID 獲取業務詳情。\n\nGet engagement details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新業務 / Update engagement',
        description='更新業務資訊。\n\nUpdate engagement information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新業務 / Partial update engagement',
        description='部分更新業務資訊。\n\nPartially update engagement information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除業務 / Delete engagement',
        description='刪除業務。\n\nDelete engagement.'
    ),
    summary=extend_schema(
        tags=['Business'],
        summary='活躍業務摘要 / Active engagements summary',
        description='獲取活躍業務摘要統計。\n\nGet active engagements summary statistics.'
    ),
)

ClientPerformanceViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出客戶績效 / List client performance',
        description='獲取所有客戶績效記錄。\n\nGet all client performance records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建客戶績效 / Create client performance',
        description='創建新的客戶績效記錄。\n\nCreate a new client performance record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取客戶績效 / Get client performance',
        description='根據 ID 獲取客戶績效詳情。\n\nGet client performance details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新客戶績效 / Update client performance',
        description='更新客戶績效資訊。\n\nUpdate client performance information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新客戶績效 / Partial update client performance',
        description='部分更新客戶績效資訊。\n\nPartially update client performance information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除客戶績效 / Delete client performance',
        description='刪除客戶績效記錄。\n\nDelete client performance record.'
    ),
)

ClientIndustryViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出客戶行業 / List client industries',
        description='獲取所有客戶行業分類。\n\nGet all client industry classifications.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建客戶行業 / Create client industry',
        description='創建新的客戶行業分類。\n\nCreate a new client industry classification.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取客戶行業 / Get client industry',
        description='根據 ID 獲取客戶行業詳情。\n\nGet client industry details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新客戶行業 / Update client industry',
        description='更新客戶行業資訊。\n\nUpdate client industry information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新客戶行業 / Partial update client industry',
        description='部分更新客戶行業資訊。\n\nPartially update client industry information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除客戶行業 / Delete client industry',
        description='刪除客戶行業分類。\n\nDelete client industry classification.'
    ),
)

MediaSentimentRecordViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出媒體情緒記錄 / List media sentiment records',
        description='獲取所有媒體情緒記錄。\n\nGet all media sentiment records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建媒體情緒記錄 / Create media sentiment record',
        description='創建新的媒體情緒記錄。\n\nCreate a new media sentiment record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取媒體情緒記錄 / Get media sentiment record',
        description='根據 ID 獲取媒體情緒記錄詳情。\n\nGet media sentiment record details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新媒體情緒記錄 / Update media sentiment record',
        description='更新媒體情緒記錄資訊。\n\nUpdate media sentiment record information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新媒體情緒記錄 / Partial update media sentiment record',
        description='部分更新媒體情緒記錄資訊。\n\nPartially update media sentiment record information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除媒體情緒記錄 / Delete media sentiment record',
        description='刪除媒體情緒記錄。\n\nDelete media sentiment record.'
    ),
    trend=extend_schema(
        tags=['Business'],
        summary='媒體情緒趨勢 / Media sentiment trend',
        description='獲取媒體情緒趨勢資料。\n\nGet media sentiment trend data.'
    ),
)

RevenueTrendViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出營收趨勢 / List revenue trends',
        description='獲取所有營收趨勢記錄。\n\nGet all revenue trend records.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='創建營收趨勢 / Create revenue trend',
        description='創建新的營收趨勢記錄。\n\nCreate a new revenue trend record.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取營收趨勢 / Get revenue trend',
        description='根據 ID 獲取營收趨勢詳情。\n\nGet revenue trend details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新營收趨勢 / Update revenue trend',
        description='更新營收趨勢資訊。\n\nUpdate revenue trend information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新營收趨勢 / Partial update revenue trend',
        description='部分更新營收趨勢資訊。\n\nPartially update revenue trend information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除營收趨勢 / Delete revenue trend',
        description='刪除營收趨勢記錄。\n\nDelete revenue trend record.'
    ),
    yearly=extend_schema(
        tags=['Business'],
        summary='年度營收摘要 / Yearly revenue summary',
        description='獲取年度營收摘要資料。\n\nGet yearly revenue summary data.'
    ),
)

BMIDocumentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['Business'],
        summary='列出 BMI 文件 / List BMI documents',
        description='獲取所有 BMI 文件列表。\n\nGet all BMI documents list.'
    ),
    create=extend_schema(
        tags=['Business'],
        summary='上傳 BMI 文件 / Upload BMI document',
        description='上傳新的 BMI 文件。\n\nUpload a new BMI document.'
    ),
    retrieve=extend_schema(
        tags=['Business'],
        summary='獲取 BMI 文件 / Get BMI document',
        description='根據 ID 獲取 BMI 文件詳情。\n\nGet BMI document details by ID.'
    ),
    update=extend_schema(
        tags=['Business'],
        summary='更新 BMI 文件 / Update BMI document',
        description='更新 BMI 文件資訊。\n\nUpdate BMI document information.'
    ),
    partial_update=extend_schema(
        tags=['Business'],
        summary='部分更新 BMI 文件 / Partial update BMI document',
        description='部分更新 BMI 文件資訊。\n\nPartially update BMI document information.'
    ),
    destroy=extend_schema(
        tags=['Business'],
        summary='刪除 BMI 文件 / Delete BMI document',
        description='刪除 BMI 文件。\n\nDelete BMI document.'
    ),
)
