"""
AI Agent ViewSet
================
REST API for AI Agent operations with autonomous CRUD and logging
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from openai import OpenAI
from django.conf import settings

from ai_assistants.models import (
    AIAgent,
    AIActionLog,
    AIConversation,
    AIActionStatus,
    AIActionType,
)
from ai_assistants.agents.ai_tools import (
    AIToolRegistry,
    BusinessToolExecutor,
)
from core.schema_serializers import AIAgentChatRequestSerializer


class AIAgentViewSet(viewsets.ViewSet):
    """
    ViewSet for AI Agent operations
    
    Endpoints:
    - POST /chat/ - Chat with AI agent and execute actions
    - GET /agents/ - List available agents
    - GET /actions/ - List action history
    - POST /actions/{id}/rollback/ - Rollback an action
    - GET /sessions/ - List conversation sessions
    - GET /tools/ - List available tools
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AIAgentChatRequestSerializer
    
    def get_permissions(self):
        """Allow public access to tools endpoint for testing"""
        if self.action == 'tools':
            return []
        return super().get_permissions()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.openai_client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))
    
    @action(detail=False, methods=['get'])
    def agents(self, request):
        """List available AI agents"""
        agents = AIAgent.objects.filter(is_active=True)
        return Response({
            "agents": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "display_name": a.display_name,
                    "description": a.description,
                    "agent_type": a.agent_type,
                    "auto_execute": a.auto_execute,
                    "allowed_tools": a.allowed_tools,
                }
                for a in agents
            ]
        })
    
    @action(detail=False, methods=['get'])
    def tools(self, request):
        """List available tools"""
        tools = AIToolRegistry.get_all_tools()
        return Response({
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "target_model": t.target_model,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "enum": p.enum,
                        }
                        for p in t.parameters
                    ]
                }
                for t in tools
            ]
        })
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """
        Chat with AI agent - processes natural language and executes actions
        
        Request body:
        {
            "message": "Create an audit project for ABC Corp",
            "session_id": "optional-session-id",
            "agent_id": "optional-agent-uuid",
            "auto_execute": true
        }
        """
        message = request.data.get('message', '')
        session_id = request.data.get('session_id') or str(uuid.uuid4())
        agent_id = request.data.get('agent_id')
        auto_execute = request.data.get('auto_execute', True)
        
        if not message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create agent
        agent = None
        if agent_id:
            try:
                agent = AIAgent.objects.get(pk=agent_id)
            except AIAgent.DoesNotExist:
                pass
        
        if not agent:
            # Use or create default business agent
            agent, _ = AIAgent.objects.get_or_create(
                name='business_agent',
                defaults={
                    'display_name': 'Business CRUD Agent',
                    'description': 'Autonomous agent for managing business data (audits, tax returns, billing, revenue)',
                    'agent_type': 'BUSINESS',
                    'auto_execute': True,
                    'llm_model': 'gpt-4o-mini',
                    'system_prompt': self._get_business_agent_prompt(),
                }
            )
        
        # Get or create conversation
        conversation, created = AIConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user,
                'agent': agent,
                'title': message[:100],
            }
        )
        
        # Add user message to history
        messages = conversation.messages or []
        messages.append({
            "role": "user",
            "content": message,
            "timestamp": timezone.now().isoformat()
        })
        
        # Get available tools
        tools = AIToolRegistry.to_openai_tools(agent.allowed_tools if agent.allowed_tools else None)
        
        # Build conversation for OpenAI
        openai_messages = [
            {"role": "system", "content": agent.system_prompt or self._get_business_agent_prompt()}
        ]
        
        # Add history (last 10 messages)
        for msg in messages[-10:]:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Call OpenAI with function calling
        try:
            response = self.openai_client.chat.completions.create(
                model=agent.llm_model or 'gpt-4o-mini',
                messages=openai_messages,
                tools=tools,
                tool_choice="auto",
                temperature=agent.temperature or 0.7,
            )
        except Exception as e:
            return Response(
                {"error": f"AI service error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls
        
        # Process tool calls if any
        actions_taken = []
        if tool_calls and auto_execute:
            executor = BusinessToolExecutor(
                user=request.user,
                session_id=session_id,
                agent=agent
            )
            
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool
                handler = AIToolRegistry.get_handler(tool_name)
                if handler:
                    result = handler(executor, **tool_args)
                    actions_taken.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": result
                    })
            
            # Get follow-up response after tool execution
            openai_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })
            
            for i, action in enumerate(actions_taken):
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_calls[i].id,
                    "content": json.dumps(action["result"])
                })
            
            # Get final response
            try:
                final_response = self.openai_client.chat.completions.create(
                    model=agent.llm_model or 'gpt-4o-mini',
                    messages=openai_messages,
                    temperature=agent.temperature or 0.7,
                )
                assistant_content = final_response.choices[0].message.content
            except Exception as e:
                assistant_content = f"Actions completed. Error getting summary: {str(e)}"
        else:
            assistant_content = assistant_message.content or "I understand. How can I help?"
            
            # If there are tool calls but auto_execute is false, explain what would be done
            if tool_calls and not auto_execute:
                pending_actions = []
                for tc in tool_calls:
                    pending_actions.append({
                        "tool": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    })
                assistant_content += f"\n\nI would like to execute the following actions (pending approval):\n{json.dumps(pending_actions, indent=2)}"
        
        # Add assistant message to history
        messages.append({
            "role": "assistant",
            "content": assistant_content,
            "timestamp": timezone.now().isoformat(),
            "actions": actions_taken if actions_taken else None
        })
        
        # Update conversation
        conversation.messages = messages
        conversation.total_actions += len(actions_taken)
        conversation.successful_actions += sum(1 for a in actions_taken if a["result"].get("success"))
        conversation.failed_actions += sum(1 for a in actions_taken if not a["result"].get("success"))
        conversation.save()
        
        return Response({
            "session_id": session_id,
            "message": assistant_content,
            "actions_taken": actions_taken,
            "conversation_stats": {
                "total_actions": conversation.total_actions,
                "successful_actions": conversation.successful_actions,
                "failed_actions": conversation.failed_actions,
            }
        })
    
    @action(detail=False, methods=['get'])
    def actions(self, request):
        """List action history with optional filters"""
        session_id = request.query_params.get('session_id')
        status_filter = request.query_params.get('status')
        model_filter = request.query_params.get('model')
        limit = int(request.query_params.get('limit', 50))
        
        queryset = AIActionLog.objects.filter(triggered_by=request.user)
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if model_filter:
            queryset = queryset.filter(target_model__icontains=model_filter)
        
        queryset = queryset.order_by('-created_at')[:limit]
        
        return Response({
            "actions": [
                {
                    "id": str(a.id),
                    "action_type": a.action_type,
                    "status": a.status,
                    "target_model": a.target_model,
                    "target_id": a.target_id,
                    "data_before": a.data_before,
                    "data_after": a.data_after,
                    "ai_reasoning": a.ai_reasoning,
                    "error_message": a.error_message,
                    "can_rollback": a.can_rollback,
                    "created_at": a.created_at.isoformat(),
                    "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                    "rolled_back_at": a.rolled_back_at.isoformat() if a.rolled_back_at else None,
                }
                for a in queryset
            ]
        })
    
    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback_action(self, request, pk=None):
        """Rollback a specific action"""
        reason = request.data.get('reason', '')
        
        executor = BusinessToolExecutor(
            user=request.user,
            session_id=str(uuid.uuid4()),
        )
        
        result = executor.rollback_action(pk, reason)
        
        if result["success"]:
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def sessions(self, request):
        """List conversation sessions"""
        limit = int(request.query_params.get('limit', 20))
        
        sessions = AIConversation.objects.filter(
            user=request.user
        ).order_by('-updated_at')[:limit]
        
        return Response({
            "sessions": [
                {
                    "session_id": s.session_id,
                    "title": s.title,
                    "agent": s.agent.display_name if s.agent else None,
                    "message_count": len(s.messages) if s.messages else 0,
                    "total_actions": s.total_actions,
                    "successful_actions": s.successful_actions,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ]
        })
    
    @action(detail=False, methods=['get'], url_path='sessions/(?P<session_id>[^/.]+)')
    def get_session(self, request, session_id=None):
        """Get a specific session with full history"""
        try:
            session = AIConversation.objects.get(
                session_id=session_id,
                user=request.user
            )
        except AIConversation.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get actions for this session
        actions = AIActionLog.objects.filter(
            session_id=session_id
        ).order_by('created_at')
        
        return Response({
            "session_id": session.session_id,
            "title": session.title,
            "agent": {
                "id": str(session.agent.id),
                "name": session.agent.display_name,
            } if session.agent else None,
            "messages": session.messages,
            "actions": [
                {
                    "id": str(a.id),
                    "action_type": a.action_type,
                    "status": a.status,
                    "target_model": a.target_model,
                    "target_id": a.target_id,
                    "can_rollback": a.can_rollback,
                    "created_at": a.created_at.isoformat(),
                }
                for a in actions
            ],
            "stats": {
                "total_actions": session.total_actions,
                "successful_actions": session.successful_actions,
                "failed_actions": session.failed_actions,
            },
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        })
    
    def _get_business_agent_prompt(self) -> str:
        """Get the system prompt for business agent"""
        return """You are an AI assistant for an ERP system that manages business operations including audit projects, tax returns, billable hours, and revenue.

You have access to tools to create, read, update, and delete records in the database. When a user asks you to perform an action, use the appropriate tool.

IMPORTANT RULES:
1. Always confirm what action you're taking before executing
2. For CREATE operations, extract all required information from the user's request
3. For UPDATE operations, identify the record first then apply changes
4. For DELETE operations, confirm the target before proceeding
5. If information is missing, ask the user for it
6. After executing an action, summarize what was done
7. All actions are logged and can be rolled back if needed

Available models and their purposes:
- AuditProject: Audit engagements for clients (financial, internal, tax audits)
- TaxReturnCase: Tax filing cases (profits tax, salaries tax, property tax)
- BillableHour: Time tracking for employees working on projects
- Revenue: Income records from clients
- Company: Client companies

When creating records:
- client_id is a UUID reference to a Company
- project_id is a UUID reference to an AuditProject (optional for some models)
- Dates should be in YYYY-MM-DD format
- Amounts/rates are decimal numbers

Be helpful, accurate, and always explain what you're doing."""
