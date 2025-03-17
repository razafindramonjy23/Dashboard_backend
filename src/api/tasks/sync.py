import requests
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from ..models.database import ExpertSenderDatabase
from ..models.metrics import CampaignMetrics
import logging
import time
import schedule
import re

logger = logging.getLogger(__name__)


def extract_country_codes(database_name): 
    """
    Extrait les codes pays du nom de la base de données.
    Exemple: "Base [FR] [BE]" retourne "FR,BE"
    """
    matches = re.findall(r'\[([A-Z]{2})\]', database_name)
    return ','.join(matches) if matches else ''


def extract_geo_variations(database_name):
    """
    Vérifie si la base a plusieurs variations géographiques
    """
    variations = re.findall(r'\[([A-Z]{2})\]', database_name)
    return variations if len(variations) > 1 else None


class APIRateLimiter:
    def __init__(self, calls_per_second=2):
        self.calls_per_second = calls_per_second
        self.last_call = 0

    def wait(self):
        current_time = time.time()
        time_since_last_call = current_time - self.last_call
        if time_since_last_call < 1.0 / self.calls_per_second:
            time.sleep(1.0 / self.calls_per_second - time_since_last_call)
        self.last_call = time.time()


def process_metrics(data, database, geo_location=None):
    domain_family_mapping = {
        'gmail.com': 'Gmail',
        'yahoo.com': 'Yahoo',
        'yahoo.fr': 'Yahoo',
        'outlook.com': 'Outlook',
        'hotmail.com': 'Outlook',
        'hotmail.fr': 'Outlook',
        'live.com': 'Outlook',
        'windowslive.com': 'Outlook',
        'orange.fr': 'Orange',
        'wanadoo.fr': 'Orange',
        'free.fr': 'Free',
        'sfr.fr': 'SFR',
        'laposte.net': 'LaPoste',
    }

    metrics_batch = []
    if 'Data' in data and 'SummaryStatistics' in data['Data']:
        for stat in data['Data']['SummaryStatistics']:
            domain = stat.get('Domain', '').lower()
            domain_parts = domain.split('@')[-1].split('.')
            domain_family = domain_family_mapping.get(domain_parts[-1], 'Other')

            # Si geo_location n'est pas fourni, l'extraire du nom de la base
            current_geo = geo_location or extract_country_codes(database.name)

            metrics_batch.append(
                CampaignMetrics(
                    database=database,
                    date=timezone.now().date(),
                    domain_family=domain_family,
                    geo_location=current_geo,
                    sent=stat.get('Sent', 0),
                    bounced=stat.get('Bounced', 0),
                    delivered=stat.get('Delivered', 0),
                    opens=stat.get('Opens', 0),
                    unique_opens=stat.get('UniqueOpens', 0),
                    clicks=stat.get('Clicks', 0),
                    clickers=stat.get('Clickers', 0),
                    complaints=stat.get('Complaints', 0),
                    unsubscribes=stat.get('Unsubscribes', 0),
                    goals=stat.get('Goals', 0),
                    revenue=stat.get('Revenue', 0),
                )
            )
    return metrics_batch


