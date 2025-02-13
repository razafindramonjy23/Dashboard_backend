from rest_framework import serializers
from ..models.database import ExpertSenderDatabase

class ExpertSenderDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSenderDatabase
        fields = ['id', 'name', 'description', 'api_url', 'is_active', 
                 'last_sync', 'created_at', 'updated_at']
        read_only_fields = ['last_sync', 'created_at', 'updated_at']

class ExpertSenderDatabaseDetailSerializer(serializers.ModelSerializer):
    total_sent = serializers.IntegerField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    geo_variations = serializers.SerializerMethodField()
    is_multi_geo = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpertSenderDatabase
        fields = ['id', 'name', 'description', 'api_url', 'is_active',
                 'last_sync', 'total_sent', 'total_revenue', 'geo_variations', 'is_multi_geo']

    def get_geo_variations(self, obj):
        return obj.get_geo_variations()

    def get_is_multi_geo(self, obj):
        return obj.is_multi_geo()