"""
Commande de gestion pour configurer les permissions des rôles NetExpress.

Usage:
    python manage.py setup_role_permissions

Cette commande :
1. Crée les groupes Django pour chaque rôle
2. Attribue les permissions appropriées à chaque groupe
3. Synchronise les permissions des utilisateurs existants
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.models import Profile
from accounts.signals import setup_role_groups, setup_user_permissions


User = get_user_model()


class Command(BaseCommand):
    help = "Configure les groupes et permissions pour les rôles NetExpress"

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-users',
            action='store_true',
            help='Synchronise également les permissions de tous les utilisateurs existants',
        )

    def handle(self, *args, **options):
        self.stdout.write("Configuration des permissions par rôle...")
        
        # 1. Créer/mettre à jour les groupes
        try:
            setup_role_groups()
            self.stdout.write(self.style.SUCCESS("[OK] Groupes de roles crees/mis a jour"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERREUR] Creation des groupes: {e}"))
            return
        
        # 2. Afficher les rôles configurés
        self.stdout.write("\nRôles configurés :")
        self.stdout.write(f"  - {Profile.ROLE_ADMIN_TECHNICAL}: Superuser (accès complet)")
        self.stdout.write(f"  - {Profile.ROLE_ADMIN_BUSINESS}: Staff avec permissions métier")
        self.stdout.write(f"  - {Profile.ROLE_WORKER}: Permissions limitées (tâches)")
        self.stdout.write(f"  - {Profile.ROLE_CLIENT}: Permissions minimales (lecture)")
        
        # 3. Synchroniser les utilisateurs existants si demandé
        if options['sync_users']:
            self.stdout.write("\nSynchronisation des utilisateurs existants...")
            profiles = Profile.objects.select_related('user').all()
            synced = 0
            errors = 0
            
            for profile in profiles:
                try:
                    setup_user_permissions(profile.user, profile.role)
                    synced += 1
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ! Erreur pour {profile.user.username}: {e}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"[OK] {synced} utilisateurs synchronises")
            )
            if errors:
                self.stdout.write(
                    self.style.WARNING(f"  ({errors} erreurs)")
                )
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Configuration terminee !"))
        self.stdout.write("\nProchaines étapes :")
        self.stdout.write("  1. Les nouveaux profils auront automatiquement les bonnes permissions")
        self.stdout.write("  2. Pour synchroniser les utilisateurs existants : python manage.py setup_role_permissions --sync-users")

