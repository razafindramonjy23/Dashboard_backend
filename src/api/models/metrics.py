from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from .database import ExpertSenderDatabase


class CampaignMetrics(models.Model):
    database = models.ForeignKey(
        ExpertSenderDatabase,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    date = models.DateField(default=timezone.now, null=False, blank=False)
    domain_family = models.CharField(max_length=100, blank=True, null=True)
    geo_location = models.CharField(
        max_length=225,
        blank=True,
        null=True,
        default='',
        help_text="Codes pays extraits du nom de la base de donnee(separ par des virgules)"
    )
    sent = models.IntegerField(default=0)
    bounced = models.IntegerField(default=0)
    delivered = models.IntegerField(default=0)
    opens = models.IntegerField(default=0)
    unique_opens = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    clickers = models.IntegerField(default=0)
    complaints = models.IntegerField(default=0)
    unsubscribes = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    goals_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    geo_variation = models.CharField(
        max_length=225,
        blank=True,
        null=True,
        help_text="Variation geo specifique"
    )

    class Meta:
        verbose_name = "Campaign Metric"
        verbose_name_plural = "Campaign Metrics"
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'database', 'domain_family', 'geo_location'],
                name='unique_metrics_per_date_database'
            )
        ]
        indexes = [
            models.Index(fields=['date', 'database']),
            models.Index(fields=['domain_family']),
            models.Index(fields=['geo_location']),
            models.Index(fields=['geo_variation'])
        ]

    def get_geo_location(self):
        return [loc.strip() for loc in self.geo_location.split(',') if loc.strip()]

    def save(self, *args, **kwargs):
        if not self.geo_variation and self.database:
            variations = re.findall(r'\[([A-Z]{2})\]', self.database.name)
            if variations:
                if len(variations) > 1:
                    base_name = re.sub(r'\[([A-Z]{2})\]', '', self.database.name).strip()
                    self.geo_variation = f"[{variations[0]}] {base_name}"
        super().save(*args, **kwargs)

    def open_rate(self):
        return (self.opens / self.sent) * 100 if self.sent > 0 else 0

    def click_rate(self):
        return (self.clicks / self.sent) * 100 if self.sent > 0 else 0

    def unsubscribe_rate(self):
        return (self.unsubscribes / self.sent) * 100 if self.sent > 0 else 0

    def revenue_per_email(self):
        return self.revenue / self.sent if self.sent > 0 else 0

    def clean(self):
        if self.sent < 0 or self.bounced < 0 or self.delivered < 0 or self.opens < 0:
            raise ValidationError("Les valeurs des métriques ne peuvent pas être négatives.")
        if self.bounced + self.delivered > self.sent:
            raise ValidationError("La somme de 'bounced' et 'delivered' ne peut pas dépasser 'sent'.")