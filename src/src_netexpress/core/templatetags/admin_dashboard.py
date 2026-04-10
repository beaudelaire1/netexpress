"""
Template tags pour le dashboard admin personnalisé.
"""

from django import template
from django.urls import reverse
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User

from devis.models import Quote
from factures.models import Invoice
from tasks.models import Task
from messaging.models import EmailMessage

register = template.Library()


@register.inclusion_tag('admin/dashboard_kpis.html', takes_context=True)
def dashboard_kpis(context):
    """Afficher les KPIs du dashboard."""
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
    
    # Pending revenue
    pending_revenue = Invoice.objects.filter(
        status=Invoice.InvoiceStatus.SENT
    ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
    
    # Quote conversion rate
    total_quotes = Quote.objects.count()
    accepted_quotes = Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count()
    conversion_rate = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0
    
    # Task performance
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status=Task.STATUS_COMPLETED).count()
    overdue_tasks = Task.objects.filter(status=Task.STATUS_OVERDUE).count()
    task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'pending_revenue': pending_revenue,
        'conversion_rate': conversion_rate,
        'task_completion_rate': task_completion_rate,
        'overdue_tasks': overdue_tasks,
        'total_quotes': total_quotes,
        'total_invoices': Invoice.objects.count(),
        'total_tasks': total_tasks,
    }


@register.inclusion_tag('admin/dashboard_quick_actions.html')
def dashboard_quick_actions():
    """Afficher les actions rapides."""
    return {
        'quick_actions': [
            {
                'title': 'Nouveau Devis',
                'url': reverse('core:admin_create_quote'),
                'icon': 'fas fa-file-alt',
                'color': 'primary'
            },
            {
                'title': 'Nouvelle Facture',
                'url': reverse('core:admin_create_invoice'),
                'icon': 'fas fa-receipt',
                'color': 'success'
            },
            {
                'title': 'Nouvelle Tâche',
                'url': reverse('core:admin_create_task'),
                'icon': 'fas fa-tasks',
                'color': 'info'
            },
            {
                'title': 'Nouveau Client',
                'url': reverse('core:admin_create_client'),
                'icon': 'fas fa-user-plus',
                'color': 'warning'
            },
            {
                'title': 'Dashboard Business',
                'url': reverse('core:admin_dashboard'),
                'icon': 'fas fa-chart-line',
                'color': 'dark'
            },
        ]
    }


@register.inclusion_tag('admin/dashboard_recent_activity.html')
def dashboard_recent_activity():
    """Afficher l'activité récente."""
    return {
        'recent_quotes': Quote.objects.order_by('-created_at')[:5],
        'recent_invoices': Invoice.objects.order_by('-created_at')[:5],
        'recent_tasks': Task.objects.order_by('-created_at')[:5],
    }

