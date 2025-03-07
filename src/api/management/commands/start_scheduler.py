from django.core.management.base import BaseCommand
import schedule
import time
import logging
from api.tasks.sync import sync_database_metrics
from api.models.database import ExpertSenderDatabase

# Configuration du logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Démarre le planificateur de tâches'

    def handle(self, *args, **kwargs):
        logger.info("Démarrage du planificateur de tâches...")
        databases = ExpertSenderDatabase.objects.filter(is_active=True)

        if not databases:
            logger.warning("Aucune base de données active trouvée.")
        
        # Planifier la synchronisation pour chaque base de données active
        for db in databases:
            logger.info(f"Planification de la synchronisation pour la base de données {db.id}.")
            schedule.every(1).hours.do(sync_database_metrics, database_id=db.id)

        logger.info("Planificateur prêt. En attente des tâches à exécuter.")

        # Exécuter le planificateur en boucle
        while True:
            schedule.run_pending()
        
            logging.info("En attente de tâches...")
            time.sleep(1)
            logging.info("Tache termine")
