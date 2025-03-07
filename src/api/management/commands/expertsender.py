import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from api.models.database import ExpertSenderDatabase
from api.models.metrics import CampaignMetrics

logger = logging.getLogger(__name__)

class ExpertSenderAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Auth-Token': api_key,
            'Content-Type': 'application/json'
        })

    def get_statistics(self, start_date: datetime, end_date: datetime, grouping: str = "DomainFamily"):
        """
        Fetch summary statistics from the ExpertSender API.
        """
        try:
            url = f"{self.base_url}/Api/SummaryStatistics"
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'apiKey': self.api_key,
                'grouping': grouping,
            }
            headers = {'Accept': 'application/json'}
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"API Response: {data}")

            # Validate and filter statistics data
            if 'Data' in data and 'SummaryStatistics' in data['Data']:
                filtered_stats = [
                    stat for stat in data['Data']['SummaryStatistics']
                    if stat.get('DomainFamily') or stat.get('IsSummaryRow') == 'true'
                ]
                data['Data']['SummaryStatistics'] = filtered_stats

            return data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None

    def get_multi_geo_lists(self):
        """
        Fetch multi-geo databases from the ExpertSender API.
        
        """
        try:
            url = f"{self.base_url}/Api/Lists"
            params = {
                'apiKey': self.api_key,
                'grouping': 'DomainFamily'  
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Multi-Geo API Response: {data}")

            # Handle multi-geo data, assuming each entry has the same ID but different lists
            if 'Data' in data:
                return data['Data']
            return None

        except requests.RequestException as e:
            logger.error(f"API request for multi-geo lists failed: {str(e)}")
            return None


class Command(BaseCommand):
    help = 'Import statistics from ExpertSender API'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=1, help='Number of days to fetch statistics for')
        parser.add_argument('--api', type=str, help='Specific API to process (e.g., "api2")')
        parser.add_argument('--account', type=str, help='Specific account ID to process')

    def load_config(self):
        """
        Load API configuration from the JSON file.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / 'config' / 'api_config.json'

        logger.info(f"Looking for config file at: {config_path}")

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        with config_path.open() as f:
            return json.load(f)

    def process_account(self, api_config, account_id, account_data, start_date, end_date):
        """
        Process a specific account to fetch its statistics and multi-geo data from the API.
        """
        logger.info(f"Processing account {account_data['name']} ({account_id})")

        client = ExpertSenderAPI(
            base_url=api_config['base_url'],
            api_key=account_data['api_key']
        )

        # Fetch the standard statistics
        stats = client.get_statistics(start_date, end_date)
        
        # Fetch the multi-geo lists
        multi_geo_data = client.get_multi_geo_lists()

        if stats:
            stats['account_id'] = account_id
            stats['account_name'] = account_data['name']
            
            # Attach multi-geo data to the stats
            if multi_geo_data:
                stats['multi_geo_data'] = multi_geo_data
            
            return stats

        return None

    def save_statistics(self, stats, start_date, end_date):
        """
        Save the fetched statistics and multi-geo lists into the database.
        """
        try:
            # Standard database instance
            database_instance, _ = ExpertSenderDatabase.objects.update_or_create(
                id=stats['account_id'],
                defaults={'name': stats['account_name']}
            )

            # Save regular statistics
            if 'Data' in stats and 'SummaryStatistics' in stats['Data']:
                for stat_data in stats['Data']['SummaryStatistics']:
                    try:
                        CampaignMetrics.objects.update_or_create(
                            database=database_instance,
                            date=end_date,
                            domain_family=stat_data.get('DomainFamily', ''),
                            defaults={
                                'sent': stat_data.get('Sent', 0),
                                'bounced': stat_data.get('Bounced', 0),
                                'delivered': stat_data.get('Delivered', 0),
                                'opens': stat_data.get('Opens', 0),
                                'unique_opens': stat_data.get('UniqueOpens', 0),
                                'clicks': stat_data.get('Clicks', 0),
                                'clickers': stat_data.get('Clickers', 0),
                                'complaints': stat_data.get('Complaints', 0),
                                'unsubscribes': stat_data.get('Unsubscribes', 0),
                                'goals': stat_data.get('Goals', 0),
                                'goals_value': stat_data.get('GoalsValue', 0),
                                'revenue': stat_data.get('Revenue', 0),
                            } 
                        )
                    except Exception as e:
                        logger.error(f"Failed to save statistics for domain_family: {stat_data.get('DomainFamily', '')}, error: {str(e)}")

            # Optionally save multi-geo data (if needed)
            if 'multi_geo_data' in stats:
                for geo_entry in stats['multi_geo_data']:
                    # Process and save multi-geo data, e.g., creating separate models or combining with campaign metrics
                    pass

        except Exception as e:
            logger.error(f"Failed to save statistics for {stats['account_name']} ({stats['account_id']}): {str(e)}")
            raise

    def handle(self, *args, **options):
        """
        Main entry point to execute the command.
        """
        try:
            config = self.load_config()
            configs = config['expertsender_configs']

            end_date = datetime.now()
            start_date = end_date - timedelta(days=options['days'])

            if options['api']:
                if options['api'] not in configs:
                    logger.error(f"API {options['api']} not found in configuration")
                    return
                configs = {options['api']: configs[options['api']]}

            for api_name, api_config in configs.items():
                accounts = api_config['accounts']

                if options['account']:
                    if options['account'] not in accounts:
                        logger.error(f"Account {options['account']} not found in {api_name}")
                        continue
                    accounts = {options['account']: accounts[options['account']]}

                for account_id, account_data in accounts.items():
                    try:
                        stats = self.process_account(
                            api_config, account_id, account_data, start_date, end_date
                        )
                        if stats:
                            self.save_statistics(stats, start_date, end_date)
                    except Exception as e:
                        logger.error(f"Failed to process account {account_id}: {str(e)}")

            self.stdout.write(self.style.SUCCESS('Successfully imported ExpertSender statistics'))

        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Failed to import statistics: {str(e)}'))
