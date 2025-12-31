"""
Commande pour corriger le rôle et les permissions d'un utilisateur spécifique.

Usage:
    python manage.py fix_user_role <username> <role>
    
Exemples:
    python manage.py fix_user_role masterjay admin_business
    python manage.py fix_user_role john admin_technical
    python manage.py fix_user_role marie worker
    python manage.py fix_user_role client1 client
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from accounts.models import Profile
from accounts.signals import setup_user_permissions

User = get_user_model()

VALID_ROLES = [
    Profile.ROLE_ADMIN_BUSINESS,
    Profile.ROLE_ADMIN_TECHNICAL,
    Profile.ROLE_WORKER,
    Profile.ROLE_CLIENT,
]


class Command(BaseCommand):
    help = "Corrige le rôle et les permissions d'un utilisateur spécifique"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help="Nom d'utilisateur à corriger")
        parser.add_argument('role', type=str, help=f"Rôle à attribuer: {', '.join(VALID_ROLES)}")
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche les changements sans les appliquer",
        )

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        dry_run = options['dry_run']
        
        # Valider le rôle
        if role not in VALID_ROLES:
            raise CommandError(f"Rôle invalide '{role}'. Rôles valides: {', '.join(VALID_ROLES)}")
        
        # Récupérer l'utilisateur
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Utilisateur '{username}' introuvable")
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Utilisateur: {username}")
        self.stdout.write(f"Email: {user.email}")
        self.stdout.write(f"{'='*50}")
        
        # Récupérer ou créer le profil
        profile, created = Profile.objects.get_or_create(user=user)
        
        self.stdout.write(f"\nÉtat actuel:")
        self.stdout.write(f"  - Rôle profil: {profile.role}")
        self.stdout.write(f"  - is_staff: {user.is_staff}")
        self.stdout.write(f"  - is_superuser: {user.is_superuser}")
        self.stdout.write(f"  - Groupes: {', '.join(g.name for g in user.groups.all()) or 'Aucun'}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] Changements qui seraient appliqués:"))
        else:
            self.stdout.write(self.style.SUCCESS("\nApplication des changements..."))
        
        # Mettre à jour le rôle du profil
        old_role = profile.role
        if old_role != role:
            self.stdout.write(f"  - Rôle: {old_role} → {role}")
            if not dry_run:
                profile.role = role
                profile.save()
        
        # Appliquer les permissions
        if not dry_run:
            setup_user_permissions(user, role)
            user.refresh_from_db()
        
        # Afficher le nouvel état
        self.stdout.write(f"\nNouvel état:")
        if not dry_run:
            profile.refresh_from_db()
            user.refresh_from_db()
        
        expected_staff = role in [Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL]
        expected_superuser = role == Profile.ROLE_ADMIN_TECHNICAL
        
        self.stdout.write(f"  - Rôle profil: {role}")
        self.stdout.write(f"  - is_staff: {user.is_staff if not dry_run else expected_staff}")
        self.stdout.write(f"  - is_superuser: {user.is_superuser if not dry_run else expected_superuser}")
        
        if not dry_run:
            self.stdout.write(f"  - Groupes: {', '.join(g.name for g in user.groups.all()) or 'Aucun'}")
        
        # Afficher le dashboard approprié
        dashboard_url = {
            Profile.ROLE_ADMIN_TECHNICAL: '/gestion/',
            Profile.ROLE_ADMIN_BUSINESS: '/admin-dashboard/',
            Profile.ROLE_WORKER: '/worker/',
            Profile.ROLE_CLIENT: '/client/',
        }.get(role, '/')
        
        self.stdout.write(f"\n{'='*50}")
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Aucun changement appliqué"))
            self.stdout.write("Exécutez sans --dry-run pour appliquer les changements")
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK] Utilisateur '{username}' configuré avec le rôle '{role}'"))
            self.stdout.write(f"\nL'utilisateur peut maintenant accéder à: {dashboard_url}")
            if role == Profile.ROLE_ADMIN_BUSINESS:
                self.stdout.write("  + Accès en lecture seule à /gestion/")
        self.stdout.write(f"{'='*50}\n")
