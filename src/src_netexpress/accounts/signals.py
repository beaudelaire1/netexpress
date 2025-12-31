"""
Signaux pour la gestion automatique des permissions selon les rôles NetExpress.

Ce module gère l'attribution automatique des permissions Django
en fonction du rôle défini dans le profil utilisateur.
"""
import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

logger = logging.getLogger(__name__)

# Mapping rôle -> groupe Django
ROLE_GROUP_MAPPING = {
    Profile.ROLE_ADMIN_BUSINESS: 'AdminBusiness',
    Profile.ROLE_WORKER: 'Workers',
    Profile.ROLE_CLIENT: 'Clients',
    # admin_technical n'a pas de groupe (superuser direct)
}

# Définition des permissions par rôle
ROLE_PERMISSIONS = {
    Profile.ROLE_ADMIN_TECHNICAL: {
        # Accès complet à tout
        'grant_all': True,
    },
    Profile.ROLE_ADMIN_BUSINESS: {
        # Permissions métier complètes
        'models': [
            # Devis
            ('devis', 'quote', ['add', 'change', 'view', 'delete']),
            ('devis', 'quoteitem', ['add', 'change', 'view', 'delete']),
            # Factures
            ('factures', 'invoice', ['add', 'change', 'view', 'delete']),
            ('factures', 'invoiceitem', ['add', 'change', 'view', 'delete']),
            # Clients
            ('clients', 'client', ['add', 'change', 'view', 'delete']),
            # Tasks
            ('tasks', 'task', ['add', 'change', 'view', 'delete']),
            # Services
            ('services', 'service', ['add', 'change', 'view']),
            ('services', 'servicecategory', ['add', 'change', 'view']),
            # Accounts (lecture seule sur profils)
            ('accounts', 'profile', ['view', 'change']),
            # Auth (gestion des utilisateurs workers/clients)
            ('auth', 'user', ['add', 'change', 'view']),
        ],
        'is_staff': True,
    },
    Profile.ROLE_WORKER: {
        'models': [
            # Lecture de leurs tâches assignées
            ('tasks', 'task', ['view', 'change']),
            # Lecture des services
            ('services', 'service', ['view']),
            # Leur propre profil
            ('accounts', 'profile', ['view']),
        ],
        'is_staff': False,
        'group': 'Workers',
    },
    Profile.ROLE_CLIENT: {
        'models': [
            # Lecture de leurs devis/factures
            ('devis', 'quote', ['view']),
            ('factures', 'invoice', ['view']),
            # Leur propre profil
            ('accounts', 'profile', ['view']),
        ],
        'is_staff': False,
        'group': 'Clients',
    },
}


def get_or_create_permission(app_label, model_name, action):
    """Récupère ou crée une permission Django standard."""
    codename = f"{action}_{model_name}"
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': f"Can {action} {model_name}"}
        )
        return permission
    except ContentType.DoesNotExist:
        return None


def sync_user_groups(user, role):
    """Synchronise les groupes Django avec le rôle du profil."""
    # Récupérer le groupe correspondant au rôle
    target_group_name = ROLE_GROUP_MAPPING.get(role)
    
    # Retirer l'utilisateur de tous les groupes de rôle
    all_role_groups = list(ROLE_GROUP_MAPPING.values())
    for group_name in all_role_groups:
        try:
            group = Group.objects.get(name=group_name)
            user.groups.remove(group)
        except Group.DoesNotExist:
            pass
    
    # Ajouter au bon groupe si défini
    if target_group_name:
        group, created = Group.objects.get_or_create(name=target_group_name)
        user.groups.add(group)
        if created:
            logger.info(f"Groupe '{target_group_name}' créé pour le rôle '{role}'")


def setup_user_permissions(user, role):
    """Configure les permissions et groupes d'un utilisateur selon son rôle."""
    config = ROLE_PERMISSIONS.get(role, {})
    
    # Synchroniser les groupes Django
    sync_user_groups(user, role)
    
    # Gérer is_staff
    if 'is_staff' in config:
        if user.is_staff != config['is_staff']:
            user.is_staff = config['is_staff']
            user.save(update_fields=['is_staff'])
    
    # Admin technique : toutes les permissions via is_superuser
    if config.get('grant_all'):
        needs_update = []
        if not user.is_superuser:
            user.is_superuser = True
            needs_update.append('is_superuser')
        if not user.is_staff:
            user.is_staff = True
            needs_update.append('is_staff')
        if needs_update:
            user.save(update_fields=needs_update)
        return
    
    # Si l'utilisateur est superuser, pas besoin d'ajouter des permissions
    if user.is_superuser:
        return
    
    # Supprimer les anciennes permissions individuelles
    user.user_permissions.clear()
    
    # Ajouter les nouvelles permissions
    models_config = config.get('models', [])
    for app_label, model_name, actions in models_config:
        for action in actions:
            perm = get_or_create_permission(app_label, model_name, action)
            if perm:
                user.user_permissions.add(perm)


def setup_role_groups():
    """Crée les groupes Django correspondant aux rôles avec leurs permissions."""
    for role, config in ROLE_PERMISSIONS.items():
        if config.get('grant_all'):
            # Pas de groupe pour admin technique (utilise superuser)
            continue
        
        group, created = Group.objects.get_or_create(name=f"Role_{role}")
        
        if created or True:  # Toujours mettre à jour les permissions
            group.permissions.clear()
            models_config = config.get('models', [])
            for app_label, model_name, actions in models_config:
                for action in actions:
                    perm = get_or_create_permission(app_label, model_name, action)
                    if perm:
                        group.permissions.add(perm)
    
    return True


@receiver(post_save, sender=Profile)
def sync_permissions_on_profile_save(sender, instance, created, **kwargs):
    """
    Synchronise automatiquement les permissions de l'utilisateur
    lorsque son profil est créé ou modifié.
    """
    if instance.user_id:
        try:
            setup_user_permissions(instance.user, instance.role)
        except Exception:
            # Ne pas bloquer la sauvegarde si les permissions échouent
            # (peut arriver lors des migrations initiales)
            pass

