from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User
from .serializers import AdminCreateUserSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer  # Admin can create users and set roles
        return UserSerializer

    def get_permissions(self):
        """Only admins can create, update, delete users"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Return current authenticated user's information"""
        serializer = self.get_serializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        })


# Custom permission class
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Custom permission to only allow admin users"""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'ADMIN'
        )
