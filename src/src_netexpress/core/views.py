"""Vues principales de l'application ``core``.

Ces vues fournissent :
  - une page d'accueil marketing utilisant le thème existant ;
  - une page "à propos" statique ;
  - un endpoint de santé JSON pour le monitoring ;
  - un tableau de bord agrégé pour le back‑office.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone

from services.models import Service, Category
from devis.models import Quote, Client
from factures.models import Invoice
from tasks.models import Task
from messaging.models import EmailMessage
from .services.document_service import ClientDocumentService
from .decorators import client_portal_required, worker_portal_required, admin_portal_required


def home(request):
    """Page d'accueil publique."""
    categories = Category.objects.all().order_by("name")
    featured_services = (
        Service.objects.filter(is_active=True)
        .order_by("-created_at")[:6]
    )
    return render(
        request,
        "core/home.html",
        {
            "categories": categories,
            "featured_services": featured_services,
        },
    )


def about(request):
    """Page de présentation de l'entreprise."""
    return render(request, "core/about.html")


def excellence(request):
    """
    Page de mise en avant des engagements de l'entreprise.

    Cette vue ne nécessite pas de logique complexe ; elle se contente
    d'afficher un template statique décrivant les valeurs et la
    philosophie de NetExpress.
    """
    return render(request, "core/excellence.html")


def realisations(request):
    """
    Galerie des réalisations.  Les images sont définies statiquement
    car aucune base de données n'est prévue pour cette page dans le
    cahier des charges.  Chaque entrée contient une URL distante
    hébergée par Unsplash, un titre et une catégorie pour le filtrage
    côté client.
    """
    # Images locales (pas d'URL externes) pour éviter les liens morts et
    # améliorer la fiabilité/perf.  Ce jeu d'images est provisoire :
    # l'utilisateur pourra remplacer les fichiers dans static/img/realisations/.
    images = [
        {"path": "img/realisations/espaces_verts_1.jpg", "title": "Villa Montjoly", "category": "espaces_verts"},
        {"path": "img/realisations/nettoyage_1.jpg", "title": "Résidence Kourou", "category": "nettoyage"},
        {"path": "img/realisations/renovation_1.png", "title": "Appartement Cayenne", "category": "renovation"},
        {"path": "img/realisations/espaces_verts_2.jpg", "title": "Jardin Tropical Remire", "category": "espaces_verts"},
        {"path": "img/realisations/nettoyage_2.jpg", "title": "Bureaux Centre-ville", "category": "nettoyage"},
        {"path": "img/realisations/renovation_2.png", "title": "Rafraîchissement Peinture", "category": "renovation"},
    ]
    categories = [
        ("all", "Toutes"),
        ("nettoyage", "Nettoyage"),
        ("espaces_verts", "Espaces verts"),
        ("renovation", "Rénovation"),
    ]
    return render(
        request,
        "core/realisations.html",
        {
            "images": images,
            "categories": categories,
        },
    )


def health(request):
    """Endpoint simple pour les probes de monitoring."""
    return JsonResponse({"status": "ok"})


# Dashboard technique supprimé - Migration vers /admin-dashboard/
# Les fonctionnalités sont maintenant disponibles dans admin_dashboard()
# Les superusers et admins techniques accèdent à /gestion/ (Django Admin)
# Les admins business accèdent à /admin-dashboard/


@client_portal_required
def client_dashboard(request):
    """Enhanced Client Portal dashboard with document filtering."""
    # Update last portal access
    if hasattr(request.user, 'profile'):
        from django.utils import timezone
        request.user.profile.last_portal_access = timezone.now()
        request.user.profile.save(update_fields=['last_portal_access'])
    
    # Get document statistics and recent documents using the service
    stats = ClientDocumentService.get_client_document_stats(request.user)
    recent_docs = ClientDocumentService.get_recent_documents(request.user, limit=5)
    
    # Get all documents for the sidebar links
    all_quotes = ClientDocumentService.get_accessible_quotes(request.user).order_by("-issue_date")
    all_invoices = ClientDocumentService.get_accessible_invoices(request.user).order_by("-issue_date")
    
    return TemplateResponse(
        request,
        "core/client_dashboard.html",
        {
            "pending_quotes": recent_docs['quotes'],
            "unpaid_invoices": recent_docs['invoices'],
            "all_quotes": all_quotes,
            "all_invoices": all_invoices,
            "stats": stats,
        },
    )


