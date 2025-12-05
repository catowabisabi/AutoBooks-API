"""
API Key management views for AI services.
Securely stores and manages API keys for OpenAI, Gemini, and DeepSeek.
"""
import os
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import openai


class ApiKeyStatusView(APIView):
    """Get the status of configured API keys"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return which API keys are configured"""
        return Response({
            'openai': bool(os.environ.get('OPENAI_API_KEY')),
            'gemini': bool(os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')),
            'deepseek': bool(os.environ.get('DEEPSEEK_API_KEY')),
        })


class ApiKeyManageView(APIView):
    """Save or delete API keys"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, provider):
        """Save an API key for a provider"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can manage API keys'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        api_key = request.data.get('api_key')
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Map provider to environment variable
        env_var_map = {
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GOOGLE_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }
        
        env_var = env_var_map.get(provider)
        if not env_var:
            return Response(
                {'error': f'Unknown provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set environment variable (runtime only)
        os.environ[env_var] = api_key
        
        # Optionally persist to .env file
        self._update_env_file(env_var, api_key)
        
        return Response({
            'success': True,
            'message': f'{provider} API key saved successfully'
        })
    
    def delete(self, request, provider):
        """Delete an API key for a provider"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can manage API keys'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        env_var_map = {
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GOOGLE_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }
        
        env_var = env_var_map.get(provider)
        if not env_var:
            return Response(
                {'error': f'Unknown provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove from environment
        if env_var in os.environ:
            del os.environ[env_var]
        
        # Remove from .env file
        self._remove_from_env_file(env_var)
        
        return Response({
            'success': True,
            'message': f'{provider} API key deleted successfully'
        })
    
    def _update_env_file(self, env_var, value):
        """Update the .env file with new value"""
        try:
            env_path = os.path.join(settings.BASE_DIR, '.env')
            lines = []
            found = False
            
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            # Update or add the variable
            new_lines = []
            for line in lines:
                if line.strip().startswith(f'{env_var}='):
                    new_lines.append(f'{env_var}={value}\n')
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(f'{env_var}={value}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
                
        except Exception as e:
            # Log error but don't fail - runtime variable is already set
            print(f'Warning: Could not update .env file: {e}')
    
    def _remove_from_env_file(self, env_var):
        """Remove a variable from the .env file"""
        try:
            env_path = os.path.join(settings.BASE_DIR, '.env')
            
            if not os.path.exists(env_path):
                return
            
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            new_lines = [line for line in lines if not line.strip().startswith(f'{env_var}=')]
            
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
                
        except Exception as e:
            print(f'Warning: Could not update .env file: {e}')


class ApiKeyTestView(APIView):
    """Test if an API key is valid"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, provider):
        """Test an API key by making a simple API call"""
        if provider == 'openai':
            return self._test_openai()
        elif provider == 'gemini':
            return self._test_gemini()
        elif provider == 'deepseek':
            return self._test_deepseek()
        else:
            return Response(
                {'error': f'Unknown provider: {provider}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _test_openai(self):
        """Test OpenAI API key"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return Response({'valid': False, 'error': 'API key not configured'})
        
        try:
            client = openai.OpenAI(api_key=api_key)
            # Simple models list call to verify key
            models = client.models.list()
            return Response({'valid': True})
        except openai.AuthenticationError:
            return Response({'valid': False, 'error': 'Invalid API key'})
        except Exception as e:
            return Response({'valid': False, 'error': str(e)})
    
    def _test_gemini(self):
        """Test Google Gemini API key"""
        api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return Response({'valid': False, 'error': 'API key not configured'})
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # List models to verify key
            models = list(genai.list_models())
            return Response({'valid': True})
        except Exception as e:
            return Response({'valid': False, 'error': str(e)})
    
    def _test_deepseek(self):
        """Test DeepSeek API key"""
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            return Response({'valid': False, 'error': 'API key not configured'})
        
        try:
            # DeepSeek uses OpenAI-compatible API
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            # Try a simple call
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return Response({'valid': True})
        except Exception as e:
            return Response({'valid': False, 'error': str(e)})
