# api/views/metrics.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, F, Case, When, CharField, Value, FloatField
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from rest_framework.pagination import PageNumberPagination
from ..models.metrics import CampaignMetrics
from ..serializers.metrics import CampaignMetricsSerializer
from datetime import datetime

from django.db.models import Min, Max, Count
from django.db.models.functions import TruncYear


def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()


class CustomPagination(PageNumberPagination):
    """
    Pagination personnalisée pour limiter les résultats retournés.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CampaignMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Fournit des endpoints pour accéder et analyser les données de campagne.
    """

    queryset = CampaignMetrics.objects.select_related('database').all()
    serializer_class = CampaignMetricsSerializer
    pagination_class = CustomPagination

    filterset_fields = {
        'date': ['gte', 'lte', 'exact', 'year', 'month'],
        'database': ['exact'],
        'domain_family': ['exact'],
        'geo_location': ['exact'],
        'geo_variation': ['exact', 'isnull'],
    }

    metrics_mapping = {
        'sent': Sum('sent'),
        'clicks': Sum('clicks'),
        'opens': Sum('opens'),
        'delivered': Sum('delivered'),
        'bounced': Sum('bounced'),
        'revenue': Sum('revenue'),
        'unique_opens': Sum('unique_opens'),
        'clickers': Sum('clickers'),
        'complaints': Sum('complaints'),
        'unsubscribes': Sum('unsubscribes'),
        'goals': Sum('goals'),
        'goals_value': Sum('goals_value'),
        'open_rate': Case(
            When(delivered__gt=0, then=(Sum('opens') * 100.0 / Sum('delivered'))),
            default=Value(0.0),
            output_field=FloatField()
        ),
        'click_rate': Case(
            When(opens__gt=0, then=(Sum('clicks') * 100.0 / Sum('opens'))),
            default=Value(0.0),
            output_field=FloatField()
        ),
        'delivery_rate': Case(
            When(sent__gt=0, then=(Sum('delivered') * 100.0 / Sum('sent'))),
            default=Value(0.0),
            output_field=FloatField()
        )
    }

    def _handle_pagination(self, queryset):
        """
        Gère la pagination de manière uniforme pour toutes les actions du ViewSet.
        """
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(queryset)

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.annotate(
            domain_family_display=Case(
                When(domain_family='', then=Value('Unknown')),
                When(domain_family__isnull=True, then=Value('Unknown')),
                default=F('domain_family'),
                output_field=CharField()
            )
        )

        geo = self.request.query_params.get('geo_location')

        if geo:
            queryset = queryset.filter(geo_location__icontains=geo)
        return queryset

    @action(detail=False)
    def summary_by_database(self, request):
        """
        Récupère un résumé des métriques agrégées par base de données.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())

            summary = queryset.values('database__name', 'geo_variation').annotate(
                total_sent=Sum('sent'),
                total_delivered=Sum('delivered'),
                total_opens=Sum('opens'),
                total_clicks=Sum('clicks'),
                total_revenue=Sum('revenue'),
                total_bounced=Sum('bounced'),
                delivery_rate=Case(
                    When(sent__gt=0, then=(Sum('delivered') * 100.0 / Sum('sent'))),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                open_rate=Case(
                    When(delivered__gt=0, then=(Sum('opens') * 100.0 / Sum('delivered'))),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                click_rate=Case(
                    When(opens__gt=0, then=(Sum('clicks') * 100.0 / Sum('opens'))),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).order_by('-total_revenue')

            return self._handle_pagination(summary)

        except Exception as e:
            return Response(
                {'error': 'Failed to calculate summary.', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False)
    def summary_by_date(self, request):
        """
        Récupère un résumé des métriques agrégées par date.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            interval = request.query_params.get('interval', 'day')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            if start_date and end_date:
                try:
                    start_date = parse_date(start_date)
                    end_date = parse_date(end_date)
                    queryset = queryset.filter(date__range=[start_date, end_date])
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if interval not in ['day', 'month']:
                return Response(
                    {'error': "Invalid interval. Use 'day' or 'month'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            date_trunc = TruncMonth('date') if interval == 'month' else TruncDate('date')

            summary = queryset.annotate(
                period=date_trunc
            ).values('period').annotate(
                total_sent=Sum('sent'),
                total_revenue=Sum('revenue'),
                total_delivered=Sum('delivered'),
                total_opens=Sum('opens'),
                open_rate=Case(
                    When(delivered__gt=0, then=(Sum('opens') * 100.0 / Sum('delivered'))),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                delivery_rate=Case(
                    When(sent__gt=0, then=(Sum('delivered') * 100.0 / Sum('sent'))),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).order_by('period')

            return self._handle_pagination(summary)

        except Exception as e:
            return Response(
                {'error': 'Summary by date calculation failed.', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False)
    def summary_by_domain(self, request):
        """
        Récupère un résumé des métriques agrégées par domaine.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())

            summary = queryset.values(
                'domain_family_display'
            ).annotate(
                geo_location=F('geo_location'),
                total_sent=Sum('sent'),
                total_delivered=Sum('delivered'),
                total_opens=Sum('opens'),
                total_clicks=Sum('clicks'),
                delivery_rate=Case(
                    When(sent__gt=0, then=Sum('delivered') * 100.0 / Sum('sent')),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                open_rate=Case(
                    When(delivered__gt=0, then=Sum('opens') * 100.0 / Sum('delivered')),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                click_rate=Case(
                    When(opens__gt=0, then=Sum('clicks') * 100.0 / Sum('opens')),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).order_by('-total_sent')

            return self._handle_pagination(summary)

        except Exception as e:
            return Response(
                {'error': 'Failed to calculate summary by domain.', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """
        Récupère un résumé global des métriques.
        """
        try:
            metrics = self.filter_queryset(self.get_queryset())

            summary = {
                'total_sent': metrics.aggregate(total=Sum('sent'))['total'] or 0,
                'total_bounced': metrics.aggregate(total=Sum('bounced'))['total'] or 0,
                'total_delivered': metrics.aggregate(total=Sum('delivered'))['total'] or 0,
                'total_opens': metrics.aggregate(total=Sum('opens'))['total'] or 0,
                'total_clicks': metrics.aggregate(total=Sum('clicks'))['total'] or 0,
                'total_revenue': metrics.aggregate(total=Sum('revenue'))['total'] or 0,
                'average_open_rate': metrics.aggregate(
                    rate=Case(
                        When(delivered__gt=0, then=Avg('opens') * 100.0 / Avg('delivered')),
                        default=Value(0.0),
                        output_field=FloatField()
                    )
                )['rate'] or 0,
                'average_click_rate': metrics.aggregate(
                    rate=Case(
                        When(opens__gt=0, then=Avg('clicks') * 100.0 / Avg('opens')),
                        default=Value(0.0),
                        output_field=FloatField()
                    )
                )['rate'] or 0
            }

            return self._handle_pagination([summary])

        except Exception as e:
            return Response(
                {'error': 'Failed to calculate summary.', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def pivot_table(self, request):
        """
        Endpoint flexible pour créer des tableaux croisés dynamiques.
        Permet de grouper, agréger et trier les données selon les paramètres de la requête.
        """
        try:
            group_by = request.query_params.getlist('group_by') or ['domain_family_display']
            metrics = request.query_params.getlist('metrics') or ['sent', 'revenue', 'opens']
            order_by = request.query_params.get('order_by', None)
            queryset = self.filter_queryset(self.get_queryset())

            aggregation = {}
            for metric in metrics:
                if metric in self.metrics_mapping:
                    aggregation[f'total_{metric}'] = self.metrics_mapping[metric]
                else:
                    return Response(
                        {"error": f"Invalid metric: {metric}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            result = queryset.values(*group_by).annotate(**aggregation)

            # Trier les résultats
            if order_by:
                if order_by.startswith('-'):
                    order_by_field = order_by[1:]
                    if f'total_{order_by_field}' in aggregation:
                        result = result.order_by(order_by)
                    else:
                        return Response(
                            {"error": f"Cannot sort by {order_by_field}.  It's not a valid metric."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    if f'total_{order_by}' in aggregation:
                        result = result.order_by(order_by)
                    else:
                        return Response(
                            {"error": f"Cannot sort by {order_by}. It's not a valid metric."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                result = result.order_by(*group_by)

            return self._handle_pagination(result)

        except Exception as e:
            return Response(
                {"error": f"Pivot table error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
