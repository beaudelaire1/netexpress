"""
Service métier pour les analyses avancées et le reporting.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncMonth, TruncWeek, ExtractMonth, ExtractYear
from django.contrib.auth.models import User

from devis.models import Quote, Client
from factures.models import Invoice
from tasks.models import Task
from services.models import Service, Category


class AnalyticsService:
    """Service pour les analyses avancées du dashboard."""
    
    @staticmethod
    def get_advanced_kpis(period: str = 'month') -> dict:
        """
        Calcule des KPIs avancés avec comparaison période précédente.
        
        Args:
            period: 'week', 'month', 'quarter', 'year'
            
        Returns:
            dict: KPIs avec variations
        """
        now = timezone.now()
        
        # Définir les périodes
        if period == 'week':
            current_start = now - timedelta(days=now.weekday())
            previous_start = current_start - timedelta(weeks=1)
            previous_end = current_start
        elif period == 'month':
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_start = (current_start - timedelta(days=1)).replace(day=1)
            previous_end = current_start
        elif period == 'quarter':
            quarter = (now.month - 1) // 3
            current_start = now.replace(month=quarter * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_start = (current_start - timedelta(days=1)).replace(day=1)
            previous_start = previous_start.replace(month=((previous_start.month - 1) // 3) * 3 + 1)
            previous_end = current_start
        else:  # year
            current_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_start = current_start.replace(year=current_start.year - 1)
            previous_end = current_start
        
        # CA période courante
        current_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
            issue_date__gte=current_start
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        # CA période précédente
        previous_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
            issue_date__gte=previous_start,
            issue_date__lt=previous_end
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        # Variation CA
        if previous_revenue > 0:
            revenue_variation = ((current_revenue - previous_revenue) / previous_revenue) * 100
        else:
            revenue_variation = 100 if current_revenue > 0 else 0
        
        # Nouveaux clients période courante
        current_clients = Client.objects.filter(created_at__gte=current_start).count()
        previous_clients = Client.objects.filter(
            created_at__gte=previous_start, created_at__lt=previous_end
        ).count()
        clients_variation = current_clients - previous_clients
        
        # Devis envoyés
        current_quotes = Quote.objects.filter(
            issue_date__gte=current_start,
            status__in=[Quote.QuoteStatus.SENT, Quote.QuoteStatus.ACCEPTED, Quote.QuoteStatus.REJECTED]
        ).count()
        previous_quotes = Quote.objects.filter(
            issue_date__gte=previous_start, issue_date__lt=previous_end,
            status__in=[Quote.QuoteStatus.SENT, Quote.QuoteStatus.ACCEPTED, Quote.QuoteStatus.REJECTED]
        ).count()
        
        # Taux de conversion
        accepted_current = Quote.objects.filter(
            issue_date__gte=current_start, status=Quote.QuoteStatus.ACCEPTED
        ).count()
        conversion_rate = (accepted_current / current_quotes * 100) if current_quotes > 0 else 0
        
        accepted_previous = Quote.objects.filter(
            issue_date__gte=previous_start, issue_date__lt=previous_end,
            status=Quote.QuoteStatus.ACCEPTED
        ).count()
        conversion_previous = (accepted_previous / previous_quotes * 100) if previous_quotes > 0 else 0
        conversion_variation = conversion_rate - conversion_previous
        
        # Tâches complétées
        current_tasks = Task.objects.filter(
            due_date__gte=current_start.date(), status=Task.STATUS_COMPLETED
        ).count()
        previous_tasks = Task.objects.filter(
            due_date__gte=previous_start.date(), due_date__lt=previous_end.date(),
            status=Task.STATUS_COMPLETED
        ).count()
        
        # Panier moyen
        avg_invoice = Invoice.objects.filter(
            issue_date__gte=current_start,
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
        ).aggregate(avg=Avg('total_ttc'))['avg'] or Decimal('0.00')
        
        return {
            'current_revenue': float(current_revenue),
            'previous_revenue': float(previous_revenue),
            'revenue_variation': round(float(revenue_variation), 1),
            'current_clients': current_clients,
            'clients_variation': clients_variation,
            'current_quotes': current_quotes,
            'previous_quotes': previous_quotes,
            'conversion_rate': round(conversion_rate, 1),
            'conversion_variation': round(conversion_variation, 1),
            'current_tasks': current_tasks,
            'previous_tasks': previous_tasks,
            'avg_invoice': float(avg_invoice),
            'period': period,
        }
    
    @staticmethod
    def get_revenue_by_service(months: int = 12) -> list:
        """
        CA par service sur les N derniers mois.
        """
        from devis.models import QuoteItem
        
        start_date = timezone.now() - timedelta(days=30 * months)
        
        # Revenus par service via les lignes de facture
        service_revenue = QuoteItem.objects.filter(
            quote__status=Quote.QuoteStatus.INVOICED,
            quote__issue_date__gte=start_date,
            service__isnull=False
        ).values('service__title').annotate(
            total=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total')[:10]
        
        return list(service_revenue)
    
    @staticmethod
    def get_revenue_by_client(limit: int = 10) -> list:
        """
        Top clients par CA.
        """
        client_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
        ).values(
            'quote__client__full_name', 'quote__client__company'
        ).annotate(
            total=Sum('total_ttc'),
            invoice_count=Count('id')
        ).order_by('-total')[:limit]
        
        return list(client_revenue)
    
    @staticmethod
    def get_monthly_comparison(year: int = None) -> list:
        """
        Comparaison mensuelle CA année courante vs année précédente.
        """
        if year is None:
            year = timezone.now().year
        
        months = []
        for month in range(1, 13):
            # Année courante
            current_revenue = Invoice.objects.filter(
                issue_date__year=year,
                issue_date__month=month,
                status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
            ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
            
            # Année précédente
            previous_revenue = Invoice.objects.filter(
                issue_date__year=year - 1,
                issue_date__month=month,
                status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
            ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
            
            months.append({
                'month': month,
                'month_name': datetime(year, month, 1).strftime('%B'),
                'current_year': float(current_revenue),
                'previous_year': float(previous_revenue),
            })
        
        return months
    
    @staticmethod
    def get_worker_detailed_stats() -> list:
        """
        Statistiques détaillées par worker.
        """
        from accounts.models import Profile
        
        workers = User.objects.filter(
            profile__role=Profile.ROLE_WORKER,
            is_active=True
        ).prefetch_related('assigned_tasks')
        
        stats = []
        for worker in workers:
            tasks = worker.assigned_tasks.all()
            total = tasks.count()
            completed = tasks.filter(status=Task.STATUS_COMPLETED).count()
            in_progress = tasks.filter(status=Task.STATUS_IN_PROGRESS).count()
            overdue = tasks.filter(status=Task.STATUS_OVERDUE).count()
            upcoming = tasks.filter(status=Task.STATUS_UPCOMING).count()
            
            # Temps moyen de complétion (si disponible)
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            stats.append({
                'worker': worker,
                'total_tasks': total,
                'completed': completed,
                'in_progress': in_progress,
                'overdue': overdue,
                'upcoming': upcoming,
                'completion_rate': round(completion_rate, 1),
            })
        
        return sorted(stats, key=lambda x: x['completion_rate'], reverse=True)
    
    @staticmethod
    def get_quote_funnel() -> dict:
        """
        Funnel de conversion des devis.
        """
        total = Quote.objects.count()
        draft = Quote.objects.filter(status=Quote.QuoteStatus.DRAFT).count()
        sent = Quote.objects.filter(status=Quote.QuoteStatus.SENT).count()
        accepted = Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count()
        rejected = Quote.objects.filter(status=Quote.QuoteStatus.REJECTED).count()
        invoiced = Quote.objects.filter(status=Quote.QuoteStatus.INVOICED).count()
        
        return {
            'total': total,
            'draft': draft,
            'sent': sent,
            'accepted': accepted,
            'rejected': rejected,
            'invoiced': invoiced,
            'sent_rate': round((sent + accepted + rejected + invoiced) / total * 100, 1) if total > 0 else 0,
            'acceptance_rate': round(accepted / (sent + accepted + rejected) * 100, 1) if (sent + accepted + rejected) > 0 else 0,
            'invoice_rate': round(invoiced / accepted * 100, 1) if accepted > 0 else 0,
        }
    
    @staticmethod
    def get_overdue_invoices() -> list:
        """
        Liste détaillée des factures impayées/en retard.
        """
        return Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.OVERDUE, Invoice.InvoiceStatus.SENT]
        ).select_related('quote__client').order_by('due_date')
    
    @staticmethod
    def get_services_demand() -> list:
        """
        Services les plus demandés.
        """
        from devis.models import QuoteItem
        
        services = QuoteItem.objects.filter(
            service__isnull=False
        ).values('service__title', 'service__id').annotate(
            request_count=Count('id'),
            total_revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-request_count')[:10]
        
        return list(services)


class ReportingService:
    """Service pour la génération de rapports."""
    
    @staticmethod
    def generate_revenue_report(start_date, end_date) -> dict:
        """
        Génère un rapport de CA détaillé.
        """
        invoices = Invoice.objects.filter(
            issue_date__gte=start_date,
            issue_date__lte=end_date
        ).select_related('quote__client').order_by('issue_date')
        
        total_ht = invoices.aggregate(total=Sum('total_ht'))['total'] or Decimal('0.00')
        total_tva = invoices.aggregate(total=Sum('tva'))['total'] or Decimal('0.00')
        total_ttc = invoices.aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        paid = invoices.filter(status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL])
        paid_amount = paid.aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'invoices': invoices,
            'invoice_count': invoices.count(),
            'total_ht': total_ht,
            'total_tva': total_tva,
            'total_ttc': total_ttc,
            'paid_amount': paid_amount,
            'unpaid_amount': total_ttc - paid_amount,
        }
    
    @staticmethod
    def generate_client_report(start_date, end_date) -> dict:
        """
        Génère un rapport par client.
        """
        clients = Client.objects.annotate(
            quote_count=Count('quotes', filter=Q(quotes__issue_date__gte=start_date, quotes__issue_date__lte=end_date)),
            invoice_total=Sum('quotes__invoices__total_ttc', filter=Q(
                quotes__invoices__issue_date__gte=start_date,
                quotes__invoices__issue_date__lte=end_date
            ))
        ).filter(quote_count__gt=0).order_by('-invoice_total')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'clients': clients,
            'client_count': clients.count(),
        }
    
    @staticmethod
    def generate_worker_report(start_date, end_date) -> dict:
        """
        Génère un rapport de performance workers.
        """
        from accounts.models import Profile
        
        workers = User.objects.filter(
            profile__role=Profile.ROLE_WORKER
        ).annotate(
            total_tasks=Count('assigned_tasks', filter=Q(
                assigned_tasks__due_date__gte=start_date,
                assigned_tasks__due_date__lte=end_date
            )),
            completed_tasks=Count('assigned_tasks', filter=Q(
                assigned_tasks__due_date__gte=start_date,
                assigned_tasks__due_date__lte=end_date,
                assigned_tasks__status=Task.STATUS_COMPLETED
            )),
            overdue_tasks=Count('assigned_tasks', filter=Q(
                assigned_tasks__due_date__gte=start_date,
                assigned_tasks__due_date__lte=end_date,
                assigned_tasks__status=Task.STATUS_OVERDUE
            ))
        ).filter(total_tasks__gt=0)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'workers': workers,
        }
    
    @staticmethod
    def export_to_csv(data: list, headers: list, filename: str) -> str:
        """
        Exporte des données en CSV.
        """
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(headers)
        
        for row in data:
            writer.writerow(row)
        
        return output.getvalue()

