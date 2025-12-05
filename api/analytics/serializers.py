"""
Analytics Module Serializers
============================
Serializers for Dashboards, Charts, Sales Analytics, and KPIs.
"""

from rest_framework import serializers
from .models import Dashboard, Chart, AnalyticsSales, KPIMetric, ReportSchedule


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = [
            'id', 'dashboard', 'title', 'type', 'config', 'data_source',
            'position', 'width', 'height', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChartListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = ['id', 'title', 'type', 'position']


class DashboardSerializer(serializers.ModelSerializer):
    charts = ChartSerializer(many=True, read_only=True)
    charts_count = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = [
            'id', 'title', 'description', 'is_default', 'layout',
            'charts', 'charts_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_charts_count(self, obj):
        return obj.charts.count()


class DashboardListSerializer(serializers.ModelSerializer):
    charts_count = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = ['id', 'title', 'is_default', 'charts_count', 'created_at']
    
    def get_charts_count(self, obj):
        return obj.charts.count()


class AnalyticsSalesSerializer(serializers.ModelSerializer):
    month_name = serializers.CharField(read_only=True)
    profit_margin = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    revenue_achievement = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = AnalyticsSales
        fields = [
            'id', 'year', 'month', 'month_name',
            'revenue', 'target_revenue', 'growth_percentage', 'yoy_growth',
            'new_clients', 'total_clients', 'churned_clients', 'churn_rate',
            'deals_closed', 'deals_pipeline', 'average_deal_value', 'conversion_rate',
            'operating_costs', 'marketing_spend',
            'profit_margin', 'revenue_achievement',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'month_name', 'profit_margin', 'revenue_achievement']


class AnalyticsSalesListSerializer(serializers.ModelSerializer):
    month_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = AnalyticsSales
        fields = [
            'id', 'year', 'month', 'month_name', 'revenue', 'growth_percentage',
            'new_clients', 'churn_rate'
        ]


class KPIMetricSerializer(serializers.ModelSerializer):
    achievement_percentage = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    change_percentage = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = KPIMetric
        fields = [
            'id', 'name', 'description', 'category',
            'current_value', 'target_value', 'previous_value',
            'unit', 'display_format', 'trend', 'is_positive_good',
            'achievement_percentage', 'change_percentage',
            'period', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'achievement_percentage', 'change_percentage']


class KPIMetricListSerializer(serializers.ModelSerializer):
    achievement_percentage = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = KPIMetric
        fields = [
            'id', 'name', 'category', 'current_value', 'target_value',
            'unit', 'trend', 'achievement_percentage'
        ]


class ReportScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'name', 'report_type', 'frequency', 'recipients',
            'is_active', 'last_run', 'next_run', 'config',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_run']