@client_portal_required
def client_quotes(request):
    """Client Portal quotes list view."""
    quotes = ClientDocumentService.get_accessible_quotes(request.user).order_by("-issue_date")
    
    return TemplateResponse(
        request,
        "core/client_quotes.html",
        {"quotes": quotes},
    )


@client_portal_required
def client_invoices(request):
    """Client Portal invoices list view."""
    invoices = ClientDocumentService.get_accessible_invoices(request.user).order_by("-issue_date")
    
    return TemplateResponse(
        request,
        "core/client_invoices.html",
        {"invoices": invoices},
    )


@client_portal_required
def client_quote_detail(request, pk):
    """Client Portal quote detail view."""
    # Get the quote and check access
    quote = get_object_or_404(Quote, pk=pk)
    
    if not ClientDocumentService.can_access_quote(request.user, quote):
        return TemplateResponse(request, "core/access_denied.html", {"target": "quote"}, status=403)
    
    # Track document access
    ClientDocumentService.track_document_access(request.user, quote=quote)
    
    return TemplateResponse(
        request,
        "core/client_quote_detail.html",
        {"quote": quote},
    )


@client_portal_required
def client_invoice_detail(request, pk):
    """Client Portal invoice detail view."""
    # Get the invoice and check access
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if not ClientDocumentService.can_access_invoice(request.user, invoice):
        return TemplateResponse(request, "core/access_denied.html", {"target": "invoice"}, status=403)
    
    # Track document access
    ClientDocumentService.track_document_access(request.user, invoice=invoice)
    
    return TemplateResponse(
        request,
        "core/client_invoice_detail.html",
        {"invoice": invoice},
    )


@client_portal_required
def client_quote_validate_start(request, pk):
    """Client Portal quote validation initiation."""
    # Get the quote and check access
    quote = get_object_or_404(Quote, pk=pk)
    
    if not ClientDocumentService.can_access_quote(request.user, quote):
        return TemplateResponse(request, "core/access_denied.html", {"target": "quote"}, status=403)
    
    # Create validation and send code (use-case layer)
    from devis.application.quote_validation import QuoteNotValidatableError, start_quote_validation

    try:
        res = start_quote_validation(quote, request=request)
        validation = res.validation
    except QuoteNotValidatableError:
        return TemplateResponse(
            request,
            "core/client_quote_detail.html",
            {"quote": quote, "error_message": "Ce devis ne peut pas être validé dans son état actuel."},
        )
    
    return TemplateResponse(
        request,
        "core/client_quote_validate_code.html",
        {
            "quote": quote,
            "validation": validation,
            "success_message": "Un code de validation a été envoyé à votre adresse email."
        },
    )


