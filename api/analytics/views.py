from rest_framework import viewsets, status
from .models import Dashboard, Chart
from .serializers import DashboardSerializer, ChartSerializer


class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer


class ChartViewSet(viewsets.ModelViewSet):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer
