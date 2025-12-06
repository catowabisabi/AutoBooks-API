"""
Google OAuth 2.0 Authentication Views
"""
import os
import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User


class GoogleOAuthURLView(APIView):
    """Generate Google OAuth URL for frontend"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
        
        if not client_id:
            return Response(
                {'error': 'Google OAuth not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Google OAuth URL
        oauth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=email%20profile&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        
        return Response({'url': oauth_url})


class GoogleOAuthCallbackView(APIView):
    """Handle Google OAuth callback"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        
        if error:
            # Redirect to frontend with error
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f"{frontend_url}/auth/sign-in?error={error}")
        
        if not code:
            return Response(
                {'error': 'No authorization code provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Exchange code for tokens
            token_data = self._exchange_code_for_tokens(code)
            
            # Get user info from Google
            user_info = self._get_google_user_info(token_data['access_token'])
            
            # Create or get user
            user = self._get_or_create_user(user_info)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Redirect to frontend with tokens
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            redirect_url = (
                f"{frontend_url}/auth/callback?"
                f"access={str(refresh.access_token)}&"
                f"refresh={str(refresh)}"
            )
            
            return redirect(redirect_url)
            
        except Exception as e:
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f"{frontend_url}/auth/sign-in?error={str(e)}")
    
    def post(self, request):
        """Handle POST request from frontend with authorization code"""
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'No authorization code provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get redirect URI from request origin (to match what frontend used)
            origin = request.headers.get('Origin', request.headers.get('Referer', ''))
            if origin:
                # Remove any trailing slash and path from origin
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                redirect_uri = f"{parsed.scheme}://{parsed.netloc}/auth/google/callback"
            else:
                redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
            
            # Exchange code for tokens
            token_data = self._exchange_code_for_tokens(code, redirect_uri)
            
            # Get user info from Google
            user_info = self._get_google_user_info(token_data['access_token'])
            
            # Create or get user
            user = self._get_or_create_user(user_info)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                }
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _exchange_code_for_tokens(self, code, redirect_uri=None):
        """Exchange authorization code for tokens"""
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            raise Exception('Failed to exchange code for tokens')
        
        return response.json()
    
    def _get_google_user_info(self, access_token):
        """Get user info from Google"""
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(user_info_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception('Failed to get user info from Google')
        
        return response.json()
    
    def _get_or_create_user(self, user_info):
        """Get or create user from Google user info"""
        email = user_info.get('email')
        
        if not email:
            raise Exception('Email not provided by Google')
        
        try:
            user = User.objects.get(email=email)
            # Update user info if needed
            if not user.full_name and user_info.get('name'):
                user.full_name = user_info['name']
                user.save()
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create(
                email=email,
                full_name=user_info.get('name', ''),
                is_active=True
            )
            # Set unusable password (user logs in via Google)
            user.set_unusable_password()
            user.save()
        
        return user


class GoogleOAuthTokenView(APIView):
    """Exchange Google OAuth tokens for JWT (for frontend-based OAuth)"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Frontend sends Google access token, we verify and return JWT
        """
        google_token = request.data.get('token')
        
        if not google_token:
            return Response(
                {'error': 'Google token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify token with Google
            user_info = self._verify_google_token(google_token)
            
            # Get or create user
            user = self._get_or_create_user(user_info)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role
                }
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _verify_google_token(self, token):
        """Verify Google token and get user info"""
        # Option 1: Use tokeninfo endpoint
        verify_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
        response = requests.get(verify_url)
        
        if response.status_code == 200:
            return response.json()
        
        # Option 2: Use userinfo endpoint with access token
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(user_info_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception('Invalid Google token')
        
        return response.json()
    
    def _get_or_create_user(self, user_info):
        """Get or create user from Google user info"""
        email = user_info.get('email')
        
        if not email:
            raise Exception('Email not provided by Google')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(
                email=email,
                full_name=user_info.get('name', ''),
                is_active=True
            )
            user.set_unusable_password()
            user.save()
        
        return user
