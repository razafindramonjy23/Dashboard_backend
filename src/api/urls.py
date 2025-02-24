from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.database import ExpertSenderDatabaseViewSet
from .views.metrics import CampaignMetricsViewSet

router = DefaultRouter()
router.register(r'databases', ExpertSenderDatabaseViewSet)
router.register(r'metrics', CampaignMetricsViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('metrics/filter_options/', CampaignMetricsViewSet.filter_options, name='filter_options'),
]