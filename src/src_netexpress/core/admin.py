"""
Configuration personnalisée pour Django Admin avec dashboard intégré.
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.contrib.auth.models import User

from devis.models import Quote, Client
from factures.models import Invoice
from tasks.models import Task
from messaging.models import EmailMessage


class CustomAdminSite(admin.AdminSite):
    """AdminSite personnalisé avec dashboard intégré."""
    
    site_header = "Nettoyage Express Administration"
    site_title = "NetExpress Admin"
    index_title = "Dashboard Administrateur"
    index_template = 'admin/dashboard.html'
    
    def get_urls(self):
        """Ajouter la route dashboard personnalisée."""
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.admin_dashboard_view), name='index'),
        ]
        return custom_urls + urls
    
    @staff_member_required
    def admin_dashboard_view(self, request):
        """
        Dashboard personnalisé pour l'interface Django Admin (/gestion/).
        Affiche des KPIs, une vision globale et des actions rapides.
        """
        from django.db.models import Sum, Count, Q
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        # Calculate revenue metrics
        total_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL]
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        # Monthly revenue (current month)
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
            issue_date__gte=current_month
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        # Pending revenue (sent but not paid invoices)
        pending_revenue = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT
        ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
        
        # Quote conversion rate
        total_quotes = Quote.objects.count()
        accepted_quotes = Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count()
        conversion_rate = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0
        
        # Task performance metrics
        total_tasks = Task.objects.count()
        completed_tasks = Task.objects.filter(status=Task.STATUS_COMPLETED).count()
        overdue_tasks = Task.objects.filter(status=Task.STATUS_OVERDUE).count()
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Worker performance
        workers = User.objects.filter(groups__name='Workers')
        worker_stats = []
        for worker in workers[:5]:  # Top 5 workers
            worker_tasks = Task.objects.filter(assigned_to=worker)
            completed = worker_tasks.filter(status=Task.STATUS_COMPLETED).count()
            total = worker_tasks.count()
            completion_rate = (completed / total * 100) if total > 0 else 0
            worker_stats.append({
                'worker': worker,
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': completion_rate,
                'overdue_tasks': worker_tasks.filter(status=Task.STATUS_OVERDUE).count()
            })
        
        # Recent activity
        recent_quotes = Quote.objects.order_by('-created_at')[:5]
        recent_invoices = Invoice.objects.order_by('-created_at')[:5]
        recent_tasks = Task.objects.order_by('-created_at')[:5]
        recent_messages = EmailMessage.objects.order_by('-created_at')[:5]
        
        # Status distributions
        quote_status_counts = {
            'draft': Quote.objects.filter(status=Quote.QuoteStatus.DRAFT).count(),
            'sent': Quote.objects.filter(status=Quote.QuoteStatus.SENT).count(),
            'accepted': Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count(),
            'rejected': Quote.objects.filter(status=Quote.QuoteStatus.REJECTED).count(),
        }
        
        invoice_status_counts = {
            'draft': Invoice.objects.filter(status=Invoice.InvoiceStatus.DRAFT).count(),
            'sent': Invoice.objects.filter(status=Invoice.InvoiceStatus.SENT).count(),
            'paid': Invoice.objects.filter(status=Invoice.InvoiceStatus.PAID).count(),
            'overdue': Invoice.objects.filter(status=Invoice.InvoiceStatus.OVERDUE).count(),
        }
        
        task_status_counts = {
            'upcoming': Task.objects.filter(status=Task.STATUS_UPCOMING).count(),
            'in_progress': Task.objects.filter(status=Task.STATUS_IN_PROGRESS).count(),
            'completed': Task.objects.filter(status=Task.STATUS_COMPLETED).count(),
            'overdue': Task.objects.filter(status=Task.STATUS_OVERDUE).count(),
        }
        
        # Quick actions
        quick_actions = [
            {
                'title': 'Nouveau Devis',
                'url': '/gestion/devis/quote/add/',
                'icon': 'fas fa-file-alt',
                'color': 'primary'
            },
            {
                'title': 'Nouvelle Facture',
                'url': '/gestion/factures/invoice/add/',
                'icon': 'fas fa-receipt',
                'color': 'success'
            },
            {
                'title': 'Nouvelle Tâche',
                'url': '/gestion/tasks/task/add/',
                'icon': 'fas fa-tasks',
                'color': 'info'
            },
            {
                'title': 'Nouveau Client',
                'url': '/gestion/devis/client/add/',
                'icon': 'fas fa-user-plus',
                'color': 'warning'
            },
            {
                'title': 'Nouveau Message',
                'url': '/gestion/messaging/emailmessage/add/',
                'icon': 'fas fa-envelope',
                'color': 'secondary'
            },
            {
                'title': 'Dashboard Business',
                'url': '/admin-dashboard/',
                'icon': 'fas fa-chart-line',
                'color': 'dark'
            },
        ]
        
        context = {
            'title': 'Dashboard Administrateur',
            'has_permission': True,
            'site_header': self.site_header,
            'site_title': self.site_title,
            'has_absolute_url': False,
            
            # KPI Metrics
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'pending_revenue': pending_revenue,
            'conversion_rate': conversion_rate,
            'task_completion_rate': task_completion_rate,
            
            # Worker Performance
            'worker_stats': worker_stats,
            'total_workers': workers.count(),
            
            # Recent Activity
            'recent_quotes': recent_quotes,
            'recent_invoices': recent_invoices,
            'recent_tasks': recent_tasks,
            'recent_messages': recent_messages,
            
            # Status Distributions
            'quote_status_counts': quote_status_counts,
            'invoice_status_counts': invoice_status_counts,
            'task_status_counts': task_status_counts,
            
            # Totals
            'total_quotes': total_quotes,
            'total_invoices': Invoice.objects.count(),
            'total_tasks': total_tasks,
            'overdue_tasks': overdue_tasks,
            
            # Quick Actions
            'quick_actions': quick_actions,
        }
        
        # Add admin site context
        context.update(self.each_context(request))
        
        return render(request, 'admin/dashboard.html', context)


# Personnaliser l'index admin avec notre template dashboard
# Django Admin utilisera automatiquement ce template pour la page d'accueil
admin.site.index_template = 'admin/dashboard.html'
admin.site.index_title = 'Dashboard Administrateur'
