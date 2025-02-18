from django.contrib import admin
from django.db.models import Sum, Case, When, Value, F
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
    list_display = ('database', 'date', 'domain_family', 'geo_location', 
                    'sent', 'delivered', 'opens', 'clicks', 
                    'bounced', 'display_open_rate', 
                    'display_click_rate')
    list_filter = ('date', 'database', 'domain_family', 'geo_location')
    date_hierarchy = 'date'
    search_fields = ('database__name', 'domain_family', 'geo_location')
    readonly_fields = ('database', 'date')

    actions = ['calculate_selected_metrics']

    def display_open_rate(self, obj):
        return f'{obj.open_rate():.2f}%'
    display_open_rate.short_description = 'Open Rate'
    display_open_rate.admin_order_field = '_open_rate'  # Permet le tri

    def display_click_rate(self, obj):
        return f'{obj.click_rate():.2f}%'
    display_click_rate.short_description = 'Click Rate'
    display_click_rate.admin_order_field = '_click_rate'  # Permet le tri

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Pré-calcule les taux d'ouverture et de clics pour éviter des requêtes supplémentaires
        return qs.annotate(
            _open_rate=Case(
                When(delivered__gt=0, then=(F('opens') * 100.0) / F('delivered')),
                default=Value(0.0)
            ),
            _click_rate=Case(
                When(opens__gt=0, then=(F('clicks') * 100.0) / F('opens')),
                default=Value(0.0)
            )
        )

    def calculate_selected_metrics(self, request, queryset):
        """Action personnalisée pour calculer des métriques agrégées sur les enregistrements sélectionnés."""
        selected_count = queryset.count()
        total_sent = queryset.aggregate(total_sent=Sum('sent'))['total_sent'] or 0
        total_delivered = queryset.aggregate(total_delivered=Sum('delivered'))['total_delivered'] or 0
        total_opens = queryset.aggregate(total_opens=Sum('opens'))['total_opens'] or 0
        total_clicks = queryset.aggregate(total_clicks=Sum('clicks'))['total_clicks'] or 0
        total_bounced = queryset.aggregate(total_bounced=Sum('bounced'))['total_bounced'] or 0
        total_revenue = queryset.aggregate(total_revenue=Sum('revenue'))['total_revenue'] or 0

        message = (
            f"Résumé des métriques pour {selected_count} enregistrements sélectionnés:\n"
            f"Total Envoyé: {total_sent}\n"
            f"Total Livré: {total_delivered}\n"
            f"Total Ouvertures: {total_opens}\n"
            f"Total Clics: {total_clicks}\n"
            f"Total Rejetés: {total_bounced}\n"
            f"Total Revenu: {total_revenue}"
        )
        self.message_user(request, message, level='INFO')
    
    calculate_selected_metrics.short_description = "Calculer les métriques sélectionnées"
