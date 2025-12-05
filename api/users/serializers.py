from rest_framework import serializers
from .models import User


# serializers.py - Keep only these
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'is_active']
        read_only_fields = ['id', 'email']


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """For admin to create users"""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user
