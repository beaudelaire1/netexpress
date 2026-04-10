"""
Service métier pour la gestion des clients.
"""

from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Sum
from django.utils import timezone
from decimal import Decimal

from devis.models import Client, Quote
from factures.models import Invoice
from core.models import ClientPortalDocument

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
        if link_to_user and User.objects.filter(email=email).exists():
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
        portal_documents = ClientPortalDocument.objects.filter(client=client, is_published=True)
        portal_user = User.objects.filter(email__iexact=client.email).select_related('profile').first()
        
        # Statistiques devis
        total_quotes = quotes.count()
        draft_quotes = quotes.filter(status=Quote.QuoteStatus.DRAFT).count()
        sent_quotes = quotes.filter(status=Quote.QuoteStatus.SENT).count()
        accepted_quotes = quotes.filter(status=Quote.QuoteStatus.ACCEPTED).count()
        rejected_quotes = quotes.filter(status=Quote.QuoteStatus.REJECTED).count()
        invoiced_quotes = quotes.filter(status=Quote.QuoteStatus.INVOICED).count()

        quote_conversion_base = quotes.filter(
            status__in=[
                Quote.QuoteStatus.SENT,
                Quote.QuoteStatus.ACCEPTED,
                Quote.QuoteStatus.REJECTED,
                Quote.QuoteStatus.INVOICED,
            ]
        ).count()
        quote_conversion_rate = round(
            ((accepted_quotes + invoiced_quotes) / quote_conversion_base) * 100,
            1,
        ) if quote_conversion_base else 0
        
        # Statistiques factures
        total_invoices = invoices.count()
        paid_invoices = invoices.filter(status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]).count()
        unpaid_invoices = invoices.filter(status=Invoice.InvoiceStatus.SENT).count()
        overdue_invoices = invoices.filter(status=Invoice.InvoiceStatus.OVERDUE).count()
        open_invoices = invoices.filter(
            status__in=[
                Invoice.InvoiceStatus.SENT,
                Invoice.InvoiceStatus.PARTIAL,
                Invoice.InvoiceStatus.OVERDUE,
            ]
        )
        
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

        open_balance = open_invoices.aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        average_quote_value = quotes.aggregate(avg=Avg('total_ttc'))['avg'] or Decimal('0.00')
        average_invoice_value = invoices.aggregate(avg=Avg('total_ttc'))['avg'] or Decimal('0.00')
        total_quote_pipeline = quotes.filter(
            status__in=[Quote.QuoteStatus.DRAFT, Quote.QuoteStatus.SENT, Quote.QuoteStatus.ACCEPTED]
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        total_sent_quotes_value = quotes.filter(
            status=Quote.QuoteStatus.SENT
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        ready_to_invoice_queryset = quotes.filter(status=Quote.QuoteStatus.ACCEPTED, invoices__isnull=True)
        ready_to_invoice_quotes = ready_to_invoice_queryset.count()
        total_ready_to_invoice = ready_to_invoice_queryset.aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        payment_collection_rate = round((total_paid / total_invoiced) * 100, 1) if total_invoiced else 0

        latest_quote = quotes.order_by('-issue_date', '-created_at').first()
        latest_invoice = invoices.order_by('-issue_date', '-created_at').first()
        latest_document = portal_documents.order_by('-published_at').first()
        last_portal_access = getattr(getattr(portal_user, 'profile', None), 'last_portal_access', None)

        activity_dates = [
            client.created_at,
            latest_quote.created_at if latest_quote else None,
            latest_invoice.created_at if latest_invoice else None,
            latest_document.updated_at if latest_document else None,
            last_portal_access,
        ]
        valid_activity_dates = [activity_date for activity_date in activity_dates if activity_date is not None]
        last_activity_at = max(valid_activity_dates) if valid_activity_dates else None
        days_since_last_activity = (timezone.now() - last_activity_at).days if last_activity_at else None
        account_age_days = (timezone.now() - client.created_at).days if client.created_at else 0

        published_documents_count = portal_documents.count()
        expired_documents_count = portal_documents.filter(expires_at__lt=timezone.localdate()).count()
        unopened_documents_count = portal_documents.filter(last_accessed_at__isnull=True).count()

        if total_overdue > 0:
            relationship_stage = 'Recouvrement'
            relationship_tone = 'red'
        elif open_balance > 0:
            relationship_stage = 'Encours à suivre'
            relationship_tone = 'amber'
        elif total_invoices > 0:
            relationship_stage = 'Client actif'
            relationship_tone = 'emerald'
        elif total_quotes > 0:
            relationship_stage = 'Prospect en négociation'
            relationship_tone = 'blue'
        else:
            relationship_stage = 'Nouveau contact'
            relationship_tone = 'slate'
        
        return {
            'total_quotes': total_quotes,
            'draft_quotes': draft_quotes,
            'sent_quotes': sent_quotes,
            'pending_quotes': sent_quotes,
            'accepted_quotes': accepted_quotes,
            'rejected_quotes': rejected_quotes,
            'invoiced_quotes': invoiced_quotes,
            'quote_conversion_rate': quote_conversion_rate,
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoices,
            'unpaid_invoices': unpaid_invoices,
            'overdue_invoices': overdue_invoices,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_unpaid': total_unpaid,
            'total_overdue': total_overdue,
            'open_balance': open_balance,
            'average_quote_value': average_quote_value,
            'average_invoice_value': average_invoice_value,
            'total_quote_pipeline': total_quote_pipeline,
            'total_sent_quotes_value': total_sent_quotes_value,
            'ready_to_invoice_quotes': ready_to_invoice_quotes,
            'total_ready_to_invoice': total_ready_to_invoice,
            'payment_collection_rate': payment_collection_rate,
            'published_documents_count': published_documents_count,
            'expired_documents_count': expired_documents_count,
            'unopened_documents_count': unopened_documents_count,
            'last_activity_at': last_activity_at,
            'days_since_last_activity': days_since_last_activity,
            'account_age_days': account_age_days,
            'last_quote': latest_quote,
            'last_invoice': latest_invoice,
            'last_document': latest_document,
            'last_portal_access': last_portal_access,
            'relationship_stage': relationship_stage,
            'relationship_tone': relationship_tone,
            'has_user_account': bool(portal_user),
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

        documents = ClientPortalDocument.objects.filter(client=client, is_published=True).select_related('published_by').order_by('-published_at')[:limit]
        for document in documents:
            history.append({
                'type': 'document',
                'object': document,
                'date': document.published_at,
                'title': document.title,
                'status': 'Document expiré' if document.is_expired else 'Document publié',
                'amount': None,
            })

        portal_user = User.objects.filter(email__iexact=client.email).select_related('profile').first()
        last_portal_access = getattr(getattr(portal_user, 'profile', None), 'last_portal_access', None)
        if last_portal_access:
            history.append({
                'type': 'portal',
                'object': portal_user,
                'date': last_portal_access,
                'title': 'Connexion espace client',
                'status': 'Portail consulté',
                'amount': None,
            })
        
        # Trier par date (plus récent en premier)
        history.sort(key=lambda x: x['date'], reverse=True)
        
        return history[:limit]

    @staticmethod
    def get_portal_tasks(client: Optional[Client]):
        """Retourne les tâches visibles par le client dans son portail."""
        from tasks.models import Task

        if client is None:
            return Task.objects.none()

        return (
            Task.objects.filter(client=client)
            .select_related('client', 'completed_by')
            .prefetch_related('assigned_to')
            .order_by('due_date', '-updated_at', 'title')
        )

    @staticmethod
    def get_portal_task_summary(tasks) -> Dict[str, Any]:
        """Construit une synthèse lisible des tâches rattachées au client."""
        from tasks.models import Task

        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status=Task.STATUS_COMPLETED).count()

        return {
            'total': total_tasks,
            'upcoming': tasks.filter(status=Task.STATUS_UPCOMING).count(),
            'in_progress': tasks.filter(status=Task.STATUS_IN_PROGRESS).count(),
            'almost_overdue': tasks.filter(status=Task.STATUS_ALMOST_OVERDUE).count(),
            'overdue': tasks.filter(status=Task.STATUS_OVERDUE).count(),
            'completed': completed_tasks,
            'open': tasks.exclude(status=Task.STATUS_COMPLETED).count(),
            'completion_rate': round((completed_tasks / total_tasks) * 100, 1) if total_tasks else 0,
        }

