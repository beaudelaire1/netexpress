"""
Service métier pour le calcul des KPIs et statistiques du dashboard.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth.models import User

from devis.models import Quote
from factures.models import Invoice
from tasks.models import Task


class DashboardService:
    """Service pour les calculs du dashboard admin."""
    
    @staticmethod
    def get_kpis() -> dict:
        """
        Calcule les KPIs principaux pour le dashboard.
        
        Returns:
            dict: KPIs avec clés:
                - total_revenue: CA total (toutes les factures payées)
                - monthly_revenue: CA du mois en cours
                - pending_revenue: CA en attente (factures envoyées non payées)
                - overdue_amount: Montant impayé (factures en retard)
                - conversion_rate: Taux de conversion devis (acceptés / envoyés)
        """
        # CA total (toutes les factures payées)
        total_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        # CA du mois en cours
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
            issue_date__gte=current_month
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        # CA en attente (factures envoyées non payées)
        pending_revenue = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        # Montant impayé (factures en retard)
        overdue_amount = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.OVERDUE
        ).aggregate(
            total=Sum('total_ttc')
        )['total'] or Decimal('0.00')
        
        # Taux de conversion devis
        sent_quotes = Quote.objects.filter(status=Quote.QuoteStatus.SENT).count()
        accepted_quotes = Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count()
        total_sent_or_accepted = sent_quotes + accepted_quotes
        conversion_rate = (accepted_quotes / total_sent_or_accepted * 100) if total_sent_or_accepted > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'pending_revenue': pending_revenue,
            'overdue_amount': overdue_amount,
            'conversion_rate': round(conversion_rate, 1),
        }
    
    @staticmethod
    def get_recent_quotes(limit: int = 5):
        """
        Retourne les devis récents.
        
        Args:
            limit: Nombre de devis à retourner
            
        Returns:
            QuerySet: Devis récents
        """
        return Quote.objects.select_related(
            'client', 'service'
        ).order_by('-issue_date', '-created_at')[:limit]
    
    @staticmethod
    def get_recent_invoices(limit: int = 5):
        """
        Retourne les factures récentes.
        
        Args:
            limit: Nombre de factures à retourner
            
        Returns:
            QuerySet: Factures récentes
        """
        return Invoice.objects.select_related(
            'quote', 'quote__client'
        ).order_by('-issue_date', '-created_at')[:limit]
    
    @staticmethod
    def get_today_tasks():
        """
        Retourne les tâches du jour (à venir + en cours).
        
        Returns:
            QuerySet: Tâches du jour
        """
        today = timezone.now().date()
        
        return Task.objects.filter(
            Q(start_date=today) | Q(due_date=today),
            status__in=[Task.STATUS_UPCOMING, Task.STATUS_IN_PROGRESS]
        ).select_related(
            'assigned_to'
        ).order_by('start_date', 'due_date')
    
    @staticmethod
    def get_revenue_trend(months: int = 12) -> list:
        """
        Calcule la tendance du CA sur les N derniers mois.
        
        Args:
            months: Nombre de mois à analyser
            
        Returns:
            list: Liste de dicts avec 'month' et 'revenue'
        """
        trend = []
        current_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(months):
            month_start = current_date - timedelta(days=30 * i)
            # Ajuster au premier jour du mois
            month_start = month_start.replace(day=1)
            # Calculer le mois suivant
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            revenue = Invoice.objects.filter(
                status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
                issue_date__gte=month_start,
                issue_date__lt=month_end
            ).aggregate(
                total=Sum('total_ttc')
            )['total'] or Decimal('0.00')
            
            trend.insert(0, {
                'month': month_start.strftime('%Y-%m'),
                'month_label': month_start.strftime('%b %Y'),
                'revenue': float(revenue),
            })
        
        return trend
    
    @staticmethod
    def get_status_distributions() -> dict:
        """
        Retourne la répartition des statuts pour devis, factures et tâches.
        
        Returns:
            dict: Distributions avec clés:
                - quote_status_counts: {status: count}
                - invoice_status_counts: {status: count}
                - task_status_counts: {status: count}
        """
        # Devis
        quote_status_counts = {}
        for status, _ in Quote.QuoteStatus.choices:
            quote_status_counts[status] = Quote.objects.filter(status=status).count()
        
        # Factures
        invoice_status_counts = {}
        for status, _ in Invoice.InvoiceStatus.choices:
            invoice_status_counts[status] = Invoice.objects.filter(status=status).count()
        
        # Tâches
        task_status_counts = {}
        for status, _ in Task.STATUS_CHOICES:
            task_status_counts[status] = Task.objects.filter(status=status).count()
        
        return {
            'quote_status_counts': quote_status_counts,
            'invoice_status_counts': invoice_status_counts,
            'task_status_counts': task_status_counts,
        }
    
    @staticmethod
    def get_worker_performance(limit: int = 5) -> list:
        """
        Retourne les performances des workers (top N).
        
        Args:
            limit: Nombre de workers à retourner
            
        Returns:
            list: Liste de dicts avec worker et statistiques
        """
        from accounts.models import Profile
        
        workers = User.objects.filter(
            profile__role=Profile.ROLE_WORKER,
            is_active=True
        ).annotate(
            total_tasks=Count('assigned_tasks'),
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status=Task.STATUS_COMPLETED)),
            overdue_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status=Task.STATUS_OVERDUE))
        ).order_by('-completed_tasks')[:limit]
        
        worker_stats = []
        for worker in workers:
            completion_rate = (worker.completed_tasks / worker.total_tasks * 100) if worker.total_tasks > 0 else 0
            worker_stats.append({
                'worker': worker,
                'total_tasks': worker.total_tasks,
                'completed_tasks': worker.completed_tasks,
                'overdue_tasks': worker.overdue_tasks,
                'completion_rate': round(completion_rate, 1),
            })
        
        return worker_stats

