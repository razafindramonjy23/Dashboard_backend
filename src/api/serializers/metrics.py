from rest_framework import serializers
from ..models.metrics import CampaignMetrics

class CampaignMetricsSerializer(serializers.ModelSerializer):
    database = serializers.CharField(source='database.name', read_only=True)
    domain_family_display = serializers.CharField( read_only=True)
    class Meta:
        model = CampaignMetrics
        fields = '__all__'
        
    # def get_database(self, obj) : 
    #     if obj.database: 
    #         return obj.database.name
    #     return None