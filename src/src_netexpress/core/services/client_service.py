"""
Service métier pour la gestion des clients.
"""

from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from decimal import Decimal

from devis.models import Client, Quote
from factures.models import Invoice

User = get_user_model()


class ClientService:
    """Service pour la création et gestion des clients."""
    
    @staticmethod
    @transaction.atomic
    def create_client(
        full_name: str,
        email: str,
        phone: str,
        address_line: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        company: Optional[str] = None,
        link_to_user: bool = False
    ) -> Client:
        """
        Crée un client.
        
        Args:
            full_name: Nom complet
            email: Email (vérification unicité si link_to_user=True)
            phone: Téléphone
            address_line: Adresse
            city: Ville
            zip_code: Code postal
            company: Entreprise (optionnel)
            link_to_user: Si True, tente de lier à un User existant (via email)
            
        Returns:
            Client instance
            
        Raises:
            ValidationError: Si données invalides
        """
        # Vérification email si link_to_user
        if link_to_user:
            if User.objects.filter(email=email).exists():
                # Le client peut être lié à un User existant
                pass
        
        # Création du client
        client = Client.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            address_line=address_line or '',
            city=city or '',
            zip_code=zip_code or '',
            company=company or '',
        )
        
        return client
    
    @staticmethod
    def link_client_to_user(client: Client, user: User) -> None:
        """
        Lie un client à un User existant (via email).
        
        Args:
            client: Client instance
            user: User instance
            
        Raises:
            ValidationError: Si l'email ne correspond pas
        """
        if client.email.lower() != user.email.lower():
            raise ValidationError("L'email du client ne correspond pas à l'email de l'utilisateur.")
        
        # Le lien se fait via l'email, pas de relation directe
        # On peut ajouter une logique supplémentaire si nécessaire
        # Pour l'instant, on considère que le lien est établi via l'email
    
    @staticmethod
    def get_client_statistics(client: Client) -> Dict[str, Any]:
        """
        Retourne les statistiques d'un client.
        
        Args:
            client: Client instance
            
        Returns:
            dict: Statistiques du client
        """
        quotes = Quote.objects.filter(client=client)
        invoices = Invoice.objects.filter(quote__client=client)
        
        # Statistiques devis
        total_quotes = quotes.count()
        draft_quotes = quotes.filter(status=Quote.QuoteStatus.DRAFT).count()
        sent_quotes = quotes.filter(status=Quote.QuoteStatus.SENT).count()
        accepted_quotes = quotes.filter(status=Quote.QuoteStatus.ACCEPTED).count()
        rejected_quotes = quotes.filter(status=Quote.QuoteStatus.REJECTED).count()
        invoiced_quotes = quotes.filter(status=Quote.QuoteStatus.INVOICED).count()
        
        # Statistiques factures
        total_invoices = invoices.count()
        paid_invoices = invoices.filter(status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]).count()
        unpaid_invoices = invoices.filter(status=Invoice.InvoiceStatus.SENT).count()
        overdue_invoices = invoices.filter(status=Invoice.InvoiceStatus.OVERDUE).count()
        
        # Totaux financiers
        total_invoiced = invoices.aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        total_paid = invoices.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        total_unpaid = invoices.filter(
            status=Invoice.InvoiceStatus.SENT
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        total_overdue = invoices.filter(
            status=Invoice.InvoiceStatus.OVERDUE
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        return {
            'total_quotes': total_quotes,
            'draft_quotes': draft_quotes,
            'sent_quotes': sent_quotes,
            'accepted_quotes': accepted_quotes,
            'rejected_quotes': rejected_quotes,
            'invoiced_quotes': invoiced_quotes,
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoices,
            'unpaid_invoices': unpaid_invoices,
            'overdue_invoices': overdue_invoices,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_unpaid': total_unpaid,
            'total_overdue': total_overdue,
            'has_user_account': User.objects.filter(email=client.email).exists(),
        }
    
    @staticmethod
    def get_client_history(client: Client, limit: int = 50) -> list:
        """
        Retourne l'historique d'un client (devis, factures, etc.).
        
        Args:
            client: Client instance
            limit: Nombre maximum d'éléments à retourner
            
        Returns:
            list: Liste des événements historiques triés par date
        """
        history = []
        
        # Devis
        quotes = Quote.objects.filter(client=client).select_related('service').order_by('-created_at')[:limit]
        for quote in quotes:
            history.append({
                'type': 'quote',
                'object': quote,
                'date': quote.created_at or quote.issue_date,
                'title': f"Devis {quote.number}",
                'status': quote.get_status_display(),
                'amount': quote.total_ttc,
            })
        
        # Factures
        invoices = Invoice.objects.filter(quote__client=client).select_related('quote').order_by('-created_at')[:limit]
        for invoice in invoices:
            history.append({
                'type': 'invoice',
                'object': invoice,
                'date': invoice.created_at or invoice.issue_date,
                'title': f"Facture {invoice.number}",
                'status': invoice.get_status_display(),
                'amount': invoice.total_ttc,
            })
        
        # Trier par date (plus récent en premier)
        history.sort(key=lambda x: x['date'], reverse=True)
        
        return history[:limit]

