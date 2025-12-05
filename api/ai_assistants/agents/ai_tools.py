"""
AI Agent Tools Registry
========================
CRUD operations for Business models with automatic action logging

Each tool:
1. Validates input
2. Logs the action to AIActionLog
3. Executes the operation
4. Returns result with action_id for tracking
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from django.db import models, transaction
from django.apps import apps
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class ToolDefinition:
    """Definition of an AI tool"""
    name: str
    description: str
    category: str  # crud, query, analysis
    target_model: str  # e.g., 'business.AuditProject'
    parameters: List[ToolParameter] = field(default_factory=list)
    requires_approval: bool = False
    
    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class AIToolRegistry:
    """
    Registry for all AI tools
    Provides CRUD operations with automatic logging
    """
    
    _tools: Dict[str, ToolDefinition] = {}
    _handlers: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, tool: ToolDefinition, handler: Callable):
        """Register a tool with its handler"""
        cls._tools[tool.name] = tool
        cls._handlers[tool.name] = handler
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name"""
        return cls._tools.get(name)
    
    @classmethod
    def get_handler(cls, name: str) -> Optional[Callable]:
        """Get a tool handler by name"""
        return cls._handlers.get(name)
    
    @classmethod
    def get_all_tools(cls) -> List[ToolDefinition]:
        """Get all registered tools"""
        return list(cls._tools.values())
    
    @classmethod
    def get_tools_by_category(cls, category: str) -> List[ToolDefinition]:
        """Get tools by category"""
        return [t for t in cls._tools.values() if t.category == category]
    
    @classmethod
    def get_tools_for_model(cls, model_name: str) -> List[ToolDefinition]:
        """Get tools for a specific model"""
        return [t for t in cls._tools.values() if t.target_model == model_name]
    
    @classmethod
    def to_openai_tools(cls, tool_names: Optional[List[str]] = None) -> List[dict]:
        """Convert tools to OpenAI tools format"""
        tools = cls._tools.values()
        if tool_names:
            tools = [t for t in tools if t.name in tool_names]
        return [{"type": "function", "function": t.to_openai_function()} for t in tools]


