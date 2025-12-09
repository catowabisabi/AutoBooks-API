"""
AI Service API Views
Provides unified API endpoints for AI chat and analysis
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from django.conf import settings
import base64

from core.libs.ai_service import AIService, AIProvider, get_ai_service
from core.schema_serializers import AIChatRequestSerializer


class AIServiceViewSet(viewsets.ViewSet):
    """
    Unified AI Service API
    
    Endpoints:
    - POST /chat/ - Send a chat message
    - POST /chat-with-history/ - Chat with conversation history
    - POST /analyze-image/ - Analyze an image
    - GET /providers/ - List available providers
    - GET /models/ - Get available models for a provider
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]
    serializer_class = AIChatRequestSerializer
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """
        Send a chat message to AI
        
        Request body:
        {
            "message": "Your question here",
            "provider": "openai" | "gemini" | "deepseek",  // optional, default: openai
            "model": "gpt-4o-mini",  // optional
            "system_prompt": "You are a helpful assistant",  // optional
            "temperature": 0.7,  // optional
            "max_tokens": 2000  // optional
        }
        """
        message = request.data.get('message')
        if not message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = request.data.get('provider', 'openai')
        model = request.data.get('model')
        system_prompt = request.data.get('system_prompt')
        temperature = float(request.data.get('temperature', 0.7))
        max_tokens = int(request.data.get('max_tokens', 2000))
        
        try:
            ai = get_ai_service(provider=provider, model=model)
            response = ai.chat(
                message=message,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return Response({
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='chat-with-history')
    def chat_with_history(self, request):
        """
        Chat with conversation history
        
        Request body:
        {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ],
            "provider": "openai",  // optional
            "model": "gpt-4o-mini",  // optional
            "system_prompt": "You are helpful",  // optional
            "temperature": 0.7,  // optional
            "max_tokens": 2000  // optional
        }
        """
        messages = request.data.get('messages')
        if not messages or not isinstance(messages, list):
            return Response(
                {"error": "Messages array is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = request.data.get('provider', 'openai')
        model = request.data.get('model')
        system_prompt = request.data.get('system_prompt')
        temperature = float(request.data.get('temperature', 0.7))
        max_tokens = int(request.data.get('max_tokens', 2000))
        
        try:
            ai = get_ai_service(provider=provider, model=model)
            response = ai.chat_with_history(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return Response({
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='analyze-image')
    def analyze_image(self, request):
        """
        Analyze an image with AI vision
        
        Request body (JSON):
        {
            "image": "base64_encoded_image_data",
            "prompt": "What's in this image?",
            "provider": "gemini" | "openai",  // optional, default: gemini
            "mime_type": "image/jpeg"  // optional
        }
        
        Or multipart form:
        - image: file upload
        - prompt: text
        - provider: text (optional)
        """
        # Handle file upload or base64
        image_file = request.FILES.get('image')
        image_base64 = request.data.get('image')
        
        if image_file:
            image_data = image_file.read()
            mime_type = image_file.content_type or 'image/jpeg'
        elif image_base64:
            try:
                image_data = base64.b64decode(image_base64)
            except Exception:
                return Response(
                    {"error": "Invalid base64 image data"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            mime_type = request.data.get('mime_type', 'image/jpeg')
        else:
            return Response(
                {"error": "Image is required (file upload or base64)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        prompt = request.data.get('prompt', 'Describe this image in detail.')
        provider = request.data.get('provider', 'gemini')
        
        try:
            ai = get_ai_service(provider=provider)
            response = ai.analyze_image(
                image_data=image_data,
                prompt=prompt,
                mime_type=mime_type
            )
            
            return Response({
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage
            })
            
        except NotImplementedError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def providers(self, request):
        """
        Get list of available AI providers and their status
        """
        providers_status = []
        
        for provider in AIProvider:
            # Check if API key is configured
            key_mapping = {
                AIProvider.OPENAI: 'OPENAI_API_KEY',
                AIProvider.GEMINI: 'GEMINI_API_KEY',
                AIProvider.DEEPSEEK: 'DEEPSEEK_API_KEY',
            }
            
            key_name = key_mapping.get(provider)
            api_key = getattr(settings, key_name, '') if key_name else ''
            is_configured = bool(api_key)
            
            providers_status.append({
                "name": provider.value,
                "display_name": provider.name,
                "is_configured": is_configured,
                "default_model": AIService.DEFAULT_MODELS.get(provider)
            })
        
        return Response({"providers": providers_status})
    
    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        Get available models for a provider
        
        Query params:
        - provider: "openai" | "gemini" | "deepseek"
        """
        provider_name = request.query_params.get('provider', 'openai')
        
        models_by_provider = {
            "openai": [
                {"name": "gpt-4o", "description": "Most capable GPT-4 model", "vision": True},
                {"name": "gpt-4o-mini", "description": "Affordable, fast GPT-4 model", "vision": True},
                {"name": "gpt-4-turbo", "description": "GPT-4 Turbo with vision", "vision": True},
                {"name": "gpt-3.5-turbo", "description": "Fast and efficient", "vision": False},
                {"name": "o1-preview", "description": "Advanced reasoning model", "vision": False},
                {"name": "o1-mini", "description": "Efficient reasoning model", "vision": False},
            ],
            "gemini": [
                {"name": "gemini-1.5-pro", "description": "Most capable Gemini model", "vision": True},
                {"name": "gemini-1.5-flash", "description": "Fast and efficient", "vision": True},
                {"name": "gemini-1.0-pro", "description": "Stable production model", "vision": False},
                {"name": "gemini-2.0-flash-exp", "description": "Experimental fast model", "vision": True},
            ],
            "deepseek": [
                {"name": "deepseek-chat", "description": "General chat model", "vision": False},
                {"name": "deepseek-coder", "description": "Code-specialized model", "vision": False},
                {"name": "deepseek-reasoner", "description": "Advanced reasoning", "vision": False},
            ],
            "anthropic": [
                {"name": "claude-3-5-sonnet-20241022", "description": "Latest Claude model", "vision": True},
                {"name": "claude-3-opus-20240229", "description": "Most capable Claude", "vision": True},
                {"name": "claude-3-haiku-20240307", "description": "Fast and efficient", "vision": True},
            ]
        }
        
        models = models_by_provider.get(provider_name.lower(), [])
        
        return Response({
            "provider": provider_name,
            "models": models
        })
    
    @action(detail=False, methods=['post'], url_path='set-default')
    def set_default(self, request):
        """
        Set the default AI provider and model for the user
        
        Request body:
        {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        """
        provider = request.data.get('provider')
        model = request.data.get('model')
        
        if not provider:
            return Response(
                {"error": "Provider is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store in user settings or session
        # For now, return success - in production this would save to UserSettings
        return Response({
            "success": True,
            "message": f"Default set to {provider}/{model or 'default'}",
            "provider": provider,
            "model": model
        })
    
    @action(detail=False, methods=['post'], url_path='test-connection')
    def test_connection(self, request):
        """
        Test connection to an AI provider
        
        Request body:
        {
            "provider": "openai"
        }
        """
        provider = request.data.get('provider', 'openai')
        
        try:
            ai = get_ai_service(provider=provider)
            response = ai.chat(
                message="Hello, please respond with 'Connection successful'",
                max_tokens=50
            )
            
            return Response({
                "success": True,
                "provider": provider,
                "model": response.model,
                "message": "Connection successful"
            })
            
        except Exception as e:
            return Response({
                "success": False,
                "provider": provider,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='module-analyze')
    def module_analyze(self, request):
        """
        Perform module-aware AI analysis
        
        Request body:
        {
            "module": "finance" | "hrms" | "projects" | "kanban" | "calendar" | "email",
            "action": "summarize" | "analyze" | "classify" | "custom",
            "prompt": "Your analysis request",
            "context_data": {...}  // Module-specific data
        }
        """
        module = request.data.get('module')
        action = request.data.get('action', 'analyze')
        prompt = request.data.get('prompt', '')
        context_data = request.data.get('context_data', {})
        provider = request.data.get('provider', 'openai')
        
        if not module:
            return Response(
                {"error": "Module is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Module-specific system prompts
        system_prompts = {
            'finance': """You are a financial analyst AI assistant. Analyze financial data, 
                identify trends, risks, and opportunities. Provide actionable insights for 
                cash flow, expenses, revenue, and compliance.""",
            'hrms': """You are an HR analytics AI assistant. Analyze workforce data, 
                predict attrition risks, evaluate team performance, and provide 
                recommendations for employee engagement and retention.""",
            'projects': """You are a project management AI assistant. Analyze project timelines, 
                identify bottlenecks, assess resource allocation, and provide recommendations 
                for improving project delivery and team productivity.""",
            'kanban': """You are a Kanban workflow AI assistant. Analyze board status, 
                identify workflow inefficiencies, suggest task prioritization, and help 
                optimize work-in-progress limits.""",
            'calendar': """You are a scheduling AI assistant. Analyze calendar patterns, 
                identify time management opportunities, suggest meeting optimizations, 
                and help find focus time blocks.""",
            'email': """You are an email management AI assistant. Analyze email patterns, 
                prioritize communications, extract action items, and help draft 
                professional responses.""",
        }
        
        # Action-specific instructions
        action_instructions = {
            'summarize': 'Provide a concise summary of the key points and metrics.',
            'analyze': 'Perform a detailed analysis and identify patterns, trends, and insights.',
            'classify': 'Categorize and classify the data into meaningful groups with labels.',
            'custom': prompt,
        }
        
        system_prompt = system_prompts.get(module, system_prompts['finance'])
        action_instruction = action_instructions.get(action, action_instructions['analyze'])
        
        # Build the full message
        full_message = f"""[{module.upper()} Module - {action.upper()} Request]

Context Data:
{context_data}

Request: {action_instruction}
{prompt if action != 'custom' else ''}

Please provide:
1. Key findings and insights
2. Specific recommendations
3. Any risks or concerns identified
4. Suggested next steps

Format your response clearly with sections and bullet points."""
        
        try:
            ai = get_ai_service(provider=provider)
            response = ai.chat(
                message=full_message,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            return Response({
                "success": True,
                "module": module,
                "action": action,
                "response": response.content,
                "provider": response.provider,
                "model": response.model,
                "metadata": {
                    "confidence": 0.85,  # Placeholder
                    "timestamp": str(request.auth) if hasattr(request, 'auth') else None,
                }
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