@client_portal_required
def client_quote_validate_code(request, pk):
    """Client Portal quote validation code verification."""
    # Get the quote and check access
    quote = get_object_or_404(Quote, pk=pk)
    
    if not ClientDocumentService.can_access_quote(request.user, quote):
        return TemplateResponse(request, "core/access_denied.html", {"target": "quote"}, status=403)
    
    # Get the most recent validation for this quote (use-case helper)
    from devis.application.quote_validation import get_pending_validation_for_quote
    from devis.models import QuoteValidation

    try:
        validation = get_pending_validation_for_quote(quote)
    except QuoteValidation.DoesNotExist:
        return TemplateResponse(
            request,
            "core/client_quote_detail.html",
            {
                "quote": quote,
                "error_message": "Aucune validation en cours pour ce devis."
            }
        )
    
    if validation.is_expired:
        return TemplateResponse(
            request,
            "core/client_quote_validate_expired.html",
            {"quote": quote, "validation": validation}
        )
    
    if request.method == "POST":
        from devis.forms import QuoteValidationCodeForm
        from devis.application.quote_validation import QuoteValidationExpiredError, confirm_quote_validation_code

        form = QuoteValidationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                ok = confirm_quote_validation_code(validation=validation, submitted_code=code)
            except QuoteValidationExpiredError:
                return TemplateResponse(
                    request,
                    "core/client_quote_validate_expired.html",
                    {"quote": quote, "validation": validation},
                )

            if ok:
                return TemplateResponse(
                    request,
                    "core/client_quote_validate_success.html",
                    {"quote": quote},
                )

            form.add_error("code", "Code incorrect. Veuillez réessayer.")
    else:
        from devis.forms import QuoteValidationCodeForm
        form = QuoteValidationCodeForm()
    
    return TemplateResponse(
        request,
        "core/client_quote_validate_code.html",
        {
            "quote": quote,
            "validation": validation,
            "form": form,
        },
    )


@worker_portal_required
def worker_dashboard(request):
    """Tableau de bord ouvrier (tâches assignées à l'utilisateur connecté)."""
    # Filter tasks by assigned worker (new approach)
    user_tasks = Task.objects.filter(assigned_to=request.user).order_by('due_date', 'start_date')
    
    # Separate tasks by status for better organization
    upcoming_tasks = user_tasks.filter(status=Task.STATUS_UPCOMING)
    in_progress_tasks = user_tasks.filter(status=Task.STATUS_IN_PROGRESS)
    almost_overdue_tasks = user_tasks.filter(status=Task.STATUS_ALMOST_OVERDUE)
    overdue_tasks = user_tasks.filter(status=Task.STATUS_OVERDUE)
    completed_tasks = user_tasks.filter(status=Task.STATUS_COMPLETED)[:10]  # Show last 10 completed
    
    return render(
        request,
        "core/worker_dashboard.html",
        {
            "upcoming_tasks": upcoming_tasks,
            "in_progress_tasks": in_progress_tasks,
            "almost_overdue_tasks": almost_overdue_tasks,
            "overdue_tasks": overdue_tasks,
            "completed_tasks": completed_tasks,
            "total_assigned": user_tasks.count(),
            "pending_tasks": user_tasks.exclude(status=Task.STATUS_COMPLETED).count(),
        },
    )