def fetch_metrics(database, start_date, headers, params):
    rate_limiter = APIRateLimiter()
    rate_limiter.wait()
    
    url = f"{database.api_url.rstrip('/')}/Api/SummaryStatistics"
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def process_metrics(data, database, geo_location=None):
    domain_family_mapping = {
        'gmail.com': 'Gmail',
        'yahoo.com': 'Yahoo',
        'yahoo.fr': 'Yahoo',
        'outlook.com': 'Outlook',
        'hotmail.com': 'Outlook',
        'hotmail.fr': 'Outlook',
        'live.com': 'Outlook',
        'windowslive.com': 'Outlook',
        'orange.fr': 'Orange',
        'wanadoo.fr': 'Orange',
        'free.fr': 'Free',
        'sfr.fr': 'SFR',
        'laposte.net': 'LaPoste',
    }

    metrics_batch = []
    if 'Data' in data and 'SummaryStatistics' in data['Data']:
        for stat in data['Data']['SummaryStatistics']:
            domain = stat.get('Domain', '').lower()
            domain_parts = domain.split('@')[-1].split('.')
            domain_family = domain_family_mapping.get(domain_parts[-1], 'Other')

            metrics_batch.append(
                CampaignMetrics(
                    database=database,
                    date=timezone.now().date(),
                    domain_family=domain_family,
                    geo_location=geo_location,
                    sent=stat.get('Sent', 0),
                    bounced=stat.get('Bounced', 0),
                    delivered=stat.get('Delivered', 0),
                    opens=stat.get('Opens', 0),
                    unique_opens=stat.get('UniqueOpens', 0),
                    clicks=stat.get('Clicks', 0),
                    clickers=stat.get('Clickers', 0),
                    complaints=stat.get('Complaints', 0),
                    unsubscribes=stat.get('Unsubscribes', 0),
                    goals=stat.get('Goals', 0),
                    revenue=stat.get('Revenue', 0),
                )
            )
    return metrics_batch


def sync_database_metrics(database_id, days_back=30):
    print(f"Synchronisation en cours pour la base de données {database_id}...")
    logger.info(f"Starting sync for database {database_id}")
    
    try:
        database = ExpertSenderDatabase.objects.get(id=database_id)
        start_date = timezone.now() - timedelta(days=days_back)

        # Check if a sync is already in progress
        lock_key = f"sync_lock_{database_id}"
        if cache.get(lock_key):
            logger.warning(f"Sync already in progress for database {database_id}")
            return
        
        cache.set(lock_key, True, timeout=3600)  # 1-hour lock

        try:
            headers = {
                'X-ApiKey': database.api_key,
                'Content-Type': 'application/json',
            }
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': timezone.now().strftime('%Y-%m-%d'),
                'grouping': 'DomainFamily',
            }

            metrics_count = 0
            variations = extract_geo_variations(database.name)

            with transaction.atomic():
                if variations:
                    # Handle multi-geo database
                    for geo in variations:
                        data = fetch_metrics(database, start_date, headers, params)
                        metrics_batch = process_metrics(data, database, geo)
                        if metrics_batch:
                            CampaignMetrics.objects.bulk_create(
                                metrics_batch,
                                update_conflicts=True,
                                unique_fields=['database', 'date', 'domain_family', 'geo_location'],
                                update_fields=[
                                    'sent', 'bounced', 'delivered',
                                    'opens', 'unique_opens',
                                    'clicks', 'clickers',
                                    'complaints',
                                    'unsubscribes',
                                    'goals',
                                    'revenue',
                                ]
                            )
                            metrics_count += len(metrics_batch)
                else:
                    # Handle single-geo database
                    data = fetch_metrics(database, start_date, headers, params)
                    metrics_batch = process_metrics(data, database)
                    if metrics_batch:
                        CampaignMetrics.objects.bulk_create(
                            metrics_batch,
                            update_conflicts=True,
                            unique_fields=['database', 'date', 'domain_family'],
                            update_fields=[
                                'sent', 'bounced', 'delivered',
                                'opens', 'unique_opens',
                                'clicks', 'clickers',
                                'complaints',
                                'unsubscribes',
                                'goals',
                                'revenue',
                            ]
                        )
                        metrics_count += len(metrics_batch)

            database.last_sync = timezone.now()
            database.save()

            logger.info(f"Sync completed for {database.name}: {metrics_count} metrics processed")
        finally:
            cache.delete(lock_key)

    except Exception as e:
        logger.error(f"Error during sync: {str(e)}", exc_info=True)
    return


def schedule_task():
    """
    Schedules the sync task using `schedule`.
    """
    databases = ExpertSenderDatabase.objects.filter(is_active=True)
    for database in databases:
        schedule.every().day.at("01:00").do(sync_database_metrics, database.id)


if __name__ == "__main__":
    schedule_task()
    while True:
        schedule.run_pending()
        time.sleep(1)