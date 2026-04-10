"""
Account creation services for NetExpress v2.

This module provides services for automatic client account creation
when quotes are validated, including user creation, profile setup,
and group assignment.
"""

from __future__ import annotations

import secrets
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Profile

User = get_user_model()


class ClientAccountCreationService:
    """Service for automatic client account creation on quote validation."""
    
    @staticmethod
    @transaction.atomic
    def create_from_quote_validation(quote) -> tuple[User, bool]:
        """
        Create client account when quote is validated.
        
        Args:
            quote: Quote instance that was validated
            
        Returns:
            tuple: (User instance, created_flag)
                - User: The created or existing user account
                - bool: True if account was created, False if it already existed
                
        Raises:
            ValidationError: If quote or client data is invalid
        """
        if not quote:
            raise ValidationError("Quote is required")
            
        client = getattr(quote, 'client', None)
        if not client:
            raise ValidationError("Quote must have an associated client")
            
        client_email = getattr(client, 'email', None)
        if not client_email:
            raise ValidationError("Client must have an email address")
            
        return ClientAccountCreationService.create_from_client(client)

    @staticmethod
    @transaction.atomic
    def create_from_client(client) -> tuple[User, bool]:
        """Create or normalize a client portal account from a client record."""
        if not client:
            raise ValidationError("Client is required")

        client_email = getattr(client, 'email', None)
        if not client_email:
            raise ValidationError("Client must have an email address")

        return ClientAccountCreationService._get_or_create_client_user(client)

    @staticmethod
    def _get_or_create_client_user(client) -> tuple[User, bool]:
        client_email = getattr(client, 'email', None)
        full_name = (getattr(client, 'full_name', '') or '').strip()
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        created = False
        existing_user = User.objects.filter(email__iexact=client_email).first()
        if existing_user:
            if existing_user.is_staff or existing_user.is_superuser:
                raise ValidationError("Un compte administrateur utilise déjà cet email. Choisissez un email client dédié.")
            existing_role = getattr(getattr(existing_user, 'profile', None), 'role', Profile.ROLE_CLIENT)
            if existing_role in {Profile.ROLE_WORKER, Profile.ROLE_ADMIN_BUSINESS, Profile.ROLE_ADMIN_TECHNICAL}:
                raise ValidationError("Cet email est déjà utilisé par un compte interne. Impossible d'activer un portail client dessus.")
            user = existing_user
        else:
            username = ClientAccountCreationService._generate_username(client_email)
            user = User.objects.create_user(
                username=username,
                email=client_email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
            created = True

        if not user.first_name and first_name:
            user.first_name = first_name
        if not user.last_name and last_name:
            user.last_name = last_name
        if not user.is_active:
            user.is_active = True
        user.save(update_fields=['first_name', 'last_name', 'is_active'])

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': Profile.ROLE_CLIENT,
                'phone': getattr(client, 'phone', ''),
                'notification_preferences': {
                    'email_notifications': True,
                    'quote_updates': True,
                    'invoice_updates': True,
                    'task_updates': False,
                },
            },
        )

        profile.role = Profile.ROLE_CLIENT
        profile.phone = getattr(client, 'phone', '')
        profile.notification_preferences = {
            'email_notifications': True,
            'quote_updates': True,
            'invoice_updates': True,
            'task_updates': False,
        }
        profile.save()

        clients_group, _ = Group.objects.get_or_create(name='Clients')
        user.groups.add(clients_group)

        return user, created
    
    @staticmethod
    def _generate_username(email: str) -> str:
        """
        Generate a unique username from email address.
        
        Args:
            email: Email address to base username on
            
        Returns:
            str: Unique username (normalized to valid Django username characters)
        """
        import re
        
        base_username = email.split('@')[0]
        # Normalize: remove invalid characters (Django usernames allow: letters, digits, @, +, -, _, .)
        # Keep only alphanumeric, underscore, and hyphen
        base_username = re.sub(r'[^a-zA-Z0-9_-]', '_', base_username)
        # Ensure it starts with alphanumeric
        base_username = re.sub(r'^[^a-zA-Z0-9]+', '', base_username) or 'user'
        # Limit length (Django username max_length is 150)
        base_username = base_username[:140]  # Leave room for counter suffix
        
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            # Prevent infinite loop (unlikely but safe)
            if counter > 10000:
                import secrets
                username = f"{base_username}_{secrets.token_hex(4)}"
                break
            
        return username
    
    @staticmethod
    def generate_invitation_token(user: User) -> str:
        """
        Generate a secure token for password setup invitation.
        
        Args:
            user: User instance to generate token for
            
        Returns:
            str: Secure token for invitation
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def link_existing_documents(user: User, client) -> None:
        """
        Link existing client documents to the new user account.
        
        Args:
            user: User instance to link documents to
            client: Client instance with existing documents
        """
        # This will be implemented when we have the ClientDocument model
        # For now, we rely on the existing client foreign key relationships
        pass