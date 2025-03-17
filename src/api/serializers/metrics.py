from rest_framework import serializers
from ..models.metrics import CampaignMetrics

class CampaignMetricsSerializer(serializers.ModelSerializer):
    base = serializers.CharField(source='database.name', read_only=True)
    domain_family_display = serializers.CharField( read_only=True)
    class Meta:
        model = CampaignMetrics
        fields = '__all__'