class BusinessToolExecutor:
    """
    Executes business model CRUD operations with logging
    """
    
    def __init__(self, user, session_id: str, agent=None):
        self.user = user
        self.session_id = session_id
        self.agent = agent
    
    def _get_model_class(self, model_path: str) -> Type[models.Model]:
        """Get Django model class from path like 'business.AuditProject'"""
        app_label, model_name = model_path.split('.')
        return apps.get_model(app_label, model_name)
    
    def _serialize_instance(self, instance) -> dict:
        """Serialize a model instance to dict for logging"""
        if instance is None:
            return {}
        
        data = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            elif hasattr(value, 'pk'):  # ForeignKey
                value = str(value.pk) if value else None
            data[field.name] = value
        return data
    
    def _create_action_log(
        self,
        action_type: str,
        target_model: str,
        target_id: str = '',
        data_before: dict = None,
        data_after: dict = None,
        user_prompt: str = '',
        ai_reasoning: str = '',
        ai_confidence: float = 0.8
    ):
        """Create an action log entry"""
        from ai_assistants.models import AIActionLog, AIActionStatus
        
        return AIActionLog.objects.create(
            agent=self.agent,
            triggered_by=self.user,
            session_id=self.session_id,
            action_type=action_type,
            status=AIActionStatus.PENDING,
            target_model=target_model,
            target_id=target_id,
            data_before=data_before or {},
            data_after=data_after or {},
            user_prompt=user_prompt,
            ai_reasoning=ai_reasoning,
            ai_confidence=ai_confidence
        )
    
    def _execute_action(self, action_log, execute_func: Callable) -> dict:
        """Execute an action and update the log"""
        from ai_assistants.models import AIActionStatus
        
        start_time = timezone.now()
        try:
            result = execute_func()
            
            action_log.status = AIActionStatus.EXECUTED
            action_log.executed_at = timezone.now()
            action_log.execution_duration_ms = int(
                (timezone.now() - start_time).total_seconds() * 1000
            )
            action_log.save()
            
            return {
                "success": True,
                "action_id": str(action_log.id),
                "result": result
            }
        except Exception as e:
            action_log.status = AIActionStatus.FAILED
            action_log.error_message = str(e)
            action_log.save()
            
            return {
                "success": False,
                "action_id": str(action_log.id),
                "error": str(e)
            }
    
    @transaction.atomic
    def create_record(
        self,
        model_path: str,
        data: dict,
        user_prompt: str = '',
        ai_reasoning: str = ''
    ) -> dict:
        """Create a new record"""
        from ai_assistants.models import AIActionType
        
        Model = self._get_model_class(model_path)
        
        # Create action log first
        action_log = self._create_action_log(
            action_type=AIActionType.CREATE,
            target_model=model_path,
            data_after=data,
            user_prompt=user_prompt,
            ai_reasoning=ai_reasoning
        )
        
        def execute():
            instance = Model.objects.create(**data)
            action_log.target_id = str(instance.pk)
            action_log.data_after = self._serialize_instance(instance)
            action_log.save()
            return self._serialize_instance(instance)
        
        return self._execute_action(action_log, execute)
    
    @transaction.atomic
    def update_record(
        self,
        model_path: str,
        record_id: str,
        data: dict,
        user_prompt: str = '',
        ai_reasoning: str = ''
    ) -> dict:
        """Update an existing record"""
        from ai_assistants.models import AIActionType
        
        Model = self._get_model_class(model_path)
        
        try:
            instance = Model.objects.get(pk=record_id)
        except Model.DoesNotExist:
            return {"success": False, "error": f"Record {record_id} not found"}
        
        # Capture before state
        data_before = self._serialize_instance(instance)
        
        # Create action log
        action_log = self._create_action_log(
            action_type=AIActionType.UPDATE,
            target_model=model_path,
            target_id=record_id,
            data_before=data_before,
            data_after=data,
            user_prompt=user_prompt,
            ai_reasoning=ai_reasoning
        )
        
        def execute():
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            instance.save()
            action_log.data_after = self._serialize_instance(instance)
            action_log.save()
            return self._serialize_instance(instance)
        
        return self._execute_action(action_log, execute)
    
    @transaction.atomic
    def delete_record(
        self,
        model_path: str,
        record_id: str,
        user_prompt: str = '',
        ai_reasoning: str = ''
    ) -> dict:
        """Delete a record (soft delete if is_active exists)"""
        from ai_assistants.models import AIActionType
        
        Model = self._get_model_class(model_path)
        
        try:
            instance = Model.objects.get(pk=record_id)
        except Model.DoesNotExist:
            return {"success": False, "error": f"Record {record_id} not found"}
        
        # Capture before state
        data_before = self._serialize_instance(instance)
        
        # Create action log
        action_log = self._create_action_log(
            action_type=AIActionType.DELETE,
            target_model=model_path,
            target_id=record_id,
            data_before=data_before,
            user_prompt=user_prompt,
            ai_reasoning=ai_reasoning
        )
        
        def execute():
            # Soft delete if possible
            if hasattr(instance, 'is_active'):
                instance.is_active = False
                instance.save()
                return {"deleted": True, "soft_delete": True, "id": record_id}
            else:
                instance.delete()
                return {"deleted": True, "soft_delete": False, "id": record_id}
        
        return self._execute_action(action_log, execute)
    
    def query_records(
        self,
        model_path: str,
        filters: dict = None,
        order_by: str = '-created_at',
        limit: int = 50
    ) -> dict:
        """Query records with filters"""
        from ai_assistants.models import AIActionType
        
        Model = self._get_model_class(model_path)
        
        # Create query action log
        action_log = self._create_action_log(
            action_type=AIActionType.QUERY,
            target_model=model_path,
            data_after={"filters": filters, "order_by": order_by, "limit": limit}
        )
        
        def execute():
            queryset = Model.objects.all()
            
            if filters:
                queryset = queryset.filter(**filters)
            
            if order_by:
                queryset = queryset.order_by(order_by)
            
            queryset = queryset[:limit]
            
            results = [self._serialize_instance(obj) for obj in queryset]
            return {
                "count": len(results),
                "records": results
            }
        
        return self._execute_action(action_log, execute)
    
    @transaction.atomic
    def rollback_action(self, action_id: str, reason: str = '') -> dict:
        """Rollback a previously executed action"""
        from ai_assistants.models import AIActionLog, AIActionStatus, AIActionType
        
        try:
            action_log = AIActionLog.objects.get(pk=action_id)
        except AIActionLog.DoesNotExist:
            return {"success": False, "error": f"Action {action_id} not found"}
        
        if not action_log.can_rollback:
            return {"success": False, "error": "This action cannot be rolled back"}
        
        Model = self._get_model_class(action_log.target_model)
        
        try:
            if action_log.action_type == AIActionType.CREATE:
                # Rollback create = delete the created record
                instance = Model.objects.get(pk=action_log.target_id)
                if hasattr(instance, 'is_active'):
                    instance.is_active = False
                    instance.save()
                else:
                    instance.delete()
                    
            elif action_log.action_type == AIActionType.UPDATE:
                # Rollback update = restore previous values
                instance = Model.objects.get(pk=action_log.target_id)
                for key, value in action_log.data_before.items():
                    if hasattr(instance, key) and key not in ['id', 'created_at', 'updated_at']:
                        setattr(instance, key, value)
                instance.save()
                
            elif action_log.action_type == AIActionType.DELETE:
                # Rollback delete = restore the record
                if hasattr(Model, 'is_active'):
                    instance = Model.objects.get(pk=action_log.target_id)
                    instance.is_active = True
                    instance.save()
                else:
                    # Can't rollback hard delete
                    # Try to recreate from data_before
                    data = action_log.data_before.copy()
                    data.pop('updated_at', None)
                    data.pop('created_at', None)
                    Model.objects.create(**data)
            
            # Update action log
            action_log.status = AIActionStatus.ROLLED_BACK
            action_log.rolled_back_at = timezone.now()
            action_log.rolled_back_by = self.user
            action_log.rollback_reason = reason
            action_log.save()
            
            return {
                "success": True,
                "action_id": action_id,
                "message": f"Action rolled back successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# =================================================================
# Register Business Model Tools
# =================================================================

def register_business_tools():
    """Register CRUD tools for all business models"""
    
    # AuditProject Tools
    AIToolRegistry.register(
        ToolDefinition(
            name="create_audit_project",
            description="Create a new audit project for a client. Required: client_id, project_name, audit_type. Optional: start_date, end_date, budget, notes.",
            category="crud",
            target_model="business.AuditProject",
            parameters=[
                ToolParameter("client_id", "string", "UUID of the client company", True),
                ToolParameter("project_name", "string", "Name of the audit project", True),
                ToolParameter("audit_type", "string", "Type of audit", True, enum=[
                    "FINANCIAL", "INTERNAL", "COMPLIANCE", "TAX", "FORENSIC", "IT", "OTHER"
                ]),
                ToolParameter("status", "string", "Project status", False, enum=[
                    "PLANNING", "IN_PROGRESS", "FIELDWORK", "REVIEW", "COMPLETED", "ON_HOLD", "CANCELLED"
                ]),
                ToolParameter("start_date", "string", "Start date (YYYY-MM-DD)", False),
                ToolParameter("end_date", "string", "End date (YYYY-MM-DD)", False),
                ToolParameter("budget", "number", "Project budget", False),
                ToolParameter("notes", "string", "Additional notes", False),
            ]
        ),
        lambda executor, **kwargs: executor.create_record("business.AuditProject", kwargs)
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="update_audit_project",
            description="Update an existing audit project",
            category="crud",
            target_model="business.AuditProject",
            parameters=[
                ToolParameter("id", "string", "UUID of the audit project to update", True),
                ToolParameter("project_name", "string", "New project name", False),
                ToolParameter("status", "string", "New status", False, enum=[
                    "PLANNING", "IN_PROGRESS", "FIELDWORK", "REVIEW", "COMPLETED", "ON_HOLD", "CANCELLED"
                ]),
                ToolParameter("end_date", "string", "New end date (YYYY-MM-DD)", False),
                ToolParameter("budget", "number", "New budget", False),
                ToolParameter("notes", "string", "Updated notes", False),
            ]
        ),
        lambda executor, **kwargs: executor.update_record(
            "business.AuditProject", 
            kwargs.pop('id'), 
            kwargs
        )
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="list_audit_projects",
            description="List audit projects with optional filters",
            category="query",
            target_model="business.AuditProject",
            parameters=[
                ToolParameter("status", "string", "Filter by status", False),
                ToolParameter("client_id", "string", "Filter by client UUID", False),
                ToolParameter("audit_type", "string", "Filter by audit type", False),
                ToolParameter("limit", "integer", "Max results (default 50)", False),
            ]
        ),
        lambda executor, **kwargs: executor.query_records(
            "business.AuditProject",
            {k: v for k, v in kwargs.items() if k != 'limit' and v},
            limit=kwargs.get('limit', 50)
        )
    )
    
    # BillableHour Tools
    AIToolRegistry.register(
        ToolDefinition(
            name="create_billable_hour",
            description="Log billable hours for an employee on a project",
            category="crud",
            target_model="business.BillableHour",
            parameters=[
                ToolParameter("employee_name", "string", "Name of the employee", True),
                ToolParameter("client_id", "string", "UUID of the client company", True),
                ToolParameter("project_id", "string", "UUID of the related project (optional)", False),
                ToolParameter("role", "string", "Employee role", True, enum=[
                    "PARTNER", "SENIOR_MANAGER", "MANAGER", "SENIOR", "STAFF", "INTERN"
                ]),
                ToolParameter("hours", "number", "Number of hours worked", True),
                ToolParameter("hourly_rate", "number", "Hourly rate", True),
                ToolParameter("multiplier", "number", "Rate multiplier (default 1.0)", False),
                ToolParameter("description", "string", "Work description", False),
                ToolParameter("work_date", "string", "Date of work (YYYY-MM-DD)", False),
            ]
        ),
        lambda executor, **kwargs: executor.create_record("business.BillableHour", kwargs)
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="list_billable_hours",
            description="List billable hours with filters",
            category="query",
            target_model="business.BillableHour",
            parameters=[
                ToolParameter("employee_name", "string", "Filter by employee name", False),
                ToolParameter("client_id", "string", "Filter by client UUID", False),
                ToolParameter("role", "string", "Filter by role", False),
                ToolParameter("limit", "integer", "Max results", False),
            ]
        ),
        lambda executor, **kwargs: executor.query_records(
            "business.BillableHour",
            {k: v for k, v in kwargs.items() if k != 'limit' and v},
            limit=kwargs.get('limit', 50)
        )
    )
    
    # Revenue Tools
    AIToolRegistry.register(
        ToolDefinition(
            name="create_revenue",
            description="Record revenue from a client",
            category="crud",
            target_model="business.Revenue",
            parameters=[
                ToolParameter("client_id", "string", "UUID of the client company", True),
                ToolParameter("project_id", "string", "UUID of related project (optional)", False),
                ToolParameter("description", "string", "Revenue description", True),
                ToolParameter("amount", "number", "Revenue amount", True),
                ToolParameter("currency", "string", "Currency code (default HKD)", False),
                ToolParameter("invoice_date", "string", "Invoice date (YYYY-MM-DD)", False),
                ToolParameter("due_date", "string", "Payment due date (YYYY-MM-DD)", False),
                ToolParameter("status", "string", "Payment status", False, enum=[
                    "DRAFT", "INVOICED", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED"
                ]),
            ]
        ),
        lambda executor, **kwargs: executor.create_record("business.Revenue", kwargs)
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="list_revenue",
            description="List revenue records with filters",
            category="query",
            target_model="business.Revenue",
            parameters=[
                ToolParameter("client_id", "string", "Filter by client UUID", False),
                ToolParameter("status", "string", "Filter by status", False),
                ToolParameter("limit", "integer", "Max results", False),
            ]
        ),
        lambda executor, **kwargs: executor.query_records(
            "business.Revenue",
            {k: v for k, v in kwargs.items() if k != 'limit' and v},
            limit=kwargs.get('limit', 50)
        )
    )
    
    # TaxReturnCase Tools
    AIToolRegistry.register(
        ToolDefinition(
            name="create_tax_return",
            description="Create a new tax return case for a client",
            category="crud",
            target_model="business.TaxReturnCase",
            parameters=[
                ToolParameter("client_id", "string", "UUID of the client company", True),
                ToolParameter("tax_year", "string", "Tax year (e.g., 2024)", True),
                ToolParameter("tax_type", "string", "Type of tax return", True, enum=[
                    "PROFITS", "SALARIES", "PROPERTY", "EMPLOYER", "BIR60", "OTHER"
                ]),
                ToolParameter("filing_deadline", "string", "Filing deadline (YYYY-MM-DD)", False),
                ToolParameter("status", "string", "Case status", False, enum=[
                    "NOT_STARTED", "DATA_COLLECTION", "PREPARATION", "REVIEW", "FILED", "ASSESSMENT", "COMPLETED", "OBJECTION"
                ]),
                ToolParameter("notes", "string", "Additional notes", False),
            ]
        ),
        lambda executor, **kwargs: executor.create_record("business.TaxReturnCase", kwargs)
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="list_tax_returns",
            description="List tax return cases with filters",
            category="query",
            target_model="business.TaxReturnCase",
            parameters=[
                ToolParameter("client_id", "string", "Filter by client UUID", False),
                ToolParameter("tax_year", "string", "Filter by tax year", False),
                ToolParameter("status", "string", "Filter by status", False),
                ToolParameter("limit", "integer", "Max results", False),
            ]
        ),
        lambda executor, **kwargs: executor.query_records(
            "business.TaxReturnCase",
            {k: v for k, v in kwargs.items() if k != 'limit' and v},
            limit=kwargs.get('limit', 50)
        )
    )
    
    # Generic Tools
    AIToolRegistry.register(
        ToolDefinition(
            name="list_companies",
            description="List all client companies",
            category="query",
            target_model="business.Company",
            parameters=[
                ToolParameter("is_active", "boolean", "Filter by active status", False),
                ToolParameter("limit", "integer", "Max results", False),
            ]
        ),
        lambda executor, **kwargs: executor.query_records(
            "business.Company",
            {k: v for k, v in kwargs.items() if k != 'limit' and v is not None},
            limit=kwargs.get('limit', 50)
        )
    )
    
    AIToolRegistry.register(
        ToolDefinition(
            name="rollback_action",
            description="Rollback a previously executed AI action by its action_id",
            category="system",
            target_model="ai_assistants.AIActionLog",
            parameters=[
                ToolParameter("action_id", "string", "UUID of the action to rollback", True),
                ToolParameter("reason", "string", "Reason for rollback", False),
            ]
        ),
        lambda executor, **kwargs: executor.rollback_action(
            kwargs['action_id'],
            kwargs.get('reason', '')
        )
    )


# Register tools on module load
register_business_tools()
