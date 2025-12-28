"""
Vues pour gérer les campagnes email via Brevo.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .services.brevo_campaign_service import BrevoCampaignService
import logging

logger = logging.getLogger(__name__)


@staff_member_required
@require_http_methods(["GET", "POST"])
def create_campaign(request):
    """Vue pour créer une nouvelle campagne email."""
    if request.method == "POST":
        try:
            service = BrevoCampaignService()
            
            # Parser les list_ids si fournis
            list_ids = None
            list_ids_str = request.POST.get('list_ids', '').strip()
            if list_ids_str:
                try:
                    list_ids = [int(id.strip()) for id in list_ids_str.split(',') if id.strip().isdigit()]
                except ValueError:
                    list_ids = None
            
            campaign = service.create_campaign(
                name=request.POST.get('name'),
                subject=request.POST.get('subject'),
                html_content=request.POST.get('html_content'),
                sender_name=request.POST.get('sender_name') or None,
                sender_email=request.POST.get('sender_email') or None,
                list_ids=list_ids,
                scheduled_at=None  # Pour l'instant, envoi immédiat
            )
            
            # Si l'utilisateur veut envoyer immédiatement
            if request.POST.get('send_now') == 'on':
                service.send_campaign(campaign['id'])
                messages.success(request, f"Campagne '{campaign['name']}' créée et envoyée avec succès!")
            else:
                messages.success(request, f"Campagne '{campaign['name']}' créée avec succès!")
            
            return redirect('core:campaigns_list')
        except Exception as e:
            logger.error(f"Erreur lors de la création de la campagne: {e}")
            messages.error(request, f"Erreur lors de la création de la campagne: {str(e)}")
    
    return render(request, 'core/create_campaign.html')


@staff_member_required
def campaigns_list(request):
    """Liste toutes les campagnes."""
    try:
        service = BrevoCampaignService()
        campaigns = service.list_campaigns(limit=50)
        
        # Pagination
        paginator = Paginator(campaigns, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'core/campaigns_list.html', {
            'campaigns': page_obj,
            'page_obj': page_obj
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des campagnes: {e}")
        messages.error(request, f"Erreur lors de la récupération des campagnes: {str(e)}")
        return render(request, 'core/campaigns_list.html', {'campaigns': []})


@staff_member_required
def campaign_detail(request, campaign_id):
    """Détails d'une campagne."""
    try:
        service = BrevoCampaignService()
        campaign = service.get_campaign(campaign_id)
        return render(request, 'core/campaign_detail.html', {'campaign': campaign})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la campagne: {e}")
        messages.error(request, f"Erreur lors de la récupération de la campagne: {str(e)}")
        return redirect('core:campaigns_list')


@staff_member_required
@require_http_methods(["POST"])
def send_campaign(request, campaign_id):
    """Envoie une campagne."""
    try:
        service = BrevoCampaignService()
        result = service.send_campaign(campaign_id)
        messages.success(request, f"Campagne envoyée avec succès!")
        return redirect('core:campaign_detail', campaign_id=campaign_id)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la campagne: {e}")
        messages.error(request, f"Erreur lors de l'envoi de la campagne: {str(e)}")
        return redirect('core:campaign_detail', campaign_id=campaign_id)


@staff_member_required
@require_http_methods(["POST"])
def delete_campaign(request, campaign_id):
    """Supprime une campagne."""
    try:
        service = BrevoCampaignService()
        service.delete_campaign(campaign_id)
        messages.success(request, "Campagne supprimée avec succès!")
        return redirect('core:campaigns_list')
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la campagne: {e}")
        messages.error(request, f"Erreur lors de la suppression de la campagne: {str(e)}")
        return redirect('core:campaigns_list')

