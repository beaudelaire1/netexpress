from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import logging

from .forms import ContactForm, TacheForm, DevisForm
from .models import Devis, Client, Service, EmailService as send_mail

def index(request):
    return render(request, 'luxama/index.html')

def nettoyage(request):
    return render(request, 'luxama/nettoyage.html')

def peinture(request):
    return render(request, 'luxama/peinture.html')

def bricolage(request):
    return render(request, 'luxama/bricolage.html')

def renovation(request):
    return render(request, 'luxama/renovation.html')

def contact(request):
    if request.method == "POST":
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        telephone = request.POST.get('telephone')
        email = request.POST.get('email')
        message = request.POST.get('message')
        devis = request.POST.get('devis')
        motif = request.POST.get('motif')
        return render(request, 'luxama/sendingData.html')
    return render(request, 'luxama/contact.html')

def submit_contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Récupération des données du formulaire
            nom = form.cleaned_data['nom']
            prenom = form.cleaned_data['prenom']
            email = form.cleaned_data['email']
            telephone = form.cleaned_data['telephone']
            motif = form.cleaned_data['motif']
            message = form.cleaned_data['message']

            # Envoi de l'email en HTML
            corps_message = (
                "Bonjour,\n\n"
                "Quelqu'un vous a contacté depuis le site de votre entreprise.\n\n"
                "Vous trouverez ci-dessous ses coordonnées et son message:\n\n"
                "Coordonnées\n"
                "------------\n"
                f"Nom: {nom}\n"
                f"Prénom: {prenom}\n"
                f"Email: {email}\n"
                f"Téléphone: {telephone}\n\n"
                "Message\n"
                "-------\n"
                f"Motif: {motif}\n"
                f"Message: {message}\n\n"
                "Vous disposez d'un bref délai pour faire une réponse.\n\n"
                "Cordialement,\n"
                "Votre site Nettoyage Express"
            )

            send_mail.envoyer_email(corps_message, subject="NOUVEAU MESSAGE DE CONTACT DEPUIS LE SITE NETTOYAGE EXPRESS")
            # Redirection ou confirmation après envoi
            return render(request, 'luxama/sendingData.html', {'form': form})  # Afficher la page de confirmation
    else:
        form = ContactForm()

    return render(request, 'luxama/contact.html', {'form': form})

def handle_contact_form(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            print(form.cleaned_data)
            return redirect('sendingData')  # Utilisez le nom de la vue ou l'URL nommée
    else:
        form = ContactForm()
    return render(request, 'luxama/contact.html', {'form': form})

#logger = logging.getLogger(__name__)

@login_required
def creer_devis(request):
    if request.method == 'POST':
        form = DevisForm(request.POST)
        if form.is_valid():
            devis = form.save(commit=False)
            services_ids = request.POST.getlist('services')
            devis.prix_initial = sum(Service.objects.filter(id__in=services_ids).values_list('prix', flat=True))
            devis.save()
            devis.service.set(services_ids)
            return redirect('detail_devis', devis_id=devis.id)
    else:
        form = DevisForm()

    clients = Client.objects.all()
    services = Service.objects.all()
    return render(request, 'luxama/creer_devis.html', {
        'form': form,
        'clients': clients,
        'services': services
    })
@login_required
def detail_devis(request, devis_id):
    devis = get_object_or_404(Devis, id=devis_id)
    return render(request, 'luxama/detail_devis.html', {'devis': devis})

@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'luxama/client_detail.html', {'client': client})

@login_required
def custom_dashboard(request):
    context = {
        'services_count': Service.objects.count(),
        'clients_count': Client.objects.count(),
        'devis_count': Devis.objects.count(),
    }
    return render(request, 'admin/index.html', context)

def sendingData(request):
    return render(request, 'luxama/sendingData.html')
