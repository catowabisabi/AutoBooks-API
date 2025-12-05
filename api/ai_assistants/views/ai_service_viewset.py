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
                {"name": "gpt-4o", "description": "Most capable GPT-4 model"},
                {"name": "gpt-4o-mini", "description": "Affordable, fast GPT-4 model"},
                {"name": "gpt-4-turbo", "description": "GPT-4 Turbo with vision"},
                {"name": "gpt-3.5-turbo", "description": "Fast and efficient"},
            ],
            "gemini": [
                {"name": "gemini-1.5-pro", "description": "Most capable Gemini model"},
                {"name": "gemini-1.5-flash", "description": "Fast and efficient"},
                {"name": "gemini-1.0-pro", "description": "Stable production model"},
            ],
            "deepseek": [
                {"name": "deepseek-chat", "description": "General chat model"},
                {"name": "deepseek-coder", "description": "Code-specialized model"},
            ]
        }
        
        models = models_by_provider.get(provider_name.lower(), [])
        
        return Response({
            "provider": provider_name,
            "models": models
        })
