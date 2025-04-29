from django.core.management.base import BaseCommand
from django.core.management import call_command
import schedule
import time
import logging

from api.tasks.sync import sync_database_metrics
from api.models.database import ExpertSenderDatabase

logger = logging.getLogger(__name__)

def job_sync_and_geo(db_id):
    """
    Lance la synchro ExpertSender pour la base db_id
    puis met à jour la géolocalisation de toutes les métriques.
    """
    try:
        logger.info(f"[SYNC] Début de la synchro pour DB #{db_id}")
        sync_database_metrics(database_id=db_id)
        logger.info(f"[SYNC] Fin de la synchro pour DB #{db_id}")
    except Exception as e:
        logger.exception(f"[SYNC] Erreur lors de la synchro pour DB #{db_id}: {e}")

    try:
        logger.info("[GEO] Début de la mise à jour géolocalisation")
        # Appel du management command 'update_geolocations'
        call_command('update_geolocations', verbosity=0)
        logger.info("[GEO] Fin de la mise à jour géolocalisation")
    except Exception as e:
        logger.exception(f"[GEO] Erreur lors de la mise à jour géolocalisation: {e}")


class Command(BaseCommand):
    help = 'Démarre le planificateur de tâches ExpertSender + géolocalisation'

    def handle(self, *args, **kwargs):
        logger.info("🔄 Démarrage du planificateur de tâches...")

        # Récupère les bases actives
        databases = ExpertSenderDatabase.objects.filter(is_active=True)
        if not databases:
            logger.warning("⚠️  Aucune base active trouvée. Le scheduler s'arrêtera.")
            return

        # Planifie un job par base active
        for db in databases:
            logger.info(f"✅ Planification pour DB #{db.id} toutes les heures")
            # Utiliser lambda pour capturer correctement db.id
            schedule.every(1).hours.do(job_sync_and_geo, db_id=db.id)

        logger.info("⏱ Scheduler prêt. Les tâches s'exécuteront toutes les heures.")

        try:
            while True:
                schedule.run_pending()
                # On logge seulement toutes les 5 minutes pour réduire le bruit
                time.sleep(300)
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du planificateur suite à une interruption clavier.")
