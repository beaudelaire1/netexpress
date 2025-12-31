"""
Service métier pour la gestion des workers.
"""

import secrets
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from accounts.models import Profile
from tasks.models import Task

User = get_user_model()


class WorkerService:
    """Service pour la création et gestion des workers."""
    
    @staticmethod
    @transaction.atomic
    def create_worker(
        email: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        admin_user: Optional[User] = None
    ) -> tuple[User, str]:
        """
        Crée un worker avec génération automatique de compte.
        
        ⚠️ RÈGLE FONDAMENTALE : Les workers ne peuvent JAMAIS créer leur compte eux-mêmes.
        Ils sont créés UNIQUEMENT par un utilisateur de gestion.
        
        Args:
            email: Email du worker (doit être unique)
            first_name: Prénom
            last_name: Nom de famille
            phone: Téléphone (optionnel)
            admin_user: Utilisateur admin qui crée le worker (pour audit)
            
        Returns:
            tuple: (User instance, temporary_password)
            
        Raises:
            ValidationError: Si l'email existe déjà ou données invalides
        """
        # Vérification email unique
        if User.objects.filter(email=email).exists():
            raise ValidationError(f"Un utilisateur avec l'email {email} existe déjà.")
        
        # Génération username unique
        username = WorkerService._generate_username(email)
        
        # Génération mot de passe temporaire sécurisé
        temporary_password = WorkerService._generate_temporary_password()
        
        # Création du User
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=temporary_password,
            is_active=True
        )
        
        # Création ou mise à jour du Profile
        # Note: On utilise get_or_create pour être sûr que le profil existe
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': Profile.ROLE_WORKER,
                'phone': phone or '',
                'notification_preferences': {
                    'email_notifications': True,
                    'task_updates': True,
                    'quote_updates': False,
                    'invoice_updates': False,
                }
            }
        )
        
        # Si le profil existait déjà, on le met à jour
        if not created:
            profile.role = Profile.ROLE_WORKER
            if phone:
                profile.phone = phone
            profile.notification_preferences = {
                'email_notifications': True,
                'task_updates': True,
                'quote_updates': False,
                'invoice_updates': False,
            }
            profile.save()
        
        # Ajout au groupe Workers
        workers_group, _ = Group.objects.get_or_create(name='Workers')
        user.groups.add(workers_group)
        
        return user, temporary_password
    
    @staticmethod
    def _generate_username(email: str) -> str:
        """Génère un username unique à partir de l'email."""
        import re
        
        base_username = email.split('@')[0]
        # Normalisation
        base_username = re.sub(r'[^a-zA-Z0-9_-]', '_', base_username)
        base_username = re.sub(r'^[^a-zA-Z0-9]+', '', base_username) or 'worker'
        base_username = base_username[:140]
        
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            if counter > 10000:
                username = f"{base_username}_{secrets.token_hex(4)}"
                break
        
        return username
    
    @staticmethod
    def _generate_temporary_password() -> str:
        """Génère un mot de passe temporaire sécurisé."""
        # Génère un mot de passe aléatoire de 12 caractères
        # Mélange lettres majuscules, minuscules et chiffres
        import string
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        return password
    
    @staticmethod
    @transaction.atomic
    def send_worker_credentials(
        worker: User,
        temporary_password: str,
        request=None
    ) -> bool:
        """
        Envoie les identifiants au worker par email.
        
        Args:
            worker: User instance du worker
            temporary_password: Mot de passe temporaire
            request: Request object pour construire l'URL (optionnel)
            
        Returns:
            bool: True si l'email a été envoyé avec succès
        """
        try:
            login_url = request.build_absolute_uri(reverse('accounts:login')) if request else '/accounts/login/'
            
            subject = f"Vos identifiants NetExpress - {worker.get_full_name()}"
            message = f"""
Bonjour {worker.first_name},

Votre compte worker a été créé sur NetExpress.

Vos identifiants de connexion :
- Email : {worker.email}
- Mot de passe temporaire : {temporary_password}

⚠️ IMPORTANT : Veuillez changer votre mot de passe lors de votre première connexion.

Accédez à votre espace : {login_url}

Cordialement,
L'équipe NetExpress
"""
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
            send_mail(
                subject,
                message,
                from_email,
                [worker.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Log l'erreur mais ne lève pas d'exception pour ne pas bloquer la création
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de l'envoi des identifiants au worker {worker.email}: {e}")
            return False
    
    @staticmethod
    def get_worker_statistics(worker: User) -> Dict[str, Any]:
        """
        Retourne les statistiques d'un worker.
        
        Args:
            worker: User instance du worker
            
        Returns:
            dict: Statistiques du worker
        """
        tasks = Task.objects.filter(assigned_to=worker)
        
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status=Task.STATUS_COMPLETED).count()
        in_progress_tasks = tasks.filter(status=Task.STATUS_IN_PROGRESS).count()
        overdue_tasks = tasks.filter(status=Task.STATUS_OVERDUE).count()
        upcoming_tasks = tasks.filter(status=Task.STATUS_UPCOMING).count()
        
        # Calcul du taux de complétion (sur les tâches terminées)
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Tâches du mois en cours
        from datetime import datetime, timedelta
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        tasks_this_month = tasks.filter(
            created_at__gte=start_of_month
        ).count()
        completed_this_month = tasks.filter(
            status=Task.STATUS_COMPLETED,
            updated_at__gte=start_of_month
        ).count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'overdue_tasks': overdue_tasks,
            'upcoming_tasks': upcoming_tasks,
            'completion_rate': round(completion_rate, 1),
            'tasks_this_month': tasks_this_month,
            'completed_this_month': completed_this_month,
            'last_login': worker.last_login,
        }
    
    @staticmethod
    def deactivate_worker(worker: User) -> None:
        """
        Désactive un worker (is_active = False).
        
        Args:
            worker: User instance du worker
        """
        worker.is_active = False
        worker.save(update_fields=['is_active'])

