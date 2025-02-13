from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from ..models.database import ExpertSenderDatabase
from ..serializers.database import ExpertSenderDatabaseSerializer, ExpertSenderDatabaseDetailSerializer
from ..tasks.sync import sync_database_metrics  # Assurez-vous que sync.py est importé correctement

class ExpertSenderDatabaseViewSet(viewsets.ModelViewSet):
    queryset = ExpertSenderDatabase.objects.all()
    serializer_class = ExpertSenderDatabaseSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExpertSenderDatabaseDetailSerializer
        return ExpertSenderDatabaseSerializer

    @action(detail=True, methods=['POST'])
    def sync(self, request, pk=None):
        try:
            database = self.get_object()
            
            # Exécute directement la fonction de synchronisation
            result = sync_database_metrics(database.id)
            
            return Response({
                'status': 'Synchronisation terminée',
                'result': result
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Capture et retourne toute erreur rencontrée
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def sync_all(self, request):
        try:
            # Filtre les bases actives et lance la synchronisation pour chacune
            databases = ExpertSenderDatabase.objects.filter(is_active=True)
            results = []
            
            for db in databases:
                result = sync_database_metrics(db.id)
                results.append({
                    'database_id': db.id,
                    'result': result
                })
            
            return Response({
                'status': f'Synchronisation terminée pour {len(results)} bases',
                'results': results
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Capture et retourne toute erreur rencontrée
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
