from django.core.management.base import BaseCommand
from authentication.models import Department

class Command(BaseCommand):
    help = 'Créer des départements par défaut'

    def handle(self, *args, **kwargs):
        departments = [ 
            {'name': 'R&D', 'is_admin': True},
            {'name': 'TM', 'is_admin': False},
            {'name': 'DEV', 'is_admin': False},
            {'name': 'AM', 'is_admin': False},
            {'name': 'COMPTA', 'is_admin': False},
        ]

        for dept in departments: 
            Department.objects.get_or_create(**dept)

        self.stdout.write(self.style.SUCCESS('Départements par défaut créés avec succès'))