@admin_portal_required
def admin_dashboard(request):
    """Admin Portal dashboard with KPIs and performance metrics."""
    from decimal import Decimal
    from django.db.models import Sum, Count, Q, Prefetch
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.contrib.auth.models import User
    from django.core.cache import cache
    import json
    
    # Cache key for dashboard data (5 minutes cache)
    cache_key = 'admin_dashboard_data'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        # Calculate revenue metrics with optimized queries
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
        
        # Quote conversion rate - optimized with single query
        quote_stats = Quote.objects.aggregate(
            total=Count('id'),
            accepted=Count('id', filter=Q(status=Quote.QuoteStatus.ACCEPTED))
        )
        total_quotes = quote_stats['total']
        accepted_quotes = quote_stats['accepted']
        conversion_rate = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0
        
        # Task performance metrics - optimized
        task_stats = Task.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status=Task.STATUS_COMPLETED)),
            overdue=Count('id', filter=Q(status=Task.STATUS_OVERDUE))
        )
        total_tasks = task_stats['total']
        completed_tasks = task_stats['completed']
        overdue_tasks = task_stats['overdue']
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Worker performance - optimized with prefetch
        workers = User.objects.filter(groups__name='Workers').prefetch_related(
            Prefetch('task_set', queryset=Task.objects.all(), to_attr='all_tasks')
        )
        worker_stats = []
        for worker in workers:
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
        
        # Recent activity - optimized with select_related
        recent_quotes = Quote.objects.select_related('client', 'service').order_by('-created_at')[:5]
        recent_invoices = Invoice.objects.select_related('quote', 'quote__client').order_by('-created_at')[:5]
        recent_tasks = Task.objects.select_related('assigned_to').order_by('-created_at')[:5]
        
        # Status distributions - optimized with single aggregation
        quote_status_counts = dict(
            Quote.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        quote_status_counts = {
            'draft': quote_status_counts.get(Quote.QuoteStatus.DRAFT, 0),
            'sent': quote_status_counts.get(Quote.QuoteStatus.SENT, 0),
            'accepted': quote_status_counts.get(Quote.QuoteStatus.ACCEPTED, 0),
            'rejected': quote_status_counts.get(Quote.QuoteStatus.REJECTED, 0),
        }
        
        invoice_status_counts = dict(
            Invoice.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        invoice_status_counts = {
            'draft': invoice_status_counts.get(Invoice.InvoiceStatus.DRAFT, 0),
            'sent': invoice_status_counts.get(Invoice.InvoiceStatus.SENT, 0),
            'paid': invoice_status_counts.get(Invoice.InvoiceStatus.PAID, 0),
            'overdue': invoice_status_counts.get(Invoice.InvoiceStatus.OVERDUE, 0),
        }
        
        task_status_counts = dict(
            Task.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        task_status_counts = {
            'upcoming': task_status_counts.get(Task.STATUS_UPCOMING, 0),
            'in_progress': task_status_counts.get(Task.STATUS_IN_PROGRESS, 0),
            'completed': task_status_counts.get(Task.STATUS_COMPLETED, 0),
            'overdue': task_status_counts.get(Task.STATUS_OVERDUE, 0),
        }
        
        # Revenue trend (last 6 months) - optimized
        revenue_trend = []
        for i in range(6):
            month_start = (current_month - timedelta(days=30*i)).replace(day=1)
            if i == 0:
                month_end = timezone.now().date()
            else:
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            month_revenue = Invoice.objects.filter(
                status__in=[Invoice.InvoiceStatus.PAID, Invoice.InvoiceStatus.PARTIAL],
                issue_date__gte=month_start,
                issue_date__lte=month_end
            ).aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')
            revenue_trend.append({
                'month': month_start.strftime('%Y-%m'),
                'revenue': float(month_revenue)
            })
        revenue_trend.reverse()
        
        # Store only serializable data in cache
        cached_data = {
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'pending_revenue': float(pending_revenue),
            'conversion_rate': float(conversion_rate),
            'task_completion_rate': float(task_completion_rate),
            'worker_stats': [
                {
                    'worker_id': ws['worker'].id,
                    'worker_name': ws['worker'].get_full_name() or ws['worker'].username,
                    'total_tasks': ws['total_tasks'],
                    'completed_tasks': ws['completed_tasks'],
                    'completion_rate': float(ws['completion_rate']),
                    'overdue_tasks': ws['overdue_tasks']
                }
                for ws in worker_stats
            ],
            'recent_quotes_ids': [q.id for q in recent_quotes],
            'recent_invoices_ids': [i.id for i in recent_invoices],
            'recent_tasks_ids': [t.id for t in recent_tasks],
            'quote_status_counts': quote_status_counts,
            'invoice_status_counts': invoice_status_counts,
            'task_status_counts': task_status_counts,
            'total_quotes': total_quotes,
            'total_invoices': Invoice.objects.count(),
            'total_tasks': total_tasks,
            'overdue_tasks': overdue_tasks,
            'revenue_trend': revenue_trend,
            'revenue_trend_json': json.dumps(revenue_trend),
        }
        cache.set(cache_key, cached_data, 300)  # Cache for 5 minutes
        
        # Keep querysets for template rendering
        recent_quotes_qs = recent_quotes
        recent_invoices_qs = recent_invoices
        recent_tasks_qs = recent_tasks
        worker_stats_list = worker_stats
        revenue_trend_json = cached_data['revenue_trend_json']
    else:
        # Restore querysets from cached IDs
        recent_quotes_qs = Quote.objects.filter(
            pk__in=cached_data['recent_quotes_ids']
        ).select_related('client', 'service').order_by('-created_at')
        recent_invoices_qs = Invoice.objects.filter(
            pk__in=cached_data['recent_invoices_ids']
        ).select_related('quote', 'quote__client').order_by('-created_at')
        recent_tasks_qs = Task.objects.filter(
            pk__in=cached_data['recent_tasks_ids']
        ).select_related('assigned_to').order_by('-created_at')
        
        # Restore worker stats with user objects
        worker_stats_list = []
        for ws_data in cached_data['worker_stats']:
            try:
                worker = User.objects.get(pk=ws_data['worker_id'])
                worker_stats_list.append({
                    'worker': worker,
                    'total_tasks': ws_data['total_tasks'],
                    'completed_tasks': ws_data['completed_tasks'],
                    'completion_rate': ws_data['completion_rate'],
                    'overdue_tasks': ws_data['overdue_tasks']
                })
            except User.DoesNotExist:
                continue
        
        # Get revenue trend JSON
        revenue_trend_json = cached_data.get('revenue_trend_json', json.dumps(cached_data.get('revenue_trend', [])))
    
    return render(
        request,
        "core/admin_dashboard.html",
        {
            # KPI Metrics
            'total_revenue': Decimal(str(cached_data['total_revenue'])),
            'monthly_revenue': Decimal(str(cached_data['monthly_revenue'])),
            'pending_revenue': Decimal(str(cached_data['pending_revenue'])),
            'conversion_rate': cached_data['conversion_rate'],
            'task_completion_rate': cached_data['task_completion_rate'],
            
            # Worker Performance
            'worker_stats': worker_stats_list,
            'total_workers': len(worker_stats_list),
            
            # Recent Activity
            'recent_quotes': recent_quotes_qs,
            'recent_invoices': recent_invoices_qs,
            'recent_tasks': recent_tasks_qs,
            
            # Status Distributions
            'quote_status_counts': cached_data['quote_status_counts'],
            'invoice_status_counts': cached_data['invoice_status_counts'],
            'task_status_counts': cached_data['task_status_counts'],
            
            # Totals
            'total_quotes': cached_data['total_quotes'],
            'total_invoices': cached_data['total_invoices'],
            'total_tasks': cached_data['total_tasks'],
            'overdue_tasks': cached_data['overdue_tasks'],
            
            # Revenue Trend for Charts (as JSON string for template)
            'revenue_trend': cached_data['revenue_trend'],
            'revenue_trend_json': revenue_trend_json,
        },
    )


@admin_portal_required
def admin_global_planning(request):
    """Admin Portal global planning view showing all workers and tasks."""
    from django.contrib.auth.models import User
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Get all workers
    workers = User.objects.filter(groups__name='Workers').order_by('first_name', 'last_name')
    
    # Get date range for planning (default to current week)
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Allow filtering by date range via GET parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = start_of_week
    else:
        start_date = start_of_week
        
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = end_of_week
    else:
        end_date = end_of_week
    
    # Get all tasks in the date range
    all_tasks = Task.objects.filter(
        start_date__lte=end_date,
        due_date__gte=start_date
    ).order_by('start_date', 'due_date')
    
    # Organize tasks by worker
    worker_planning = []
    for worker in workers:
        worker_tasks = all_tasks.filter(assigned_to=worker)
        
        # Categorize tasks by status
        upcoming = worker_tasks.filter(status=Task.STATUS_UPCOMING)
        in_progress = worker_tasks.filter(status=Task.STATUS_IN_PROGRESS)
        completed = worker_tasks.filter(status=Task.STATUS_COMPLETED)
        overdue = worker_tasks.filter(status=Task.STATUS_OVERDUE)
        almost_overdue = worker_tasks.filter(status=Task.STATUS_ALMOST_OVERDUE)
        
        worker_planning.append({
            'worker': worker,
            'total_tasks': worker_tasks.count(),
            'upcoming_tasks': upcoming,
            'in_progress_tasks': in_progress,
            'completed_tasks': completed,
            'overdue_tasks': overdue,
            'almost_overdue_tasks': almost_overdue,
            'workload_percentage': min(100, (worker_tasks.count() * 10))  # Simple workload calculation
        })
    
    # Get unassigned tasks
    unassigned_tasks = all_tasks.filter(assigned_to__isnull=True)
    
    # Summary statistics
    total_tasks_in_period = all_tasks.count()
    assigned_tasks = all_tasks.filter(assigned_to__isnull=False).count()
    unassigned_count = unassigned_tasks.count()
    
    # Task distribution by status
    status_distribution = {
        'upcoming': all_tasks.filter(status=Task.STATUS_UPCOMING).count(),
        'in_progress': all_tasks.filter(status=Task.STATUS_IN_PROGRESS).count(),
        'completed': all_tasks.filter(status=Task.STATUS_COMPLETED).count(),
        'overdue': all_tasks.filter(status=Task.STATUS_OVERDUE).count(),
        'almost_overdue': all_tasks.filter(status=Task.STATUS_ALMOST_OVERDUE).count(),
    }
    
    return render(
        request,
        "core/admin_global_planning.html",
        {
            'worker_planning': worker_planning,
            'unassigned_tasks': unassigned_tasks,
            'start_date': start_date,
            'end_date': end_date,
            'total_workers': workers.count(),
            'total_tasks_in_period': total_tasks_in_period,
            'assigned_tasks': assigned_tasks,
            'unassigned_count': unassigned_count,
            'status_distribution': status_distribution,
            'all_tasks': all_tasks,  # For comprehensive view
        },
    )


# Admin Portal Management Views

@admin_portal_required
def admin_create_worker(request):
    """Admin Portal worker creation view."""
    from .forms import WorkerCreationForm
    
    if request.method == 'POST':
        form = WorkerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Ouvrier {user.get_full_name()} créé avec succès!")
            return redirect('core:admin_dashboard')
    else:
        form = WorkerCreationForm()
    
    return render(request, 'core/admin_create_worker.html', {'form': form})


@admin_portal_required
def admin_create_client(request):
    """Admin Portal client creation view."""
    from .forms import ClientCreationForm
    
    if request.method == 'POST':
        form = ClientCreationForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client {client.full_name} créé avec succès!")
            return redirect('core:admin_dashboard')
    else:
        form = ClientCreationForm()
    
    return render(request, 'core/admin_create_client.html', {'form': form})


@admin_portal_required
def admin_create_quote(request):
    """Admin Portal quote creation view."""
    from .forms import QuoteCreationForm
    
    if request.method == 'POST':
        form = QuoteCreationForm(request.POST)
        if form.is_valid():
            quote = form.save()
            messages.success(request, f"Devis {quote.number} créé avec succès!")
            return redirect('core:admin_dashboard')
    else:
        form = QuoteCreationForm()
    
    return render(request, 'core/admin_create_quote.html', {'form': form})


@admin_portal_required
def admin_create_task(request):
    """Admin Portal task creation view."""
    from .forms import TaskCreationForm
    
    if request.method == 'POST':
        form = TaskCreationForm(request.POST)
        if form.is_valid():
            task = form.save()
            messages.success(request, f"Tâche '{task.title}' créée avec succès!")
            return redirect('core:admin_dashboard')
    else:
        form = TaskCreationForm()
    
    return render(request, 'core/admin_create_task.html', {'form': form})


@admin_portal_required
def admin_workers_list(request):
    """Admin Portal workers management view with optimized queries."""
    from django.contrib.auth.models import User
    from django.db.models import Count, Q, Prefetch
    from django.core.paginator import Paginator
    
    workers = User.objects.filter(groups__name='Workers').order_by('first_name', 'last_name')
    
    # Optimize with prefetch and annotations
    workers = workers.prefetch_related(
        Prefetch('task_set', queryset=Task.objects.all(), to_attr='all_tasks')
    ).annotate(
        total_tasks=Count('task_set'),
        completed_tasks=Count('task_set', filter=Q(task_set__status=Task.STATUS_COMPLETED)),
        overdue_tasks=Count('task_set', filter=Q(task_set__status=Task.STATUS_OVERDUE))
    )
    
    # Add task statistics for each worker
    workers_with_stats = []
    for worker in workers:
        workers_with_stats.append({
            'worker': worker,
            'total_tasks': worker.total_tasks,
            'completed_tasks': worker.completed_tasks,
            'pending_tasks': worker.total_tasks - worker.completed_tasks,
            'overdue_tasks': worker.overdue_tasks,
        })
    
    # Pagination
    paginator = Paginator(workers_with_stats, 20)  # 20 workers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/admin_workers_list.html', {
        'workers_with_stats': page_obj,
        'page_obj': page_obj
    })


@admin_portal_required
def admin_clients_list(request):
    """Admin Portal clients management view with optimized queries."""
    from django.db.models import Count, Q
    from django.core.paginator import Paginator
    
    clients = Client.objects.all().order_by('full_name')
    
    # Optimize with annotations
    clients = clients.annotate(
        total_quotes=Count('quote'),
        accepted_quotes=Count('quote', filter=Q(quote__status=Quote.QuoteStatus.ACCEPTED)),
        pending_quotes=Count('quote', filter=Q(quote__status=Quote.QuoteStatus.SENT))
    )
    
    # Add statistics for each client
    clients_with_stats = []
    for client in clients:
        clients_with_stats.append({
            'client': client,
            'total_quotes': client.total_quotes,
            'accepted_quotes': client.accepted_quotes,
            'pending_quotes': client.pending_quotes,
        })
    
    # Pagination
    paginator = Paginator(clients_with_stats, 25)  # 25 clients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/admin_clients_list.html', {
        'clients_with_stats': page_obj,
        'page_obj': page_obj
    })


