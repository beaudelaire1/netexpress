# Guide de Corrections : PDF & Email

## 1. UNIFIER LE SYSTÈME PDF (Priorité haute)

### Problème actuel
Tu as deux générateurs PDF :
- **ReportLab** dans `devis/models.py` (237 lignes procédurales)
- **WeasyPrint** dans `core/services/pdf_generator.py` (template HTML)

### Solution : Supprimer ReportLab, garder WeasyPrint

**Pourquoi WeasyPrint ?**
- Templates HTML + CSS = facile à personnaliser
- Pas besoin de coder les coordonnées pixel par pixel
- Même template utilisable pour web preview

### Étapes de migration

**Étape 1 : Modifier le signal dans `devis/models.py`**

Remplacer la méthode `Quote.generate_pdf()` (lignes 225-461) par une délégation vers le service :

```python
# devis/models.py - Nouvelle version de generate_pdf

def generate_pdf(self, attach: bool = True) -> bytes:
    """Génère le PDF via WeasyPrint (service unifié)."""
    from core.services.pdf_service import QuotePdfService
    from django.core.files.base import ContentFile

    service = QuotePdfService()
    pdf_file = service.generate(self)

    if attach:
        self.pdf.save(pdf_file.filename, ContentFile(pdf_file.content), save=True)

    return pdf_file.content
```

**Étape 2 : Améliorer le signal post_save**

```python
# devis/models.py - Modifier le signal (lignes 563-597)

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Quote)
def send_quote_created_email(sender, instance: "Quote", created: bool, **kwargs):
    """Notification après création d'un devis."""
    if not created:
        return

    # Calcul des totaux avec logging
    try:
        instance.compute_totals()
    except Exception as e:
        logger.exception("Échec compute_totals pour devis %s: %s", instance.pk, e)
        # On continue quand même pour notifier l'admin

    email_service = PremiumEmailService()

    # Notification admin (ne bloque pas)
    try:
        email_service.notify_admin_quote_created(instance)
    except Exception as e:
        logger.warning("Échec notification admin devis %s: %s", instance.pk, e)

    # Email client avec PDF
    try:
        email_service.send_quote_pdf_to_client(instance)
    except Exception as e:
        logger.exception("Échec envoi email client devis %s: %s", instance.pk, e)
```

---

## 2. CORRIGER LE CHEMIN DU LOGO

### Problème
```html
<img src="file://{{ branding.logo_path }}">
```
Ne fonctionne pas en production.

### Solution dans `templates/pdf/quote.html`

```html
<!-- Ligne 12-16 - Remplacer par : -->
{% if branding.logo_path %}
  <img class="logo" src="{{ branding.logo_path }}" alt="Logo">
{% else %}
  <div class="kicker">{{ branding.name|default:"NetExpress" }}</div>
{% endif %}
```

Et modifier `core/services/pdf_generator.py` pour passer le chemin absolu correctement :

```python
# Dans render_quote_pdf(), ajouter avant ctx :
from django.contrib.staticfiles import finders

logo_path = _branding().get("logo_path")
if logo_path:
    # Résoudre vers un chemin absolu utilisable par WeasyPrint
    resolved = finders.find(logo_path.replace("static:", "").lstrip("/"))
    if resolved:
        logo_path = resolved

ctx: Dict[str, Any] = {
    "doc_type": "quote",
    "quote": quote,
    "branding": {**_branding(), "logo_path": logo_path},
}
```

---

## 3. HARMONISER LES COULEURS EMAIL

### Fichier : `templates/emails/base_email.html`

Remplacer toutes les occurrences de `#0a36ff` par `#0f6d4e` :

```html
<!-- Ligne 14 : gradient -->
<td align="center" style="padding:22px 18px;background:linear-gradient(90deg,#0f6d4e,#0a3c28);">

<!-- Ligne 32 : liens -->
<a href="{{ branding.site_url|default:'#' }}" style="color:#0f6d4e;text-decoration:none;">

<!-- Ligne 35 : liens sociaux -->
<a href="{{ branding.facebook_url }}" style="color:#0f6d4e;text-decoration:none;">
```

### Fichier : `templates/emails/new_quote_pdf.html`

```html
<!-- Ligne 22 : bouton CTA -->
<a href="{{ cta_url }}" style="display:inline-block;padding:12px 16px;border-radius:12px;background:#0f6d4e;color:#fff;text-decoration:none;font-weight:700;">
```

---

## 4. AMÉLIORER LA ROBUSTESSE EMAIL

### Fichier : `devis/tasks.py`

