from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from authentication.models import AdminToken, Department
import secrets

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialise le premier utilisateur administrateur R&D et crée un token admin'

    def handle(self, *args, **kwargs):
        # Création du token administrateur
        admin_token = AdminToken.objects.create(
            token=secrets.token_hex(16),
            description="Token initial d'administration R&D"
        )
        
        # Vérification si un superutilisateur existe déjà
        if not User.objects.filter(is_superuser=True).exists():
            # Création du premier superutilisateur (admin R&D)
            department, created = Department.objects.get_or_create(name="R&D", is_admin=True)
            admin = User.objects.create_user(
                username="Admin",
                email="admin@example.com",
                password="bef039f16d3adf9e4eb5f648142165ab",  
                first_name="Admin",
                last_name="rd_admin",
                is_superuser=True,
                is_staff=True,
                is_active=True,
                is_verified=True,
                department=department
            )
            self.stdout.write(self.style.SUCCESS(f'Superutilisateur créé avec succès: {admin.email}'))
        
        self.stdout.write(self.style.SUCCESS(f'Token administrateur créé: {admin_token.token}'))
        self.stdout.write(self.style.WARNING('IMPORTANT: Notez ce token et changez le mot de passe admin par défaut!'))
