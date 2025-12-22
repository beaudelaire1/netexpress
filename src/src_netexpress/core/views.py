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


@staff_member_required
def dashboard(request):
    """Tableau de bord interne agrégé."""
    tasks = Task.objects.all().order_by("-created_at")[:5]
    quotes = Quote.objects.all().order_by("-issue_date")[:5]
    invoices = Invoice.objects.all().order_by("-issue_date")[:5]
    email_messages = EmailMessage.objects.all().order_by("-created_at")[:5]

    # Statistiques rapides (ERP)
    invoice_stats = {
        "total": Invoice.objects.count(),
        "draft": Invoice.objects.filter(status=Invoice.InvoiceStatus.DRAFT).count(),
        "sent": Invoice.objects.filter(status=Invoice.InvoiceStatus.SENT).count(),
        "paid": Invoice.objects.filter(status=Invoice.InvoiceStatus.PAID).count(),
        "overdue": Invoice.objects.filter(status=Invoice.InvoiceStatus.OVERDUE).count(),
    }
    task_stats = {
        "total": Task.objects.count(),
        "completed": Task.objects.filter(status=Task.STATUS_COMPLETED).count(),
        "overdue": Task.objects.filter(status=Task.STATUS_OVERDUE).count(),
        "in_progress": Task.objects.filter(status=Task.STATUS_IN_PROGRESS).count(),
        "upcoming": Task.objects.filter(status=Task.STATUS_UPCOMING).count(),
    }
    quote_stats = {
        "total": Quote.objects.count(),
        "draft": Quote.objects.filter(status=Quote.QuoteStatus.DRAFT).count(),
        "sent": Quote.objects.filter(status=Quote.QuoteStatus.SENT).count(),
        "accepted": Quote.objects.filter(status=Quote.QuoteStatus.ACCEPTED).count(),
    }

    return render(
        request,
        "core/dashboard.html",
        {
            "tasks": tasks,
            "quotes": quotes,
            "invoices": invoices,
            "recent_messages": email_messages,
            "invoice_stats": invoice_stats,
            "task_stats": task_stats,
            "quote_stats": quote_stats,
        },
    )


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
    
    # Check if quote can be validated
    if quote.status != Quote.QuoteStatus.SENT:
        return TemplateResponse(
            request, 
            "core/client_quote_detail.html", 
            {
                "quote": quote,
                "error_message": "Ce devis ne peut pas être validé dans son état actuel."
            }
        )
    
    # Create validation and send code
    from devis.models import QuoteValidation
    from devis.email_service import send_quote_validation_code
    
    validation = QuoteValidation.create_for_quote(quote)
    send_quote_validation_code(quote, validation)
    
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
    
    # Get the most recent validation for this quote
    from devis.models import QuoteValidation
    try:
        validation = QuoteValidation.objects.filter(
            quote=quote, 
            confirmed_at__isnull=True
        ).latest('created_at')
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
        form = QuoteValidationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            if validation.verify(code):
                # Update quote status
                quote.status = Quote.QuoteStatus.ACCEPTED
                quote.save(update_fields=["status"])
                
                # Always generate/regenerate PDF to ensure it's current
                try:
                    quote.generate_pdf(attach=True)
                except Exception as e:
                    # Log the error but don't fail the validation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"PDF generation failed for quote {quote.number}: {e}")
                
                # Send notification about quote validation
                try:
                    from core.services.notification_service import NotificationService
                    notification_service = NotificationService()
                    notification_service.notify_quote_validation(quote)
                except Exception as e:
                    # Log the error but don't fail the validation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Notification failed for quote {quote.number}: {e}")
                
                return TemplateResponse(
                    request,
                    "core/client_quote_validate_success.html",
                    {"quote": quote}
                )
            else:
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
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.contrib.auth.models import User
    
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
    
    # Recent activity
    recent_quotes = Quote.objects.order_by('-created_at')[:5]
    recent_invoices = Invoice.objects.order_by('-created_at')[:5]
    recent_tasks = Task.objects.order_by('-created_at')[:5]
    
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
    
    return render(
        request,
        "core/admin_dashboard.html",
        {
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
            
            # Status Distributions
            'quote_status_counts': quote_status_counts,
            'invoice_status_counts': invoice_status_counts,
            'task_status_counts': task_status_counts,
            
            # Totals
            'total_quotes': total_quotes,
            'total_invoices': Invoice.objects.count(),
            'total_tasks': total_tasks,
            'overdue_tasks': overdue_tasks,
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
    """Admin Portal workers management view."""
    from django.contrib.auth.models import User
    
    workers = User.objects.filter(groups__name='Workers').order_by('first_name', 'last_name')
    
    # Add task statistics for each worker
    workers_with_stats = []
    for worker in workers:
        worker_tasks = Task.objects.filter(assigned_to=worker)
        workers_with_stats.append({
            'worker': worker,
            'total_tasks': worker_tasks.count(),
            'completed_tasks': worker_tasks.filter(status=Task.STATUS_COMPLETED).count(),
            'pending_tasks': worker_tasks.exclude(status=Task.STATUS_COMPLETED).count(),
            'overdue_tasks': worker_tasks.filter(status=Task.STATUS_OVERDUE).count(),
        })
    
    return render(request, 'core/admin_workers_list.html', {'workers_with_stats': workers_with_stats})


@admin_portal_required
def admin_clients_list(request):
    """Admin Portal clients management view."""
    clients = Client.objects.all().order_by('full_name')
    
    # Add statistics for each client
    clients_with_stats = []
    for client in clients:
        client_quotes = Quote.objects.filter(client=client)
        clients_with_stats.append({
            'client': client,
            'total_quotes': client_quotes.count(),
            'accepted_quotes': client_quotes.filter(status=Quote.QuoteStatus.ACCEPTED).count(),
            'pending_quotes': client_quotes.filter(status=Quote.QuoteStatus.SENT).count(),
        })
    
    return render(request, 'core/admin_clients_list.html', {'clients_with_stats': clients_with_stats})


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
    """Admin Portal invoices management view."""
    invoices = Invoice.objects.all().order_by('-issue_date')
    
    return render(request, 'core/admin_invoices_list.html', {'invoices': invoices})


@admin_portal_required
def admin_quotes_list(request):
    """Admin Portal quotes management view."""
    quotes = Quote.objects.all().order_by('-issue_date')
    
    return render(request, 'core/admin_quotes_list.html', {'quotes': quotes})


@admin_portal_required
def admin_send_quote_email(request, pk):
    """Admin Portal send quote by email view."""
    from .forms import QuoteEmailForm
    from django.core.mail import EmailMessage as DjangoEmailMessage
    
    quote = get_object_or_404(Quote, pk=pk)
    
    if request.method == 'POST':
        form = QuoteEmailForm(quote=quote, data=request.POST)
        if form.is_valid():
            try:
                # Generate PDF
                pdf_content = quote.generate_pdf(attach=True)
                
                # Create email
                email = DjangoEmailMessage(
                    subject=form.cleaned_data['subject'],
                    body=form.cleaned_data['message'],
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL
                    to=[form.cleaned_data['recipient_email']]
                )
                email.content_subtype = 'html'
                
                # Attach PDF
                email.attach(f'devis_{quote.number}.pdf', pdf_content, 'application/pdf')
                
                # Send email
                email.send()
                
                # Update quote status
                if quote.status == Quote.QuoteStatus.DRAFT:
                    quote.status = Quote.QuoteStatus.SENT
                    quote.save()
                
                messages.success(request, f"Devis {quote.number} envoyé avec succès à {form.cleaned_data['recipient_email']}!")
                return redirect('core:admin_quotes_list')
                
            except Exception as e:
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
    
    UINotification.objects.filter(user=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    
    # Return updated notification count
    count = UINotification.get_unread_count(request.user)
    return render(
        request,
        "core/partials/notification_count.html",
        {"count": count}
    )
