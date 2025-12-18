"""
Google OAuth authentication views for Wisematic ERP.
Handles Google OAuth2 flow and JWT token generation.
"""
import os
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from core.schema_serializers import GoogleOAuthRequestSerializer

User = get_user_model()


class GoogleOAuthView(APIView):
    """
    Handle Google OAuth2 authentication.
    Accepts either:
    - 'code': Authorization code from OAuth flow (for web apps)
    - 'credential': ID token from Google Sign-In (for JavaScript SDK)
    """
    permission_classes = [AllowAny]
    serializer_class = GoogleOAuthRequestSerializer
    
    def post(self, request):
        code = request.data.get('code')
        credential = request.data.get('credential')
        
        if credential:
            # Handle ID token (from Google Sign-In JavaScript SDK)
            return self._handle_id_token(credential)
        elif code:
            # Handle authorization code (from OAuth redirect flow)
            return self._handle_auth_code(code, request)
        else:
            return Response(
                {'error': 'Either code or credential is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _handle_id_token(self, credential):
        """Verify Google ID token and authenticate user"""
        try:
            google_client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '') or getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
            
            if not google_client_id:
                return Response(
                    {'error': 'Google OAuth is not configured on the server'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                google_client_id
            )
            
            # Extract user info
            email = idinfo.get('email')
            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': f"{idinfo.get('given_name', '')} {idinfo.get('family_name', '')}".strip() or email.split('@')[0],
                    'is_active': True,
                }
            )
            
            # Update user info if exists
            if not created:
                if not user.full_name and (idinfo.get('given_name') or idinfo.get('family_name')):
                    user.full_name = f"{idinfo.get('given_name', '')} {idinfo.get('family_name', '')}".strip()
                user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                }
            })
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid Google token: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _handle_auth_code(self, code, request):
        """Exchange authorization code for tokens and authenticate user"""
        try:
            google_client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '') or getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
            google_client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '') or getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
            
            if not google_client_id or not google_client_secret:
                return Response(
                    {'error': 'Google OAuth is not configured on the server'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get redirect URI from request origin
            origin = request.headers.get('Origin', request.headers.get('Referer', ''))
            if origin:
                redirect_uri = f"{origin.rstrip('/')}/auth/google/callback"
            else:
                redirect_uri = os.environ.get('GOOGLE_OAUTH_REDIRECT_URI', '') or os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/google/callback')
            
            # Exchange code for tokens
            token_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'code': code,
                    'client_id': google_client_id,
                    'client_secret': google_client_secret,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                }
            )
            
            if not token_response.ok:
                return Response(
                    {'error': 'Failed to exchange code for tokens'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tokens = token_response.json()
            access_token = tokens.get('access_token')
            
            # Get user info
            userinfo_response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if not userinfo_response.ok:
                return Response(
                    {'error': 'Failed to get user info from Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            userinfo = userinfo_response.json()
            email = userinfo.get('email')
            
            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': f"{userinfo.get('given_name', '')} {userinfo.get('family_name', '')}".strip() or email.split('@')[0],
                    'is_active': True,
                }
            )
            
            # Update user info if exists
            if not created:
                if not user.full_name and (userinfo.get('given_name') or userinfo.get('family_name')):
                    user.full_name = f"{userinfo.get('given_name', '')} {userinfo.get('family_name', '')}".strip()
                user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Google OAuth error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleOAuthCallbackView(APIView):
    """
    Handle Google OAuth2 callback (for redirect-based flow).
    This is called when Google redirects back with the authorization code.
    Supports both GET (browser redirect) and POST (AJAX) methods.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        
        if error:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not code:
            return Response(
                {'error': 'Authorization code not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the code using the main OAuth view
        oauth_view = GoogleOAuthView()
        oauth_view.request = request
        return oauth_view._handle_auth_code(code, request)
    
    def post(self, request):
        """Handle POST request from frontend AJAX call"""
        code = request.data.get('code')
        error = request.data.get('error')
        
        if error:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not code:
            return Response(
                {'error': 'Authorization code not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the code using the main OAuth view
        oauth_view = GoogleOAuthView()
        oauth_view.request = request
        return oauth_view._handle_auth_code(code, request)
