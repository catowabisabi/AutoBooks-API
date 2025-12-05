from rest_framework import serializers


class PlannerQuerySerializer(serializers.Serializer):
    query = serializers.CharField()