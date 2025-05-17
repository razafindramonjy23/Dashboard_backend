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

import requests
from django.conf import settings




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
        'database__name': ['exact'],
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
                geo_location=F('geo_location'),
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

            total_sent = metrics.aggregate(total=Sum('sent'))['total'] or 0
            total_bounced = metrics.aggregate(total=Sum('bounced'))['total'] or 0
            total_delivered = metrics.aggregate(total=Sum('delivered'))['total'] or 0
            total_opens = metrics.aggregate(total=Sum('opens'))['total'] or 0
            total_clicks = metrics.aggregate(total=Sum('clicks'))['total'] or 0
            total_revenue = metrics.aggregate(total=Sum('revenue'))['total'] or 0

            average_open_rate = 0
            if total_delivered > 0:
                average_open_rate = metrics.aggregate(
                    rate=Avg('opens') * 100.0 / Avg('delivered')
                )['rate'] or 0

            average_click_rate = 0
            if total_opens > 0:
                average_click_rate = metrics.aggregate(
                    rate=Avg('clicks') * 100.0 / Avg('opens')
                )['rate'] or 0

            summary = {
                'total_sent': total_sent,
                'total_bounced': total_bounced,
                'total_delivered': total_delivered,
                'total_opens': total_opens,
                'total_clicks': total_clicks,
                'total_revenue': total_revenue,
                'average_open_rate': average_open_rate,
                'average_click_rate': average_click_rate
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

    @action(detail=False, methods=['GET'])
    def filter_options(self, request):
        """
            Récupère les options de filtre pour les métriques.
        """
        try: 
            data = {
                "databases": CampaignMetrics.objects.values_list("database__name", flat=True).distinct(),
                "domain_families": CampaignMetrics.objects.values_list("domain_family", flat=True).distinct(),
                "geo_locations": CampaignMetrics.objects.values_list("geo_location", flat=True).distinct(),
                "geo_variations": CampaignMetrics.objects.values_list("geo_variation", flat=True).distinct(),
            }
            return Response(data)
        except Exception as e: 
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @action(detail=False, methods=['GET'])
    def grouping_options(self, request):
        """
            Récupère les options de groupement pour les métriques.
        """
        groupings = [
            {"value": "database__name", "label": "Database"},
            {"value": "domain_family_display", "label": "Domain Family"},
            {"value": "geo_location", "label": "Geo Location"},
            {"value": "geo_variation", "label": "Geo Variation"},
            {"value": "date", "label": "Date"},
        ]
        return Response(groupings)
    
    
    
    @action(detail=False, methods=["POST"])
    def gemini_predictive_insight(self, request):
        """
        Appelle l'API Gemini pour générer un classement prédictif basé sur les données envoyées.
        Analyse toutes les bases de données fournies pour une prédiction complète.
        """
        try:
            data = request.data.get('metrics')
            if not data:
                return Response({"error": "No metrics data provided"}, status=400)

            api_key = settings.GEMINI_API_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

            # Calcul des taux moyens globaux pour normalisation
            total_sent = sum(item.get("sent", 0) for item in data)
            total_opens = sum(item.get("opens", 0) for item in data)
            total_clicks = sum(item.get("clicks", 0) for item in data)
            avg_click_rate = round((total_clicks / total_opens) * 100, 2) if total_opens > 0 else 0

            all_data = []
            for item in data:
                database = item.get("database", "N/A")
                sent = item.get("sent", 0)
                delivered = item.get("delivered", 0)
                opens = item.get("opens", 0)
                clicks = item.get("clicks", 0)
                bounced = item.get("bounced", 0)

                open_rate = round((opens / delivered) * 100, 2) if delivered > 0 else 0
                click_rate = round((clicks / opens) * 100, 2) if opens > 0 else 0
                bounce_rate = round((bounced / sent) * 100, 2) if sent > 0 else 0

                engagement_ratio = clicks / opens if opens > 0 else 0
                delivery_quality = delivered / sent if sent > 0 else 0
                growth_potential = (click_rate / avg_click_rate) if avg_click_rate > 0 else 0

                potential_score = (
                    (engagement_ratio * 0.5) +
                    (delivery_quality * 0.3) +
                    (growth_potential * 0.2)
                ) * 100

                all_data.append({
                    "database": database,
                    "sent": sent,
                    "delivered": delivered,
                    "opens": opens,
                    "clicks": clicks,
                    "bounced": bounced,
                    "open_rate": open_rate,
                    "click_rate": click_rate,
                    "bounce_rate": bounce_rate,
                    "potential_score": round(potential_score, 2)
                })

            all_data.sort(key=lambda x: (x["open_rate"], x["click_rate"]), reverse=True)
            potential_data = sorted(all_data, key=lambda x: x["potential_score"], reverse=True)
            top_10_potential = potential_data[:10]

            simplified_data = [{
                "database": item["database"],
                "metrics": {
                    "sent": item["sent"],
                    "delivered": item["delivered"],
                    "opens": item["opens"],
                    "clicks": item["clicks"],
                    "bounced": item["bounced"]
                },
                "rates": {
                    "open_rate": f"{item['open_rate']}%",
                    "click_rate": f"{item['click_rate']}%",
                    "bounce_rate": f"{item['bounce_rate']}%"
                },
                "potential_score": f"{item['potential_score']}%"
            } for item in all_data]

            top_potential_data = [{
                "database": item["database"],
                "potential_score": f"{item['potential_score']}%",
                "open_rate": f"{item['open_rate']}%",
                "click_rate": f"{item['click_rate']}%"
            } for item in top_10_potential]

            total_delivered = sum(item["delivered"] for item in all_data)
            total_bounced = sum(item["bounced"] for item in all_data)
            summary_stats = {
                "nombre_total_bases": len(all_data),
                "moyenne_taux_ouverture": round((total_opens / total_delivered) * 100, 2) if total_delivered > 0 else 0,
                "moyenne_taux_clic": avg_click_rate,
                "moyenne_taux_rebond": round((total_bounced / total_sent) * 100, 2) if total_sent > 0 else 0
            }

            prompt = f"""
                Voici les données de performance email marketing pour {len(all_data)} bases de données :
                {simplified_data}

                Voici les 10 bases ayant le plus fort potentiel futur :
                {top_potential_data}

                Analyse toutes les bases de données (pas uniquement celles listées ci-dessus) et réponds EXCLUSIVEMENT sous ce format concis :

                1. TOP 3 BASES ACTUELLES (selon NOMBRE d'ouvertures et de clics uniquement, pas de taux) :
                Format exact : "NomBase = X ouvertures, Y clics"

                2. 3 BASES À FORT POTENTIEL (différentes des bases du TOP 3) :
                Format exact : "NomBase = Score potentiel X, croissance estimée Y"

                3. 2 BASES À AMÉLIORER (peu d’ouvertures/clics mais potentiel détecté) :
                Format exact : "NomBase = Performances actuelles X ouvertures/Y clics → Objectif X/Y"

                4. TENDANCES GLOBALES (sur les {len(all_data)} bases analysées) :
                Format : "Métrique: valeur" (ex. "Total clics: 10423")

                5. RECOMMANDATION : une seule phrase courte pour améliorer l'ensemble des performances

                IMPORTANT : 
                - Respecte STRICTEMENT ces formats, sans phrases supplémentaires.
                - Utilise UNIQUEMENT les NOMBRES d'ouvertures et de clics pour le classement, pas de taux ni de métriques envoyées/livrées.
                - Ne répète AUCUNE base entre les catégories.
                - L’analyse doit couvrir L’ENSEMBLE des bases disponibles, sans exception.
"""



            response = requests.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                return Response({"error": "Gemini API error", "details": response.text}, status=500)

            gemini_response = response.json()
            if "candidates" in gemini_response and gemini_response["candidates"]:
                content = gemini_response["candidates"][0]["content"]["parts"][0]["text"]
                result = {
                    "insight": content,
                    "top_potential_bases": [
                        {"database": item["database"], "potential_score": item["potential_score"]}
                        for item in top_10_potential
                    ],
                    "metadata": {
                        "analyzed_databases": len(all_data),
                        "global_stats": summary_stats,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                return Response(result)
            else:
                return Response({"error": "Invalid Gemini response format"}, status=500)

        except Exception as e:
            import traceback
            return Response({"error": str(e), "trace": traceback.format_exc()}, status=500)