```python
# Améliorer send_quote_pdf_email (ligne 18-59)

import logging
logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 min entre retries
    max_retries=5,
    acks_late=True,  # Acknowledge après succès seulement
)
def send_quote_pdf_email(self, quote_id: int) -> dict:
    """Envoi asynchrone du devis PDF au client."""
    from devis.models import Quote

    try:
        quote = Quote.objects.select_related("client").prefetch_related("quote_items").get(pk=quote_id)
    except Quote.DoesNotExist:
        logger.error("Devis %s introuvable pour envoi email", quote_id)
        return {"status": "error", "reason": "quote_not_found"}

    # Recalcul des totaux
    try:
        quote.compute_totals()
    except Exception as e:
        logger.warning("compute_totals échoué pour devis %s: %s", quote_id, e)

    # Génération PDF
    try:
        pdf_res = render_quote_pdf(quote)
    except Exception as e:
        logger.exception("Génération PDF échouée pour devis %s", quote_id)
        raise  # Retry automatique

    # Validation destinataire
    to_email = getattr(quote.client, "email", None) or getattr(quote, "email", None)
    if not to_email:
        logger.warning("Pas d'email client pour devis %s", quote_id)
        return {"status": "skipped", "reason": "no_recipient"}

    # Construction email
    context = {
        "quote": quote,
        "branding": getattr(settings, "INVOICE_BRANDING", {}) or {},
        "cta_url": f"{settings.SITE_URL.rstrip('/')}/devis/{quote.pk}/" if hasattr(settings, "SITE_URL") else None,
    }
    html = render_to_string("emails/new_quote_pdf.html", context)

    email = EmailMessage(
        subject=f"Votre devis {quote.number}",
        body=html,
        to=[to_email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
    email.content_subtype = "html"
    email.attach(pdf_res.filename, pdf_res.content, "application/pdf")

    # BCC admin
    admin_email = getattr(settings, "TASK_NOTIFICATION_EMAIL", None)
    if admin_email:
        email.bcc = [admin_email]

    try:
        email.send(fail_silently=False)
        logger.info("Email devis %s envoyé à %s", quote.number, to_email)
        return {"status": "sent", "to": to_email, "quote": quote.number}
    except Exception as e:
        logger.exception("Envoi email échoué pour devis %s", quote_id)
        raise  # Retry automatique
```

---

## 5. AJOUTER UN FALLBACK SANS CELERY

Si Celery n'est pas disponible, l'email doit quand même partir.

### Fichier : `devis/views.py`

```python
# Dans request_quote(), après form.save() (lignes 34-40)

try:
    from devis.tasks import send_quote_request_received
    send_quote_request_received.delay(quote_request.pk)
except Exception as e:
    # Fallback synchrone si Celery down
    logger.warning("Celery indisponible, envoi synchrone: %s", e)
    try:
        from core.services.email_service import PremiumEmailService
        PremiumEmailService().notify_admin_quote_created(quote_request)
    except Exception as sync_error:
        logger.exception("Envoi synchrone également échoué: %s", sync_error)
```

---

## 6. CONFIGURER LE LOGGING

### Fichier : `netexpress/settings/base.py`

Ajouter à la fin :

```python
# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'netexpress.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'devis': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'core.services': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}
```

Et créer le dossier logs :
```bash
mkdir -p src/src_netexpress/logs
echo "*.log" >> src/src_netexpress/logs/.gitignore
```

---

## RÉSUMÉ DES FICHIERS À MODIFIER

| Fichier | Modifications |
|---------|---------------|
| `devis/models.py` | Simplifier `generate_pdf()`, améliorer signal |
| `devis/tasks.py` | Ajouter logging, retours structurés |
| `devis/views.py` | Fallback synchrone |
| `core/services/pdf_generator.py` | Résolution logo |
| `templates/pdf/quote.html` | Retirer `file://` |
| `templates/emails/base_email.html` | Couleurs marque |
| `templates/emails/new_quote_pdf.html` | Couleur bouton |
| `netexpress/settings/base.py` | Config logging |

---

## TEST DE VALIDATION

Après modifications, tester avec :

```python
# Django shell
from devis.models import Quote, Client

# Créer un test
client = Client.objects.create(
    full_name="Test Client",
    email="ton-email@test.com",
    phone="0694000000"
)
quote = Quote.objects.create(client=client, message="Test PDF")
quote.compute_totals()

# Générer PDF
pdf_bytes = quote.generate_pdf(attach=True)
print(f"PDF généré: {len(pdf_bytes)} bytes")
print(f"Fichier: {quote.pdf.name}")

# Test email (synchrone)
from core.services.email_service import PremiumEmailService
service = PremiumEmailService()
service.send_quote_pdf_to_client(quote)
```
