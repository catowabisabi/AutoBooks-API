from django.db import models
import uuid


class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Chart(models.Model):
    CHART_TYPES = (
        ('bar', 'Bar'),
        ('pie', 'Pie'),
        ('line', 'Line'),
        ('scatter', 'Scatter'),
        ('table', 'Table'),
        ('unsupported', 'Unsupported'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='charts')
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=CHART_TYPES)
    config = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"
