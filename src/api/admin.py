from django.contrib import admin
from .models.database import ExpertSenderDatabase
from .models.metrics import CampaignMetrics

@admin.register(ExpertSenderDatabase)
class ExpertSenderDatabaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'last_sync', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_sync')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_url')
        }),
        ('Timestamps', {
            'fields': ('last_sync', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CampaignMetrics)
class CampaignMetricsAdmin(admin.ModelAdmin):
    list_display = ('database', 'date', 'domain_family', 'geo_location', 'sent', 'delivered', 'opens', 'clicks', 'bounced')
    list_filter = ('date', 'database', 'domain_family', 'geo_location')
    date_hierarchy = 'date'
    search_fields = ('database__name', 'domain_family', 'geo_location')
    readonly_fields = ('database', 'date')