"""
Services for Client Portal document access control and filtering.
"""

from typing import List, Optional
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils import timezone

from devis.models import Quote
from factures.models import Invoice
from ..models import ClientDocument


class ClientDocumentService:
    """Service for managing client document access and filtering."""
    
    @staticmethod
    def get_accessible_quotes(user: User) -> QuerySet[Quote]:
        """Get all quotes accessible to a client user."""
        if not user.is_authenticated:
            return Quote.objects.none()
        
        # For staff/admin users, return all quotes
        if user.is_staff or user.is_superuser:
            return Quote.objects.all()
        
        # For client users, filter by email
        user_email = getattr(user, 'email', '') or ''
        if not user_email:
            return Quote.objects.none()
        
        return Quote.objects.filter(client__email__iexact=user_email)
    
    @staticmethod
    def get_accessible_invoices(user: User) -> QuerySet[Invoice]:
        """Get all invoices accessible to a client user."""
        if not user.is_authenticated:
            return Invoice.objects.none()
        
        # For staff/admin users, return all invoices
        if user.is_staff or user.is_superuser:
            return Invoice.objects.all()
        
        # For client users, filter by email through quote relationship
        user_email = getattr(user, 'email', '') or ''
        if not user_email:
            return Invoice.objects.none()
        
        return Invoice.objects.filter(quote__client__email__iexact=user_email)
    
    @staticmethod
    def can_access_quote(user: User, quote: Quote) -> bool:
        """Check if a user can access a specific quote."""
        if not user.is_authenticated:
            return False
        
        # Staff/admin can access all quotes
        if user.is_staff or user.is_superuser:
            return True
        
        # Client users can only access their own quotes
        # Use case-insensitive comparison consistently
        user_email = getattr(user, 'email', '') or ''
        if not user_email:
            return False
        
        quote_email = getattr(quote.client, 'email', '') or ''
        return quote_email.lower() == user_email.lower()
    
    @staticmethod
    def can_access_invoice(user: User, invoice: Invoice) -> bool:
        """Check if a user can access a specific invoice."""
        if not user.is_authenticated:
            return False
        
        # Staff/admin can access all invoices
        if user.is_staff or user.is_superuser:
            return True
        
        # Client users can only access invoices linked to their quotes
        if not invoice.quote:
            return False
        
        return ClientDocumentService.can_access_quote(user, invoice.quote)
    
    @staticmethod
    def track_document_access(user: User, quote: Optional[Quote] = None, invoice: Optional[Invoice] = None):
        """Track when a client accesses a document."""
        if not user.is_authenticated or (not quote and not invoice):
            return
        
        # Only track for client users, not staff/admin
        if user.is_staff or user.is_superuser:
            return
        
        try:
            if quote:
                client_doc, created = ClientDocument.objects.get_or_create(
                    client_user=user,
                    quote=quote,
                    defaults={'access_granted_at': timezone.now()}
                )
                if not created:
                    client_doc.update_last_accessed()
            
            if invoice:
                client_doc, created = ClientDocument.objects.get_or_create(
                    client_user=user,
                    invoice=invoice,
                    defaults={'access_granted_at': timezone.now()}
                )
                if not created:
                    client_doc.update_last_accessed()
        except Exception as e:
            # Log error instead of silently failing
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors du suivi d'accès au document pour {user}: {e}", exc_info=True)
    
    @staticmethod
    def get_client_document_stats(user: User) -> dict:
        """Get document access statistics for a client."""
        if not user.is_authenticated:
            return {}
        
        quotes = ClientDocumentService.get_accessible_quotes(user)
        invoices = ClientDocumentService.get_accessible_invoices(user)
        
        # Get pending quotes (draft or sent)
        pending_quotes = quotes.filter(status__in=['draft', 'sent'])
        
        # Get unpaid invoices
        unpaid_invoices = invoices.filter(status__in=['sent', 'partial', 'overdue'])
        
        return {
            'total_quotes': quotes.count(),
            'total_invoices': invoices.count(),
            'pending_quotes': pending_quotes.count(),
            'unpaid_invoices': unpaid_invoices.count(),
        }
    
    @staticmethod
    def get_recent_documents(user: User, limit: int = 5) -> dict:
        """Get recent documents for a client dashboard."""
        if not user.is_authenticated:
            return {'quotes': [], 'invoices': []}
        
        quotes = ClientDocumentService.get_accessible_quotes(user)
        invoices = ClientDocumentService.get_accessible_invoices(user)
        
        # Get recent pending quotes
        recent_pending_quotes = quotes.filter(
            status__in=['draft', 'sent']
        ).order_by('-issue_date')[:limit]
        
        # Get recent unpaid invoices
        recent_unpaid_invoices = invoices.filter(
            status__in=['sent', 'partial', 'overdue']
        ).order_by('-issue_date')[:limit]
        
        return {
            'quotes': list(recent_pending_quotes),
            'invoices': list(recent_unpaid_invoices),
        }