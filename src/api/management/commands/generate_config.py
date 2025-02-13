# api/management/commands/generate_config.py

from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape ExpertSender databases and generate api_config.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output path for the file (default: config/api_config1.json)',
            default='config/api_config1.json'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Enable JSON pretty-print formatting'
        )
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='ExpertSender username'
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='ExpertSender password'
        )

    def get_session(self, username, password):
        """Établit une session authentifiée avec ExpertSender via Selenium."""
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        
        driver.get("https://service8.esv2.com/Account/LogOn")

        try: 
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "Email"))
            )
            email_input.send_keys(username)

            password_input = driver.find_element(By.ID, "Password")
            password_input.send_keys(password)
            password_input.send_keys(Keys.RETURN)

            WebDriverWait(driver, 15).until(EC.url_contains("dashboard"))
            logger.info("Authentification réussie.")

            return driver
        except Exception as e: 
            logger.error(f"Erreur lors de l'authentification : {e}")
            driver.quit()
            raise

    def scrape_databases(self, driver):
        """Récupère les informations des bases de données."""
        databases = []
        
        driver.get("https://www.expertsender.com/databases")
        
        try:
            time.sleep(10)  # Attendre que la page soit chargée
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Parcourir le tableau des bases de données
            for db_row in soup.find_all('tr', class_='database-row'):
                db_info = {
                    'name': db_row.find('td', class_='name').text.strip(),
                    'api_url': db_row.find('td', class_='api-url').text.strip(),
                    'api_key': db_row.find('td', class_='api-key').text.strip(),
                    'is_active': 'inactive' not in db_row.get('class', [])
                }
                databases.append(db_info)
            
            return databases
        
        except Exception as e:
            logger.error(f"Erreur lors du scraping : {e}")
            raise

    def extract_api_number(self, api_url):
        """Extrait le numéro d'API de l'URL."""
        # Pour les URLs ESV2
        esv2_match = re.search(r'api(\d+)\.esv2\.com', api_url)
        if esv2_match:
            return f"api{esv2_match.group(1)}"
        
        # Pour poradadnia.com
        if 'poradadnia.com' in api_url:
            return "pl_api"
        
        # Extraction générique basée sur le sous-domaine
        parsed_url = urlparse(api_url)
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 2 and domain_parts[0].startswith('api'):
            return domain_parts[0]
            
        return None

    def generate_config(self, databases, config_path):
        """Génère ou met à jour la configuration à partir des bases scrapées."""
        try:
            # Charger le fichier de configuration existant
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            # Si le fichier n'existe pas, créer une configuration vide
            config = {
                "expertsender_configs": {}
            }
        
        for db in databases:
            if not db['is_active']:
                continue
            
            api_number = self.extract_api_number(db['api_url'])
            if not api_number:
                logger.warning(f"Impossible d'extraire le numéro d'API pour {db['name']}")
                continue
            
            if api_number not in config["expertsender_configs"]:
                config["expertsender_configs"][api_number] = {
                    "base_url": db['api_url'],
                    "accounts": {}
                }
            
            # Vérifier si la base de données existe déjà
            existing_account_names = [config["expertsender_configs"][api_number]["accounts"][id]['name'] for id in config["expertsender_configs"][api_number]["accounts"]]
            if db['name'] not in existing_account_names:
                db_id = str(len(config["expertsender_configs"][api_number]["accounts"]) + 1)
                config["expertsender_configs"][api_number]["accounts"][db_id] = {
                    "name": db['name'],
                    "api_key": db['api_key']
                }
        
        # Écrire le fichier de configuration mis à jour
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(
                config,
                f,
                indent=4 if self.option_dict.get('pretty', False) else None,
                ensure_ascii=False
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Configuration mise à jour avec succès dans {config_path}'
            )
        )

    def handle(self, *args, **options):
        try:
            # Établir la session
            driver = self.get_session(options['username'], options['password'])
            
            # Scraper les bases de données
            logger.info("Récupération des bases de données...")
            databases = self.scrape_databases(driver)
            
            # Générer ou mettre à jour la configuration
            logger.info("Mise à jour de la configuration...")
            self.generate_config(databases, options['output'])
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la génération : {str(e)}')
            )
        
        finally:
            if 'driver' in locals():
                driver.quit()
