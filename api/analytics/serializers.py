from rest_framework import serializers
from .models import Dashboard, Chart


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = '__all__'


class DashboardSerializer(serializers.ModelSerializer):
    charts = ChartSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = '__all__'
