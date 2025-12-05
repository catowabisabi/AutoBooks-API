from rest_framework import serializers


class AnalystQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
