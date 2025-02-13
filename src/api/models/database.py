from django.db import models
from django.core.validators import URLValidator
from django.utils.timezone import now
import requests
from requests.exceptions import RequestException
import logging
import xml.etree.ElementTree as ET
import re

logger = logging.getLogger(__name__)

class ExpertSenderDatabase(models.Model):
    SYNC_STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('success', 'Succès'),
        ('failed', 'Échec')
    ]

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nom unique de la base de données"
    )
    description = models.TextField(
        blank=True,
        help_text="Description optionnelle de la base de données"
    )
    api_key = models.CharField(
        max_length=500,
        help_text="Clé API ExpertSender"
    )
    api_url = models.URLField(
        validators=[URLValidator()],
        help_text="URL de l'API ExpertSender (ex: https://api5.esv2.com/v2/)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indique si la base est active"
    )
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/heure de la dernière synchronisation"
    )
    last_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        help_text="Statut de la dernière synchronisation"
    )
    last_sync_error = models.TextField(
        blank=True,
        help_text="Message d'erreur de la dernière synchronisation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ExpertSender Database"
        verbose_name_plural = "ExpertSender Databases"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_sync']),
            models.Index(fields=['last_sync_status']),
        ]

    def __str__(self):
        return f"{self.name} (Statut: {self.get_last_sync_status_display()})"

    def fetch_data(self, endpoint):
        try:
            headers = {
                "X-ApiKey": self.api_key,
                "Content-Type": "application/json",
            }
            url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            logger.info(f"Fetching data from {url} for database {self.name}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            if "application/xml" in response.headers.get("Content-Type", ""):
                return ET.fromstring(response.content)  # Parse XML
            
            return response.json()
            
        except RequestException as e:
            logger.error(f"Error fetching data for {self.name}: {str(e)}")
            raise

    def synchronize(self, endpoint):
        self.last_sync_status = 'running'
        self.save(update_fields=['last_sync_status'])
        
        try:
            data = self.fetch_data(endpoint)
            self.last_sync = now()
            self.last_sync_status = 'success'
            self.last_sync_error = ''
            self.save(update_fields=['last_sync', 'last_sync_status', 'last_sync_error'])
            return data
            
        except Exception as e:
            error_message = f"Failed to synchronize {self.name}: {str(e)}"
            logger.error(error_message)
            self.last_sync_status = 'failed'
            self.last_sync_error = error_message
            self.save(update_fields=['last_sync_status', 'last_sync_error'])
            raise
            
    def get_geo_variations(self): 
        counties = re.findall(r'\[([A-Z]{2})\]', self.name)
        base_name = re.sub(r'\[([A-Z]{2})\]', '', self.name).strip()

        return [f'[{county}] {base_name}' for county in counties]
    
    def is_multi_geo(self): 
        '''
            ato mdefinir ra multiGeo le base
        '''
        return len(re.findall(r'\[([A-Z]{2})\]', self.name)) > 1