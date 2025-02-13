from django.core.management.base import BaseCommand
from api.models.metrics import CampaignMetrics
import re
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Met à jour les géolocalisations pour toutes les métriques existantes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les changements sans les appliquer'
        )

    def extract_country_codes(self, database_name):
        matches = re.findall(r'\[([A-Za-z]{2,4}(?:\s?[A-Za-z]{2,4})*)\]', database_name)
        return ','.join(matches) if matches else ''

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        metrics_count = 0
        updated_count = 0

        self.stdout.write('Début de la mise à jour des géolocalisations...')

        try:
            # Récupère toutes les métriques par lots pour optimiser la mémoire
            for metric in CampaignMetrics.objects.select_related('database').iterator():
                metrics_count += 1
                
                if metric.database:
                    new_geo_location = self.extract_country_codes(metric.database.name)
                    
                    if new_geo_location != metric.geo_location:
                        if dry_run:
                            self.stdout.write(f'[DRY RUN] Mise à jour de la métrique {metric.id}: {metric.geo_location} -> {new_geo_location}')
                        else:
                            old_geo = metric.geo_location
                            metric.geo_location = new_geo_location
                            metric.save(update_fields=['geo_location'])
                            updated_count += 1
                            logger.info(f'Métrique {metric.id} mise à jour: {old_geo} -> {new_geo_location}')

                if metrics_count % 1000 == 0:  # Log progression tous les 1000 enregistrements
                    self.stdout.write(f'Traitement en cours... {metrics_count} métriques traitées')

            status = '[DRY RUN] ' if dry_run else ''
            self.stdout.write(
                self.style.SUCCESS(
                    f'{status}Mise à jour terminée. '
                    f'{updated_count}/{metrics_count} métriques mises à jour.'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la mise à jour: {str(e)}')
            )
            logger.error(f'Erreur lors de la mise à jour des géolocalisations: {str(e)}', exc_info=True)