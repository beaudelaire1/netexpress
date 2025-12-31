"""
Signaux pour la gestion automatique des permissions selon les rôles NetExpress.

Ce module gère l'attribution automatique des permissions Django
en fonction du rôle défini dans le profil utilisateur.

IMPORTANT: Le rôle du profil est la SOURCE DE VÉRITÉ pour les permissions.
"""
import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Profile

logger = logging.getLogger(__name__)

# Mapping rôle -> groupe Django
ROLE_GROUP_MAPPING = {
    Profile.ROLE_ADMIN_BUSINESS: 'AdminBusiness',
    Profile.ROLE_ADMIN_TECHNICAL: 'AdminTechnical',
    Profile.ROLE_WORKER: 'Workers',
    Profile.ROLE_CLIENT: 'Clients',
}

# Définition des permissions par rôle
ROLE_PERMISSIONS = {
    Profile.ROLE_ADMIN_TECHNICAL: {
        # Accès complet à tout (superuser)
        'grant_all': True,
        'is_staff': True,
        'is_superuser': True,
    },
    Profile.ROLE_ADMIN_BUSINESS: {
        # Permissions métier complètes + accès Django Admin
        'models': [
            # Devis
            ('devis', 'quote', ['add', 'change', 'view', 'delete']),
            ('devis', 'quoteitem', ['add', 'change', 'view', 'delete']),
            ('devis', 'quoterequest', ['add', 'change', 'view', 'delete']),
            # Factures
            ('factures', 'invoice', ['add', 'change', 'view', 'delete']),
            ('factures', 'invoiceitem', ['add', 'change', 'view', 'delete']),
            # Clients
            ('clients', 'client', ['add', 'change', 'view', 'delete']),
            # Tasks
            ('tasks', 'task', ['add', 'change', 'view', 'delete']),
            # Services
            ('services', 'service', ['add', 'change', 'view', 'delete']),
            ('services', 'category', ['add', 'change', 'view', 'delete']),
            # Accounts
            ('accounts', 'profile', ['view', 'change']),
            # Auth (gestion des utilisateurs)
            ('auth', 'user', ['add', 'change', 'view']),
            ('auth', 'group', ['view']),
        ],
        'is_staff': True,
        'is_superuser': False,
    },
    Profile.ROLE_WORKER: {
        'models': [
            ('tasks', 'task', ['view', 'change']),
            ('services', 'service', ['view']),
            ('accounts', 'profile', ['view']),
        ],
        'is_staff': False,
        'is_superuser': False,
        'group': 'Workers',
    },
    Profile.ROLE_CLIENT: {
        'models': [
            ('devis', 'quote', ['view']),
            ('factures', 'invoice', ['view']),
            ('accounts', 'profile', ['view']),
        ],
        'is_staff': False,
        'is_superuser': False,
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
    """
    Configure les permissions et groupes d'un utilisateur selon son rôle.
    
    Cette fonction est la source de vérité pour les permissions utilisateur.
    Elle doit être appelée à chaque modification de profil.
    """
    config = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Profile.ROLE_CLIENT])
    
    # Synchroniser les groupes Django
    sync_user_groups(user, role)
    
    # Collecter les champs à mettre à jour
    fields_to_update = []
    
    # Gérer is_staff
    target_is_staff = config.get('is_staff', False)
    if user.is_staff != target_is_staff:
        user.is_staff = target_is_staff
        fields_to_update.append('is_staff')
    
    # Gérer is_superuser
    target_is_superuser = config.get('is_superuser', False)
    if user.is_superuser != target_is_superuser:
        user.is_superuser = target_is_superuser
        fields_to_update.append('is_superuser')
    
    # Sauvegarder les modifications de l'utilisateur
    if fields_to_update:
        user.save(update_fields=fields_to_update)
        logger.info(f"[PERMISSIONS] User {user.username}: updated {fields_to_update}")
    
    # Si superuser (admin_technical), pas besoin de permissions individuelles
    if config.get('grant_all') or user.is_superuser:
        logger.info(f"[PERMISSIONS] User {user.username}: superuser, skipping individual permissions")
        return
    
    # Supprimer les anciennes permissions individuelles
    user.user_permissions.clear()
    
    # Ajouter les nouvelles permissions
    models_config = config.get('models', [])
    permissions_added = 0
    for app_label, model_name, actions in models_config:
        for action in actions:
            perm = get_or_create_permission(app_label, model_name, action)
            if perm:
                user.user_permissions.add(perm)
                permissions_added += 1
    
    logger.info(f"[PERMISSIONS] User {user.username}: {permissions_added} permissions added for role {role}")


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
            logger.info(f"[SIGNAL] Profile saved for {instance.user.username}, role={instance.role}")
        except Exception as e:
            # Ne pas bloquer la sauvegarde si les permissions échouent
            logger.warning(f"[SIGNAL] Error syncing permissions for {instance.user.username}: {e}")


User = get_user_model()

@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    S'assure qu'un profil existe pour chaque utilisateur.
    
    Pour les superusers/staff sans profil, crée automatiquement un profil
    avec le rôle approprié.
    """
    try:
        # Vérifier si le profil existe
        if hasattr(instance, 'profile'):
            profile = instance.profile
            # Si l'utilisateur est devenu superuser, mettre à jour le rôle
            if instance.is_superuser and profile.role != Profile.ROLE_ADMIN_TECHNICAL:
                profile.role = Profile.ROLE_ADMIN_TECHNICAL
                profile.save(update_fields=['role'])
                logger.info(f"[SIGNAL] Updated {instance.username} to admin_technical (is_superuser=True)")
            # Si l'utilisateur est staff mais pas superuser et pas de rôle admin
            elif instance.is_staff and not instance.is_superuser and profile.role not in [Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL]:
                profile.role = Profile.ROLE_ADMIN_BUSINESS
                profile.save(update_fields=['role'])
                logger.info(f"[SIGNAL] Updated {instance.username} to admin_business (is_staff=True)")
    except Profile.DoesNotExist:
        # Créer un nouveau profil
        if instance.is_superuser:
            role = Profile.ROLE_ADMIN_TECHNICAL
        elif instance.is_staff:
            role = Profile.ROLE_ADMIN_BUSINESS
        else:
            role = Profile.ROLE_CLIENT
        
        Profile.objects.create(user=instance, role=role)
        logger.info(f"[SIGNAL] Created profile for {instance.username} with role={role}")