@admin_portal_required
def admin_create_invoice(request):
    """Admin Portal invoice creation view."""
    from .forms import InvoiceCreationForm
    
    if request.method == 'POST':
        form = InvoiceCreationForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            messages.success(request, f"Facture {invoice.number} créée avec succès!")
            return redirect('core:admin_invoices_list')
    else:
        form = InvoiceCreationForm()
    
    return render(request, 'core/admin_create_invoice.html', {'form': form})


@admin_portal_required
def admin_invoices_list(request):
    """Admin Portal invoices management view with pagination."""
    from django.core.paginator import Paginator
    
    invoices = Invoice.objects.select_related('quote', 'quote__client').order_by('-issue_date')
    paginator = Paginator(invoices, 25)  # 25 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/admin_invoices_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj
    })


@admin_portal_required
def admin_quotes_list(request):
    """Admin Portal quotes management view with pagination."""
    from django.core.paginator import Paginator
    
    quotes = Quote.objects.select_related('client', 'service').order_by('-issue_date')
    paginator = Paginator(quotes, 25)  # 25 quotes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/admin_quotes_list.html', {
        'quotes': page_obj,
        'page_obj': page_obj
    })


@admin_portal_required
def admin_send_quote_email(request, pk):
    """Admin Portal send quote by email view."""
    from .forms import QuoteEmailForm
    from django.core.mail import EmailMessage as DjangoEmailMessage
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    quote = get_object_or_404(Quote, pk=pk)
    
    if request.method == 'POST':
        form = QuoteEmailForm(quote=quote, data=request.POST)
        if form.is_valid():
            try:
                # Ensure PDF exists and is generated
                if not quote.pdf:
                    quote.generate_pdf(attach=True)
                
                # Get explicit from_email
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nettoyageexpresse.fr')
                
                # Create email
                email = DjangoEmailMessage(
                    subject=form.cleaned_data['subject'],
                    body=form.cleaned_data['message'],
                    from_email=from_email,
                    to=[form.cleaned_data['recipient_email']]
                )
                email.content_subtype = 'html'
                
                # Attach PDF - use the saved file if available, otherwise generate bytes
                try:
                    if quote.pdf and hasattr(quote.pdf, 'open'):
                        with quote.pdf.open('rb') as f:
                            pdf_bytes = f.read()
                            email.attach(f'devis_{quote.number}.pdf', pdf_bytes, 'application/pdf')
                    else:
                        # Fallback: generate PDF as bytes
                        pdf_bytes = quote.generate_pdf(attach=False)
                        email.attach(f'devis_{quote.number}.pdf', pdf_bytes, 'application/pdf')
                except Exception as attach_error:
                    logger.error(f"Erreur lors de l'attachement du PDF pour le devis {quote.number}: {attach_error}")
                    messages.warning(request, f"Le devis a été envoyé mais le PDF n'a pas pu être attaché : {str(attach_error)}")
                
                # Send email with proper error handling
                try:
                    email.send(fail_silently=False)
                except Exception as send_error:
                    logger.error(f"Erreur lors de l'envoi de l'email pour le devis {quote.number}: {send_error}")
                    messages.error(request, f"Erreur lors de l'envoi de l'email : {str(send_error)}")
                    return render(request, 'core/admin_send_quote_email.html', {'form': form, 'quote': quote})
                
                # Update quote status
                if quote.status == Quote.QuoteStatus.DRAFT:
                    quote.status = Quote.QuoteStatus.SENT
                    quote.save(update_fields=['status'])
                
                messages.success(request, f"Devis {quote.number} envoyé avec succès à {form.cleaned_data['recipient_email']}!")
                return redirect('core:admin_quotes_list')
                
            except Exception as e:
                logger.error(f"Erreur inattendue lors de l'envoi de l'email pour le devis {quote.number}: {e}", exc_info=True)
                messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
    else:
        form = QuoteEmailForm(quote=quote)
    
    return render(request, 'core/admin_send_quote_email.html', {'form': form, 'quote': quote})


