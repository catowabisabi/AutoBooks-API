"""
Unified AI Service for Wisematic ERP
Supports: OpenAI (GPT), Google Gemini, DeepSeek
"""
import os
from enum import Enum
from typing import Optional, Dict, Any, List
from django.conf import settings
from dataclasses import dataclass


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class AIService:
    """
    Unified AI service that can switch between different AI providers.
    
    Usage:
        ai = AIService(provider=AIProvider.OPENAI)
        response = ai.chat("Hello, how are you?")
        
        # Or with specific model
        ai = AIService(provider=AIProvider.GEMINI, model="gemini-1.5-pro")
        response = ai.chat("Analyze this data...")
    """
    
    # Default models for each provider
    DEFAULT_MODELS = {
        AIProvider.OPENAI: "gpt-4o-mini",
        AIProvider.GEMINI: "gemini-1.5-pro",
        AIProvider.DEEPSEEK: "deepseek-chat",
    }
    
    def __init__(
        self, 
        provider: AIProvider = AIProvider.OPENAI,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.model = model or self.DEFAULT_MODELS.get(provider)
        self._api_key = api_key
        self._client = None
        
    @property
    def api_key(self) -> str:
        """Get API key from parameter, settings, or environment"""
        if self._api_key:
            return self._api_key
            
        key_mapping = {
            AIProvider.OPENAI: ('OPENAI_API_KEY', 'OPENAI_API_KEY'),
            AIProvider.GEMINI: ('GEMINI_API_KEY', 'GOOGLE_API_KEY'),
            AIProvider.DEEPSEEK: ('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY'),
        }
        
        settings_key, env_key = key_mapping.get(self.provider, ('', ''))
        
        # Try settings first, then environment
        return getattr(settings, settings_key, '') or os.getenv(env_key, '')
    
    def _get_openai_client(self):
        """Initialize OpenAI client"""
        from openai import OpenAI
        return OpenAI(api_key=self.api_key)
    
    def _get_deepseek_client(self):
        """Initialize DeepSeek client (OpenAI compatible)"""
        from openai import OpenAI
        base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        return OpenAI(api_key=self.api_key, base_url=base_url)
    
    def _get_gemini_client(self):
        """Initialize Gemini client"""
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(self.model)
    
    def chat(
        self, 
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AIResponse:
        """
        Send a chat message to the AI provider.
        
        Args:
            message: The user message
            system_prompt: Optional system prompt
            temperature: Creativity level (0-1)
            max_tokens: Maximum response tokens
            
        Returns:
            AIResponse object with content and metadata
        """
        if self.provider == AIProvider.GEMINI:
            return self._chat_gemini(message, system_prompt, temperature, max_tokens, **kwargs)
        else:
            return self._chat_openai_compatible(message, system_prompt, temperature, max_tokens, **kwargs)
    
    def _chat_openai_compatible(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AIResponse:
        """Chat using OpenAI-compatible API (OpenAI, DeepSeek)"""
        if self.provider == AIProvider.DEEPSEEK:
            client = self._get_deepseek_client()
        else:
            client = self._get_openai_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return AIResponse(
            content=response.choices[0].message.content,
            provider=self.provider.value,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            raw_response=response
        )
    
    def _chat_gemini(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AIResponse:
        """Chat using Google Gemini API"""
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        model = genai.GenerativeModel(
            self.model,
            generation_config=generation_config,
            system_instruction=system_prompt if system_prompt else None
        )
        
        response = model.generate_content(message)
        
        return AIResponse(
            content=response.text,
            provider=self.provider.value,
            model=self.model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
            } if hasattr(response, 'usage_metadata') else None,
            raw_response=response
        )
    
    def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AIResponse:
        """
        Chat with conversation history.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system prompt
            temperature: Creativity level (0-1)
            max_tokens: Maximum response tokens
            
        Returns:
            AIResponse object
        """
        if self.provider == AIProvider.GEMINI:
            return self._chat_with_history_gemini(messages, system_prompt, temperature, max_tokens, **kwargs)
        else:
            return self._chat_with_history_openai(messages, system_prompt, temperature, max_tokens, **kwargs)
    
    def _chat_with_history_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AIResponse:
        """Chat with history using OpenAI-compatible API"""
        if self.provider == AIProvider.DEEPSEEK:
            client = self._get_deepseek_client()
        else:
            client = self._get_openai_client()
        
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)
        
        response = client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return AIResponse(
            content=response.choices[0].message.content,
            provider=self.provider.value,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            raw_response=response
        )
    
    def _chat_with_history_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AIResponse:
        """Chat with history using Gemini API"""
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        model = genai.GenerativeModel(
            self.model,
            generation_config=generation_config,
            system_instruction=system_prompt if system_prompt else None
        )
        
        # Convert messages to Gemini format
        chat = model.start_chat(history=[])
        
        # Add history
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            chat.history.append({
                "role": role,
                "parts": [msg["content"]]
            })
        
        # Send last message
        last_message = messages[-1]["content"]
        response = chat.send_message(last_message)
        
        return AIResponse(
            content=response.text,
            provider=self.provider.value,
            model=self.model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
            } if hasattr(response, 'usage_metadata') else None,
            raw_response=response
        )
    
    def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str = "image/jpeg"
    ) -> AIResponse:
        """
        Analyze an image with AI vision capabilities.
        Currently supports Gemini and OpenAI GPT-4 Vision.
        
        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            mime_type: Image MIME type
            
        Returns:
            AIResponse object
        """
        if self.provider == AIProvider.GEMINI:
            return self._analyze_image_gemini(image_data, prompt, mime_type)
        elif self.provider == AIProvider.OPENAI:
            return self._analyze_image_openai(image_data, prompt, mime_type)
        else:
            raise NotImplementedError(f"Image analysis not supported for {self.provider.value}")
    
    def _analyze_image_gemini(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str
    ) -> AIResponse:
        """Analyze image using Gemini"""
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        
        response = model.generate_content([
            {"mime_type": mime_type, "data": image_data},
            prompt
        ])
        
        return AIResponse(
            content=response.text,
            provider=self.provider.value,
            model="gemini-1.5-pro",
            raw_response=response
        )
    
    def _analyze_image_openai(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str
    ) -> AIResponse:
        """Analyze image using OpenAI GPT-4 Vision"""
        import base64
        
        client = self._get_openai_client()
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        return AIResponse(
            content=response.choices[0].message.content,
            provider=self.provider.value,
            model="gpt-4o",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            raw_response=response
        )


# Convenience functions
def get_ai_service(provider: str = "openai", model: Optional[str] = None) -> AIService:
    """
    Get an AI service instance.
    
    Args:
        provider: "openai", "gemini", or "deepseek"
        model: Optional specific model name
        
    Returns:
        AIService instance
    """
    provider_enum = AIProvider(provider.lower())
    return AIService(provider=provider_enum, model=model)


def quick_chat(message: str, provider: str = "openai") -> str:
    """
    Quick chat function for simple use cases.
    
    Args:
        message: User message
        provider: AI provider name
        
    Returns:
        AI response content as string
    """
    ai = get_ai_service(provider)
    return ai.chat(message).content
