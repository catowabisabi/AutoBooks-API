"""
HRMS Schema Extensions
人力資源模組 API 文檔標籤和說明
"""
from drf_spectacular.utils import extend_schema, extend_schema_view


DesignationViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出職位 / List designations',
        description='獲取所有職位（職稱）列表。\n\nGet all designations (job titles) list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建職位 / Create designation',
        description='創建新的職位。\n\nCreate a new designation.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取職位 / Get designation',
        description='根據 ID 獲取職位詳情。\n\nGet designation details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新職位 / Update designation',
        description='更新職位資訊。\n\nUpdate designation information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新職位 / Partial update designation',
        description='部分更新職位資訊。\n\nPartially update designation information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除職位 / Delete designation',
        description='刪除職位。\n\nDelete designation.'
    ),
)

DepartmentViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出部門 / List departments',
        description='獲取所有部門列表。\n\nGet all departments list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建部門 / Create department',
        description='創建新的部門。\n\nCreate a new department.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取部門 / Get department',
        description='根據 ID 獲取部門詳情。\n\nGet department details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新部門 / Update department',
        description='更新部門資訊。\n\nUpdate department information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新部門 / Partial update department',
        description='部分更新部門資訊。\n\nPartially update department information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除部門 / Delete department',
        description='刪除部門。\n\nDelete department.'
    ),
    tree=extend_schema(
        tags=['HRMS'],
        summary='部門樹狀結構 / Department tree',
        description='獲取部門的階層樹狀結構。\n\nGet department hierarchy as tree.'
    ),
)

EmployeeViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出員工 / List employees',
        description='獲取所有員工列表，支援篩選和搜索。\n\nGet all employees list with filtering and search.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建員工 / Create employee',
        description='創建新的員工記錄。\n\nCreate a new employee record.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取員工 / Get employee',
        description='根據 ID 獲取員工詳情。\n\nGet employee details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新員工 / Update employee',
        description='更新員工資訊。\n\nUpdate employee information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新員工 / Partial update employee',
        description='部分更新員工資訊。\n\nPartially update employee information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除員工 / Delete employee',
        description='刪除員工記錄。\n\nDelete employee record.'
    ),
)

LeaveApplicationViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出請假申請 / List leave applications',
        description='獲取所有請假申請列表。\n\nGet all leave applications list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='提交請假申請 / Submit leave application',
        description='提交新的請假申請。\n\nSubmit a new leave application.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取請假申請 / Get leave application',
        description='根據 ID 獲取請假申請詳情。\n\nGet leave application details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新請假申請 / Update leave application',
        description='更新請假申請資訊。\n\nUpdate leave application information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新請假申請 / Partial update leave application',
        description='部分更新請假申請資訊。\n\nPartially update leave application information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除請假申請 / Delete leave application',
        description='刪除請假申請。\n\nDelete leave application.'
    ),
)

PayrollViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出薪資記錄 / List payroll records',
        description='獲取所有薪資記錄列表。\n\nGet all payroll records list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建薪資記錄 / Create payroll record',
        description='創建新的薪資記錄。\n\nCreate a new payroll record.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取薪資記錄 / Get payroll record',
        description='根據 ID 獲取薪資記錄詳情。\n\nGet payroll record details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新薪資記錄 / Update payroll record',
        description='更新薪資記錄資訊。\n\nUpdate payroll record information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新薪資記錄 / Partial update payroll record',
        description='部分更新薪資記錄資訊。\n\nPartially update payroll record information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除薪資記錄 / Delete payroll record',
        description='刪除薪資記錄。\n\nDelete payroll record.'
    ),
)

ProjectViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出 HRMS 專案 / List HRMS projects',
        description='獲取所有 HRMS 專案列表。\n\nGet all HRMS projects list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建 HRMS 專案 / Create HRMS project',
        description='創建新的 HRMS 專案。\n\nCreate a new HRMS project.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取 HRMS 專案 / Get HRMS project',
        description='根據 ID 獲取 HRMS 專案詳情。\n\nGet HRMS project details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新 HRMS 專案 / Update HRMS project',
        description='更新 HRMS 專案資訊。\n\nUpdate HRMS project information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新 HRMS 專案 / Partial update HRMS project',
        description='部分更新 HRMS 專案資訊。\n\nPartially update HRMS project information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除 HRMS 專案 / Delete HRMS project',
        description='刪除 HRMS 專案。\n\nDelete HRMS project.'
    ),
)

TaskViewSetSchema = extend_schema_view(
    list=extend_schema(
        tags=['HRMS'],
        summary='列出任務 / List tasks',
        description='獲取所有任務列表。\n\nGet all tasks list.'
    ),
    create=extend_schema(
        tags=['HRMS'],
        summary='創建任務 / Create task',
        description='創建新的任務。\n\nCreate a new task.'
    ),
    retrieve=extend_schema(
        tags=['HRMS'],
        summary='獲取任務 / Get task',
        description='根據 ID 獲取任務詳情。\n\nGet task details by ID.'
    ),
    update=extend_schema(
        tags=['HRMS'],
        summary='更新任務 / Update task',
        description='更新任務資訊。\n\nUpdate task information.'
    ),
    partial_update=extend_schema(
        tags=['HRMS'],
        summary='部分更新任務 / Partial update task',
        description='部分更新任務資訊。\n\nPartially update task information.'
    ),
    destroy=extend_schema(
        tags=['HRMS'],
        summary='刪除任務 / Delete task',
        description='刪除任務。\n\nDelete task.'
    ),
)