# Notification HTMX Views

@login_required
def notification_count(request):
    """HTMX endpoint to get unread notification count."""
    from core.models import UINotification
    
    count = UINotification.get_unread_count(request.user)
    return render(
        request,
        "core/partials/notification_count.html",
        {"count": count}
    )


@login_required
def notification_list(request):
    """HTMX endpoint to get notification list."""
    from core.models import UINotification
    
    notifications = UINotification.get_recent_notifications(request.user, limit=10)
    return render(
        request,
        "core/partials/notification_list.html",
        {"notifications": notifications}
    )


@login_required
def mark_notification_read(request, notification_id):
    """HTMX endpoint to mark a notification as read."""
    from core.models import UINotification
    
    try:
        notification = UINotification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
    except UINotification.DoesNotExist:
        pass
    
    # Return updated notification count
    count = UINotification.get_unread_count(request.user)
    return render(
        request,
        "core/partials/notification_count.html",
        {"count": count}
    )


@login_required
def mark_all_notifications_read(request):
    """HTMX endpoint to mark all notifications as read."""
    from core.models import UINotification
    from django.utils import timezone
    
    UINotification.objects.filter(user=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    
    # Return updated notification list
    notifications = UINotification.get_recent_notifications(request.user, limit=10)
    return render(
        request,
        "core/partials/notification_list.html",
        {"notifications": notifications}
    )
