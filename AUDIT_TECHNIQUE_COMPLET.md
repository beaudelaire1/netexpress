# AUDIT TECHNIQUE COMPLET - NetExpress

**Date:** 22 décembre 2025
**Projet:** Application Django de gestion commerciale (Devis, Factures, Services)
**Version Django:** 3.2 LTS
**Lignes de code:** ~7 246 lignes Python
**Fichiers Python:** 117 fichiers

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Architecture et structure](#2-architecture-et-structure)
3. [Analyse des dépendances](#3-analyse-des-dépendances)
4. [Modèles de données](#4-modèles-de-données)
5. [Logique métier et vues](#5-logique-métier-et-vues)
6. [Système d'emails et notifications](#6-système-demails-et-notifications)
7. [Génération de PDF](#7-génération-de-pdf)
8. [Interface admin et ergonomie](#8-interface-admin-et-ergonomie)
9. [Sécurité et configuration production](#9-sécurité-et-configuration-production)
10. [Tests et qualité du code](#10-tests-et-qualité-du-code)
11. [Points forts identifiés](#11-points-forts-identifiés)
12. [Problèmes critiques](#12-problèmes-critiques)
13. [Recommandations priorisées](#13-recommandations-priorisées)
14. [Plan d'action détaillé](#14-plan-daction-détaillé)

---

## 1. VUE D'ENSEMBLE DU PROJET

### 1.1 Contexte

NetExpress est une application web Django destinée à une entreprise de services (nettoyage, espaces verts, rénovation, bricolage) basée en Guyane française. L'application gère:

- **Catalogue de services** avec catégories
- **Demandes de devis** clients avec formulaire public
- **Gestion des devis** avec génération PDF
- **Facturation** avec conversion devis → facture
- **Contact** avec formulaire et notifications
- **Tâches** (planification et suivi)
- **Messagerie** (historique emails envoyés)

### 1.2 Stack technique identifiée

```
Backend:     Django 3.2 LTS
Serveur web: Gunicorn + Uvicorn (prod)
Base de données: SQLite (dev) - PostgreSQL recommandé (prod)
PDF:         WeasyPrint + ReportLab
Emails:      SMTP avec templates HTML
Tâches async: Celery + Redis
Admin UI:    Django Admin + Jazzmin theme
Frontend:    HTML/CSS/JS vanilla (pas de framework JS)
```

### 1.3 Arborescence du projet

```
src/src_netexpress/
├── contact/           # Formulaire de contact
├── core/              # Services partagés (PDF, email)
│   └── services/
│       ├── email_service.py    # PremiumEmailService
│       ├── pdf_service.py      # InvoicePdfService, QuotePdfService
│       └── pdf_generator.py    # Helpers WeasyPrint
├── devis/             # Gestion devis
│   ├── models.py      # Quote, QuoteItem, Client, QuoteRequest
│   ├── views.py       # Formulaires publics + admin
│   ├── forms.py       # DevisForm, QuoteRequestForm
│   ├── tasks.py       # Tâches Celery
│   └── admin.py       # Configuration admin
├── factures/          # Gestion factures
│   ├── models.py      # Invoice, InvoiceItem
│   ├── views.py
│   ├── services/
│   │   └── pdf_generator.py
│   └── admin.py
├── services/          # Catalogue services
│   └── models.py      # Service, Category, ServiceTask
├── tasks/             # Gestion tâches
│   ├── models.py      # Task
│   └── services.py    # EmailNotificationService
├── messaging/         # Historique emails
│   └── models.py      # EmailMessage
├── hexcore/           # Architecture hexagonale (partielle)
│   ├── domain/
│   │   └── entities.py    # Invoice, InvoiceItem (dataclasses)
│   └── ports/
│       └── interfaces.py  # InvoiceRepository, PdfGenerator
├── django_orm/        # Adaptateur ORM
├── weasyprint_adapter/  # Adaptateur PDF
├── netexpress/        # Configuration projet
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── celery.py
│   └── urls.py
├── templates/         # Templates Django
│   ├── base.html
│   ├── core/
│   ├── devis/
│   ├── factures/
│   ├── contact/
│   ├── emails/        # Templates email HTML
│   └── pdf/           # Templates PDF WeasyPrint
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── pdf.css
│   │   └── base.css
│   ├── js/
│   │   ├── main.js
│   │   ├── forms.js
│   │   └── quote_admin.js
│   └── img/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── tests/
    └── test_models.py
```

---

## 2. ARCHITECTURE ET STRUCTURE

### 2.1 Architecture globale

**Pattern:** Django MVT (Model-View-Template) classique avec début d'architecture hexagonale

**Apps Django:**
- `core`: Services partagés (emails, PDF, vues utilitaires)
- `contact`: Formulaire de contact + notifications
- `devis`: Gestion complète des devis
- `factures`: Facturation
- `services`: Catalogue de services
- `tasks`: Planification et suivi tâches
- `messaging`: Historique des emails envoyés

### 2.2 Architecture hexagonale (partielle)

**Constat:** Le projet a une ébauche d'architecture hexagonale dans `hexcore/` mais **elle n'est pas complètement implémentée**.

```python
# hexcore/domain/entities.py
@dataclass
class Invoice:
    """Domain entity - pas de dépendance Django"""
    number: str
    issue_date: date
    items: List[InvoiceItem]
    # ...

# hexcore/ports/interfaces.py
class InvoiceRepository(ABC):
    @abstractmethod
    def create_from_quote(self, quote_id: int) -> Invoice:
        ...

class PdfGenerator(ABC):
    @abstractmethod
    def generate(self, invoice: Invoice, ...) -> bytes:
        ...
```

**Analyse:**
✅ **Bon:** Séparation domaine/infrastructure théorique
⚠️ **Incomplet:** Les adaptateurs (`django_orm/`, `weasyprint_adapter/`) existent mais ne sont **pas utilisés** dans le code principal
⚠️ **Incohérence:** `factures/models.py` utilise directement Django ORM, pas le repository pattern

**Recommandation:** Soit finir la migration hexagonale, soit la supprimer pour éviter la confusion.

### 2.3 Services métier

Le projet utilise des services pour centraliser la logique:

```python
# core/services/email_service.py
class PremiumEmailService:
    """
    ✅ Bon: Encapsulation logique email
    ✅ Bon: Génération PDF avant envoi
    ✅ Bon: Templates HTML brandés
    """
    def send_invoice_notification(self, invoice):
        pdf_file = self.invoice_pdf_service.generate(invoice)
        # ... envoi email avec PDF
        email.send(fail_silently=False)
```

**Points positifs:**
- Séparation claire des responsabilités
- Réutilisable entre apps
- Testable indépendamment des vues

---

## 3. ANALYSE DES DÉPENDANCES

### 3.1 Structure requirements/

**Constat:** Contrairement à mon analyse initiale erronée, le projet **possède bien** une structure de requirements propre.

```
requirements/
├── base.txt      # Dépendances communes
├── dev.txt       # -r base.txt + outils dev
└── prod.txt      # -r base.txt + serveurs prod
```

### 3.2 Contenu base.txt

```txt
Django>=3.2,<4.0          # Django 3.2 LTS
django-environ>=0.11      # Variables d'environnement
dj-database-url>=2.2      # Parse DATABASE_URL
whitenoise>=6.6           # Servir fichiers statiques
psycopg2-binary>=2.9      # PostgreSQL driver
django-jazzmin>=2.6       # Theme admin
reportlab>=4.0            # Génération PDF (devis)
```

**Analyse:**

✅ **Django 3.2 LTS** - Bon choix (support jusqu'à avril 2024)
⚠️ **Pas Django 4.x** - Considérer migration vers Django 4.2 LTS (support jusqu'à 2026)
✅ **WhiteNoise** - Parfait pour servir fichiers statiques en production
✅ **psycopg2** - PostgreSQL driver présent
⚠️ **ReportLab uniquement** - WeasyPrint **absent** alors que le code l'utilise!

### 3.3 Contenu dev.txt

```txt
-r base.txt
pytest>=8.3
pytest-django>=4.8
num2words==0.5.14
numpy==2.2.2
sqlparse==0.5.3
```

✅ **Pytest** - Framework de tests moderne (bon choix)
✅ **pytest-django** - Plugin Django pour pytest
⚠️ **num2words** - Utilisé pour montants en lettres, devrait être dans base.txt

### 3.4 Contenu prod.txt

```txt
-r base.txt
gunicorn>=22.0       # Serveur WSGI
uvicorn>=0.30        # Serveur ASGI
reportlab>=3.6       # Redondant avec base.txt
django-jazzmin>=2.6  # Redondant avec base.txt
```

✅ **Gunicorn + Uvicorn** - Stack serveur solide
⚠️ **Redondances** - reportlab et jazzmin déjà dans base.txt

### 3.5 Dépendances manquantes critiques

**🔴 PROBLÈME MAJEUR:** Le code utilise des bibliothèques **non déclarées** dans requirements!

```python
# core/services/pdf_service.py:30
from weasyprint import HTML, CSS  # ❌ PAS dans requirements!

# netexpress/celery.py:2
from celery import Celery  # ❌ PAS dans requirements!

# settings/base.py:301
CELERY_BROKER_URL = env("CELERY_BROKER_URL",
                        default="redis://localhost:6379/0")
# ❌ redis package PAS dans requirements!
```

**Impact:**
- `pip install -r requirements/prod.txt` **va échouer** au runtime
- Déploiement impossible sans installer manuellement weasyprint, celery, redis

**Correction immédiate requise:**

```txt
# requirements/base.txt
Django>=3.2,<4.0
django-environ>=0.11
dj-database-url>=2.2
whitenoise>=6.6
psycopg2-binary>=2.9
django-jazzmin>=2.6
reportlab>=4.0
weasyprint>=60.1         # ← AJOUTER
celery>=5.3              # ← AJOUTER
redis>=5.0               # ← AJOUTER
pillow>=10.0             # ← AJOUTER (images)
num2words>=0.5.14        # ← DÉPLACER depuis dev.txt
```

---

## 4. MODÈLES DE DONNÉES

### 4.1 Vue d'ensemble

**Total:** 12 modèles Django principaux

| App | Modèles | Relations |
|-----|---------|-----------|
| `devis` | Client, Quote, QuoteItem, QuoteRequest, QuotePhoto, QuoteRequestPhoto | Quote → Client (FK), QuoteItem → Quote (FK) |
| `factures` | Invoice, InvoiceItem | Invoice → Quote (FK), InvoiceItem → Invoice (FK) |
| `contact` | Message | Aucune FK |
| `services` | Service, Category, ServiceTask | Service → Category (FK), ServiceTask → Service (FK) |
| `tasks` | Task | Aucune FK |
| `messaging` | EmailMessage | Aucune FK |

### 4.2 Modèle Contact (contact/models.py)

```python
class Message(models.Model):
    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    city = models.CharField(max_length=200)
    street = models.CharField(max_length=200)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=50, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["topic", "created_at"])]
```

**Analyse:**

✅ **Points forts:**
- Index composite (topic, created_at) - bonnes performances
- Capture IP pour modération anti-spam
- Choix multiples pour topics
- Méthode `obfuscated_email()` pour confidentialité

⚠️ **Problèmes:**
1. **Pas de workflow de traitement**
   - Champ `processed` boolean trop simpliste
   - Devrait avoir: `status` (nouveau, en_cours, traité, archivé)
2. **Pas de traçabilité d'assignation**
   - Pas de FK vers `User` (qui traite le message?)
3. **Validation manquante**
   - Pas de validation cohérence zip_code ↔ city

**Recommandations:**

```python
class Message(models.Model):
    STATUS_CHOICES = [
        ('new', 'Nouveau'),
        ('in_progress', 'En cours'),
        ('processed', 'Traité'),
        ('archived', 'Archivé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='new')
    assigned_to = models.ForeignKey('auth.User', null=True, blank=True,
                                    on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True, blank=True)
    internal_notes = models.TextField(blank=True)  # Notes internes
```

### 4.3 Modèle Devis (devis/models.py)

#### 4.3.1 Client

```python
class Client(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

✅ **Bon:** Modèle simple et clair
⚠️ **Manque:** Pas de champ `reference` (code client)
⚠️ **Manque:** Pas de validation unicité email

#### 4.3.2 Quote

```python
class Quote(models.Model):
    number = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, null=True, blank=True, ...)
    status = models.CharField(max_length=20, choices=QuoteStatus.choices)
    issue_date = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)

    total_ht = models.DecimalField(max_digits=10, decimal_places=2)
    tva = models.DecimalField(max_digits=10, decimal_places=2)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2)

    pdf = models.FileField(upload_to="devis", blank=True, null=True)
```

**Numérotation automatique:**

```python
def save(self, *args, **kwargs):
    if not self.number:
        year = self.issue_date.year
        prefix = f"DEV-{year}-"
        last_number = Quote.objects.filter(
            number__startswith=prefix
        ).order_by("number").last()
        # ...
        self.number = f"{prefix}{last_counter + 1:03d}"
    super().save(*args, **kwargs)
```

✅ **Bon:** Numérotation séquentielle par année (DEV-2025-001)
⚠️ **Race condition possible** - Pas de `select_for_update()` contrairement à Invoice

**Problèmes critiques:**

**🔴 1. Méthode `generate_pdf()` fait 462 lignes dans le modèle!**

```python
# devis/models.py:225-461
def generate_pdf(self, attach: bool = True) -> bytes:
    """
    ❌ VIOLATION Single Responsibility Principle
    - Import ReportLab (ligne 242)
    - Logique de mise en page PDF complète
    - Gestion logo, watermark, tableaux
    - Total: 236 lignes dans le MODÈLE
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        # ... 230 lignes de code PDF ...
```

**Impact:**
- Modèle surchargé (responsabilités multiples)
- Impossible à tester unitairement
- Impossible à réutiliser
- Ralentit chaque import de `models.py`

**Solution:**

```python
# Déplacer vers core/services/pdf_generator.py
def generate_quote_pdf(quote: Quote) -> bytes:
    # ... logique PDF ...

# Dans models.py:
def generate_pdf(self, attach: bool = True) -> bytes:
    from core.services.pdf_generator import generate_quote_pdf
    return generate_quote_pdf(self)
```

**🔴 2. Validation manquante**

```python
# Aucune validation clean()
# ✅ Devrait avoir:
def clean(self):
    if self.valid_until and self.valid_until < self.issue_date:
        raise ValidationError(
            "La date de validité ne peut pas être antérieure à la date d'émission"
        )
    if self.total_ttc < 0:
        raise ValidationError("Le montant total ne peut pas être négatif")
```

### 4.4 Modèle Factures (factures/models.py)

```python
class Invoice(models.Model):
    quote = models.ForeignKey("devis.Quote", on_delete=models.SET_NULL,
                              null=True, blank=True)
    number = models.CharField(max_length=20, unique=True, blank=True)
    issue_date = models.DateField(default=date.today)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices)

    total_ht = models.DecimalField(max_digits=10, decimal_places=2)
    tva = models.DecimalField(max_digits=10, decimal_places=2)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=10, decimal_places=2)  # ⚠️ Redondant
```

**Points forts:**

✅ **Numérotation atomique avec verrouillage:**

```python
def save(self, *args, **kwargs):
    if not self.pk and not self.number:
        year = self.issue_date.year
        prefix = f"FAC-{year}-"
        from django.db import transaction
        with transaction.atomic():
            last = (
                Invoice.objects
                .select_for_update()  # ← Verrouillage pessimiste
                .filter(number__startswith=prefix)
                .order_by("number")
                .last()
            )
            # ...
            self.number = f"{prefix}{counter + 1:03d}"
```

✅ **Excellent:** Évite race conditions lors de création simultanée de factures

✅ **Méthode `create_from_quote` bien conçue:**

```python
@classmethod
def create_from_quote(cls, quote: "devis.Quote") -> "Invoice":
    from django.db import transaction
    with transaction.atomic():
        invoice = cls.objects.create(quote=quote, ...)
        for item in quote.items.all():
            InvoiceItem.objects.create(invoice=invoice, ...)
        invoice.compute_totals()
    return invoice
```

✅ **Transaction atomique** garantit cohérence

**Problèmes:**

⚠️ **1. Champ `amount` redondant avec `total_ttc`**

```python
# factures/models.py:165
amount = models.DecimalField(...)  # Dette technique rétro-compatibilité
```

**Justification dans le code:** "Compat historique"
**Solution:** Migration pour supprimer et remplacer par `total_ttc`

⚠️ **2. Pas de validation `due_date > issue_date`**

```python
# Devrait avoir:
def clean(self):
    if self.due_date and self.due_date < self.issue_date:
        raise ValidationError(
            "La date d'échéance doit être postérieure à la date d'émission"
        )
```

⚠️ **3. Référence en chaîne "devis.Quote"**

```python
# factures/models.py:144
quote = models.ForeignKey("devis.Quote", ...)  # String reference
```

**Analyse:**
✅ **Bon:** Évite imports circulaires
⚠️ **Incohérent:** Autres fichiers importent directement

### 4.5 Modèle Services (services/models.py)

```python
class Category(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to="categories", blank=True, null=True)

class Service(models.Model):
    title = models.CharField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    unit_type = models.CharField(max_length=50, default="forfait")
    duration_minutes = models.PositiveIntegerField(default=60)
    image = models.ImageField(upload_to="services", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(max_length=200, unique=True)
```

**Points forts:**

✅ **Génération automatique de slugs uniques:**

```python
def save(self, *args, **kwargs):
    if not self.slug or (self.pk and title_changed):
        base_slug = slugify(self.title, allow_unicode=True)
        slug = base_slug
        counter = 1
        while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug
    super().save(*args, **kwargs)
```

✅ **Logique de collision avec suffixe numérique**

✅ **Index sur `slug` et `is_active`** pour performances

```python
class Meta:
    indexes = [
        models.Index(fields=["slug"]),
        models.Index(fields=["is_active"]),
    ]
```

⚠️ **Manque:** Pas de prix dans le modèle Service (normal, tarifs dans devis/factures)

### 4.6 Modèle Tasks (tasks/models.py)

```python
class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    team = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(default=date.today)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def save(self, *args, **kwargs):
        today = date.today()
        if self.status != self.STATUS_COMPLETED:
            if self.due_date and self.due_date < today:
                self.status = self.STATUS_OVERDUE
            elif self.start_date and self.start_date > today:
                self.status = self.STATUS_UPCOMING
            else:
                self.status = self.STATUS_IN_PROGRESS

        # Validation
        if self.due_date and self.start_date and self.due_date < self.start_date:
            raise ValueError("Date d'échéance antérieure à la date de début")

        super().save(*args, **kwargs)
```

**Points forts:**

✅ **Recalcul automatique du statut** basé sur dates
✅ **Validation dans `save()`** (due_date ≥ start_date)
✅ **Méthode `is_due_soon(days_threshold=3)`** bien pensée
✅ **Méthode `get_absolute_url()`** pour liens canoniques

⚠️ **Problèmes:**

1. **Pas de FK vers User** (assignation manuelle via champ `team` texte)
2. **Pas de notifications automatiques** (signaux dans `signals.py` mais pas configurés)

### 4.7 Diagramme relationnel

```
┌──────────────┐
│   Category   │
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼───────┐     1     ┌──────────────┐
│   Service    │◄──────────┤ ServiceTask  │
└──────────────┘           └──────────────┘

┌──────────────┐
│    Client    │
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼───────┐     1     ┌──────────────┐
│    Quote     │◄──────────┤  QuoteItem   │
└──────┬───────┘           └──────────────┘
       │ 1
       │
       │ 0..N
┌──────▼───────┐     1     ┌──────────────┐
│   Invoice    │◄──────────┤ InvoiceItem  │
└──────────────┘           └──────────────┘

┌──────────────┐
│   Message    │  (isolé, pas de FK)
└──────────────┘

┌──────────────┐
│     Task     │  (isolé, pas de FK)
└──────────────┘
```

---

## 5. LOGIQUE MÉTIER ET VUES

### 5.1 Contact (contact/views.py)

```python
def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()
            # Email admin asynchrone
            try:
                notify_new_contact.delay(msg.pk)  # Celery
            except Exception:
                pass  # ✅ Bon: Ne bloque jamais l'utilisateur
            messages.success(request, "Message envoyé")
            return redirect(reverse("contact:success"))
```

**Points forts:**

✅ **Try/except sur Celery** - N'impacte pas UX si Celery down
✅ **Message de confirmation** utilisateur
✅ **Redirection POST/GET** (pattern PRG)

**Problèmes:**

⚠️ **1. Exception trop large**

```python
except Exception:  # ❌ Masque TOUTES les erreurs
    pass
```

**Solution:**

```python
except (ImportError, Exception) as e:
    logger.warning(f"Notification email échouée: {e}")
    # Continue sans bloquer
```

⚠️ **2. Pas de capture IP automatique**

```python
# Devrait avoir:
msg = form.save(commit=False)
msg.ip = request.META.get('REMOTE_ADDR')
msg.save()
```

### 5.2 Devis (devis/views.py)

#### 5.2.1 Formulaire public

```python
def request_quote(request):
    if request.method == "POST":
        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quote_request = form.save()
            files = request.FILES.getlist("photos")
            for f in files:
                photo = QuoteRequestPhoto.objects.create(image=f)
                quote_request.photos.add(photo)

            try:
                send_quote_request_received.delay(quote_request.pk)
            except Exception:
                pass  # ❌ Même problème exception trop large

            return redirect(reverse("devis:quote_success"))
```

✅ **Gestion multi-upload photos**
⚠️ **Pas de transaction atomique** - Photo peut être créée même si `add()` échoue

**Solution:**

```python
from django.db import transaction

with transaction.atomic():
    quote_request = form.save()
    for f in files:
        photo = QuoteRequestPhoto.objects.create(image=f)
        quote_request.photos.add(photo)
```

#### 5.2.2 Éditeur admin de devis

```python
@login_required
@staff_member_required
def admin_quote_edit(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    QuoteItemFormSet = inlineformset_factory(Quote, QuoteItem, ...)

    if request.method == "POST":
        prev_status = quote.status
        form = QuoteAdminForm(request.POST, instance=quote)
        formset = QuoteItemFormSet(request.POST, instance=quote)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()  # ⚠️ Pas de transaction

            quote.compute_totals()

            if quote.status == Quote.QuoteStatus.SENT and prev_status != Quote.QuoteStatus.SENT:
                # Génération PDF + envoi
                pdf_res = render_quote_pdf(quote)
                quote.pdf.save(pdf_res.filename, ContentFile(pdf_res.content))
                send_quote_pdf_email.delay(quote.pk)
```

**Problèmes critiques:**

**🔴 1. Pas de transaction atomique**

```python
form.save()        # ⚠️ Peut réussir
formset.save()     # ⚠️ Peut échouer
quote.compute_totals()  # ⚠️ État incohérent si échec ligne précédente
```

**Impact:** Si `formset.save()` échoue, le devis principal est modifié mais pas les items

**Solution:**

```python
from django.db import transaction

if form.is_valid() and formset.is_valid():
    with transaction.atomic():
        form.save()
        formset.save()
        quote.compute_totals()

        if status_changed:
            # ... génération PDF ...
```

**🔴 2. Autorisation insuffisante**

```python
@staff_member_required
def admin_quote_edit(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    # ❌ AUCUNE vérification de propriété
```

**Problème:** Un staff peut modifier TOUS les devis, même ceux d'autres commerciaux

**Solution (si multi-utilisateurs):**

```python
def admin_quote_edit(request, pk):
    quote = get_object_or_404(Quote, pk=pk)

    # Vérifier permissions
    if not (request.user.is_superuser or
            quote.created_by == request.user or
            request.user.has_perm('devis.change_any_quote')):
        raise PermissionDenied
```

### 5.3 Factures (factures/views.py)

```python
@staff_member_required
def download_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.pdf:
        raise Http404("PDF non généré")
    return FileResponse(invoice.pdf.open("rb"),
                        filename=invoice.pdf.name,
                        as_attachment=False)
```

**🔴 Même problème d'autorisation:** Pas de vérification de propriété

---

## 6. SYSTÈME D'EMAILS ET NOTIFICATIONS

### 6.1 Architecture email

```
┌─────────────────────────────────────┐
│  PremiumEmailService                │
│  (core/services/email_service.py)   │
│                                     │
│  - send_invoice_notification()     │
│  - send_quote_pdf_to_client()      │
│  - notify_admin_quote_created()    │
└──────────────┬──────────────────────┘
               │
               │ utilise
               ▼
┌─────────────────────────────────────┐
│  InvoicePdfService / QuotePdfService│
│  (core/services/pdf_service.py)     │
│                                     │
│  - generate(invoice) → PdfFile      │
└─────────────────────────────────────┘
```

### 6.2 PremiumEmailService (core/services/email_service.py)

```python
class PremiumEmailService:
    def send_invoice_notification(self, invoice):
        # ✅ 1. Génération PDF AVANT envoi
        pdf_file = self.invoice_pdf_service.generate(invoice)

        # ✅ 2. Template HTML brandé
        context = {
            'invoice': invoice,
            'branding': branding,
            'client_name': _safe_client_name(invoice),
        }
        html_body = render_to_string("emails/invoice_notification.html", context)
        text_body = strip_tags(html_body)

        # ✅ 3. Email multipart (HTML + texte)
        email = EmailMultiAlternatives(subject, text_body, from_email, recipients)
        email.attach_alternative(html_body, "text/html")
        email.attach(pdf_file.filename, pdf_file.content, pdf_file.mimetype)

        # ✅ 4. Fail loudly
        email.send(fail_silently=False)
```

**Points forts:**

✅ **PDF généré avant envoi** (pas d'email sans PDF)
✅ **Templates HTML professionnels** avec branding
✅ **Multipart email** (HTML + fallback texte)
✅ **fail_silently=False** pour logs erreurs

**Problèmes:**

**🔴 1. Configuration SMTP hardcodée**

```python
# settings/base.py:226-232
EMAIL_HOST_USER = env("EMAIL_HOST_USER",
    default="vilmebeaudelaire5@gmail.com")  # 🔴 HARDCODED!
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD",
    default="")  # 🔴 Mot de passe vide par défaut
```

**Problèmes:**
- Credentials exposés dans le code source
- Git history contient l'email
- Violation RGPD/sécurité

**Solution immédiate:**

```python
# settings/base.py
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # Pas de default
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

# .env (JAMAIS committé)
EMAIL_HOST_USER=contact@netexpress.gf
EMAIL_HOST_PASSWORD=mot_de_passe_securise
```

**Puis nettoyer l'historique Git:**

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch netexpress/settings/base.py" \
  --prune-empty -- --all
```

**🔴 2. Emails en mode DEBUG**

```python
# settings/base.py:240-241
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

**Problème:** En dev, emails affichés console mais **jamais envoyés réellement**

**Impact:** Impossible de tester rendu réel emails

**Solution (utiliser Mailtrap en dev):**

```python
# settings/dev.py
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST', default='sandbox.smtp.mailtrap.io')
    EMAIL_PORT = env.int('EMAIL_PORT', default=2525)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = True
```

**⚠️ 3. Templates email sans version texte brut**

```html
<!-- templates/emails/new_quote_pdf.html -->
{% extends "emails/base_email.html" %}
<!-- ❌ MANQUE: templates/emails/new_quote_pdf.txt -->
```

**Impact:**
- Clients email bloquant HTML voient message vide
- Score spam plus élevé

**Solution:** Créer version .txt pour chaque template

```
templates/emails/
├── base_email.html
├── base_email.txt        # ← AJOUTER
├── new_quote_pdf.html
├── new_quote_pdf.txt     # ← AJOUTER
├── invoice_notification.html
└── invoice_notification.txt  # ← AJOUTER
```

### 6.3 Celery & Tâches asynchrones

#### Configuration (netexpress/celery.py)

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netexpress.settings.base")

app = Celery("netexpress")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

**🔴 Problème:** `DJANGO_SETTINGS_MODULE` hardcodé sur `base`

**Solution:**

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      os.getenv("DJANGO_SETTINGS_MODULE", "netexpress.settings.dev"))
```

#### Configuration settings (base.py:301-306)

```python
CELERY_BROKER_URL = env("CELERY_BROKER_URL",
    default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
```

**Problèmes:**

⚠️ **1. Pas de healthcheck Redis**
⚠️ **2. Pas de retry policy configurée**
⚠️ **3. Pas de monitoring (Flower)**
⚠️ **4. Configuration production insuffisante**

**Solution complète:**

```python
# settings/base.py
CELERY_BROKER_URL = env("CELERY_BROKER_URL")  # Pas de default
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)

# Acknowledgment tardif (tâche relancée si worker crash)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Prefetch: 1 tâche à la fois par worker (évite blocage longues tâches)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Retry automatique
CELERY_TASK_AUTORETRY_FOR = (
    ConnectionError,
    TimeoutError,
    SMTPException,
)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute

# En dev: tâches synchrones (pas besoin de Redis)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)
```

#### Tâches (contact/tasks.py)

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def notify_new_contact(self, message_id: int) -> None:
    msg = Message.objects.get(pk=message_id)
    # ... envoi email admin ...
```

✅ **Bon:** `autoretry_for`, `retry_backoff`, `max_retries`
⚠️ **Problème:** `autoretry_for=(Exception,)` trop large (retry même erreurs non transientes)

**Solution:**

```python
from smtplib import SMTPException
from requests.exceptions import ConnectionError

@shared_task(
    bind=True,
    autoretry_for=(SMTPException, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes
    max_retries=5
)
```

---

## 7. GÉNÉRATION DE PDF

### 7.1 Architecture PDF

Le projet utilise **2 bibliothèques PDF** différentes:

1. **ReportLab** - Utilisé dans `devis/models.py:generate_pdf()` (PDF devis)
2. **WeasyPrint** - Utilisé dans `core/services/pdf_service.py` (PDF factures)

### 7.2 WeasyPrint (factures)

```python
# core/services/pdf_service.py
class InvoicePdfService:
    template_name: str = "pdf/invoice_premium.html"

    def generate(self, invoice) -> PdfFile:
        if HTML is None:
            raise RuntimeError("WeasyPrint doit être installé")

        context = {
            'invoice': invoice,
            'branding': branding,
            'rows': rows,
            # ...
        }
        html_string = render_to_string(self.template_name, context)

        base_dir = Path(settings.BASE_DIR)
        base_url = str(base_dir)

        # CSS externe
        css_path = base_dir / "static" / "css" / "pdf.css"
        if css_path.exists():
            stylesheets.append(CSS(filename=str(css_path)))

        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(
            stylesheets=stylesheets
        )
        return PdfFile(filename=f"{invoice.number}.pdf", content=pdf_bytes)
```

**Points forts:**

✅ **Template HTML** (facile à maintenir)
✅ **CSS externe** pour styling
✅ **base_url** configuré pour résolution assets
✅ **Service dédié** (séparation des responsabilités)

**Problèmes:**

⚠️ **WeasyPrint absent des requirements!** (déjà mentionné section 3)

### 7.3 ReportLab (devis)

```python
# devis/models.py:225-461 (236 lignes!)
def generate_pdf(self, attach: bool = True) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas
        # ...

        # Filigrane "DEVIS"
        c.saveState()
        c.setFillColor(colors.HexColor("#F0F0F0"))
        c.setFont("Helvetica-Bold", 60)
        c.translate(width / 2, height / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "DEVIS")
        c.restoreState()

        # ... 200+ lignes de code PDF ...
```

**Problèmes majeurs:**

🔴 **1. 236 lignes dans le modèle** (déjà mentionné section 4)
🔴 **2. Duplication** avec système WeasyPrint
🔴 **3. Difficilement maintenable**

**Recommandation:** Migrer vers WeasyPrint + template HTML

```html
<!-- templates/pdf/quote_premium.html -->
{% extends "pdf/document_base.html" %}

{% block title %}DEVIS {{ quote.number }}{% endblock %}

{% block content %}
<div class="watermark">DEVIS</div>

<div class="header">
    <h1>DEVIS {{ quote.number }}</h1>
    <div class="branding">{{ branding.name }}</div>
</div>

<div class="client-info">
    <h2>Client</h2>
    <p>{{ quote.client.full_name }}</p>
    <!-- ... -->
</div>

<table class="items">
    {% for item in quote.items.all %}
    <tr>
        <td>{{ item.description }}</td>
        <td>{{ item.quantity }}</td>
        <td>{{ item.unit_price }} €</td>
        <td>{{ item.total_ttc }} €</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}
```

**Bénéfices:**
- Réduction de 236 lignes Python → 30 lignes HTML
- Facile à modifier (pas besoin développeur)
- Cohérence avec factures
- Testable visuellement

### 7.4 Templates PDF existants

```
templates/pdf/
├── document_base.html      # ✅ Base commune
├── invoice_premium.html    # ✅ Facture WeasyPrint
├── invoice_modern.html     # ⚠️ Non utilisé?
├── invoice.html            # ⚠️ Ancien template?
└── quote.html              # ⚠️ Non utilisé (ReportLab direct)
```

**Constat:** Plusieurs templates PDF non utilisés → **nettoyage nécessaire**

---

## 8. INTERFACE ADMIN ET ERGONOMIE

### 8.1 Django Admin

**URL:** `/gestion/` (au lieu du standard `/admin/`)

**Configuration Jazzmin (settings/base.py:257-292):**

```python
JAZZMIN_SETTINGS = {
    "site_title": "Nettoyage Express Admin",
    "site_header": "Nettoyage Express",
    "welcome_sign": "Bienvenue dans l'administration...",

    # Logos
    "site_logo": "img/logo.svg",

    # Icônes personnalisées
    "icons": {
        "factures.Invoice": "fas fa-file-invoice-dollar",
        "devis.Quote": "fas fa-file-contract",
        "services.Service": "fas fa-broom",
        # ...
    },

    # Couleur
    "theme_color": "#0B5D46",

    # CSS custom
    "custom_css": "css/jazzmin_overrides.css",
}
```

**Points forts:**

✅ **Jazzmin** - Interface moderne et responsive
✅ **Icônes FontAwesome** - Navigation visuelle claire
✅ **Branding cohérent** - Couleur verte premium
✅ **Custom CSS** - Personnalisation légère

### 8.2 Admin classes

**Total:** 9 classes Admin (devis: 2, factures: 1, services: 2, tasks: 1, contact: 1, messaging: 1)

#### Exemple: QuoteAdmin (devis/admin.py)

```python
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "status", "issue_date", "total_ttc")
    list_filter = ("status", "issue_date")
    search_fields = ("number", "client__full_name", "client__email")
    list_editable = ("status",)  # ✅ Modification rapide

    actions = ["send_quotes", "convert_to_invoice"]

    class QuoteItemInline(admin.TabularInline):
        model = QuoteItem
        extra = 1
        readonly_fields = ("total_ht", "total_tva", "total_ttc")

    inlines = [QuoteItemInline]
```

**Points forts:**

✅ **Inline editing** - Modifier items directement
✅ **list_editable** - Changer statut rapidement
✅ **Actions custom** - Envoyer devis, convertir en facture
✅ **readonly_fields** - Totaux calculés automatiquement

**Problèmes:**

⚠️ **Action "send_quotes" (ligne 53) sans PDF**

```python
def send_quotes(self, request, queryset):
    for quote in queryset:
        # ❌ Email simple SANS PDF
        EmailNotificationService.send(
            client.email,
            f"Votre devis {quote.number}",
            body,  # Texte brut uniquement
        )
```

**Impact:** Devis non professionnel (pas de document attaché)

**Solution:** Utiliser `PremiumEmailService.send_quote_pdf_to_client()`

#### InvoiceAdmin (factures/admin.py)

```python
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    actions = ["generate_pdfs", "send_invoices"]

    def generate_pdfs(self, request, queryset):
        for invoice in queryset:
            invoice.compute_totals()
            invoice.generate_pdf()  # ✅ WeasyPrint
            invoice.save()

    def send_invoices(self, request, queryset):
        email_service = PremiumEmailService()
        for invoice in queryset:
            invoice.compute_totals()
            invoice.generate_pdf(attach=True)
            email_service.send_invoice_notification(invoice)
```

**Points forts:**

✅ **Actions batch** - Générer plusieurs PDFs
✅ **Utilise PremiumEmailService** - Email brandé + PDF

⚠️ **Problème:** Pas de gestion d'erreurs dans la boucle

```python
# Devrait avoir:
count_success = 0
count_error = 0
for invoice in queryset:
    try:
        email_service.send_invoice_notification(invoice)
        count_success += 1
    except Exception as e:
        count_error += 1
        logger.error(f"Erreur envoi facture {invoice.number}: {e}")

self.message_user(request,
    f"{count_success} facture(s) envoyée(s), {count_error} erreur(s)",
    level='warning' if count_error else 'success'
)
```

### 8.3 Dashboard custom (templates/core/dashboard.html)

```html
<!-- KPIs -->
<div class="kpis">
  <div class="kpi-card">
    <div class="kpi-value">{{ tasks|length }}</div>
    <div class="kpi-label">Tâches</div>
  </div>
  <!-- ... -->
</div>

<!-- Tableaux -->
<table class="dashboard-table">
  <thead><tr><th>Numéro</th><th>Total TTC</th>...</tr></thead>
  <tbody>
    {% for inv in invoices %}
    <tr>
      <td>{{ inv.number }}</td>
      <td>{{ inv.total_ttc }} €</td>
      <!-- ... -->
    </tr>
    {% endfor %}
  </tbody>
</table>
```

**Points forts:**

✅ **KPIs visuels** - Nombre tâches, factures, devis
✅ **Tableaux récapitulatifs** - Derniers éléments
✅ **Actions rapides** - Liens Voir/Éditer

**Problèmes ergonomie:**

⚠️ **1. Pas de filtres**

```html
<!-- Devrait avoir: -->
<form method="get" class="filters">
  <select name="status">
    <option value="">Tous les statuts</option>
    <option value="new">Nouveau</option>
    <option value="in_progress">En cours</option>
  </select>
  <input type="date" name="date_from" placeholder="Du">
  <input type="date" name="date_to" placeholder="Au">
  <button type="submit">Filtrer</button>
</form>
```

⚠️ **2. Pas de pagination**

```python
# views.py:
tasks = Task.objects.all()[:10]  # ❌ Limite hard-codée

# Devrait avoir:
from django.core.paginator import Paginator
paginator = Paginator(Task.objects.all(), 25)
page_obj = paginator.get_page(request.GET.get('page'))
```

⚠️ **3. Pas de recherche globale**

Jazzmin offre cette fonctionnalité mais elle n'est pas configurée:

```python
# settings/base.py JAZZMIN_SETTINGS:
"search_model": [
    "factures.Invoice",
    "devis.Quote",
    "contact.Message",
],
```

### 8.4 Ergonomie pour utilisateurs non techniques

**Analyse des formulaires publics:**

#### Formulaire contact (templates/contact/contact.html)

```html
<form method="post" novalidate class="contact-form">
  <div class="field">
    <label for="id_topic">Sujet</label>
    {{ form.topic }}  <!-- Select dropdown -->
  </div>

  <div class="field">
    <label for="id_city">Commune</label>
    {{ form.city }}
    <datalist id="city-list"></datalist>  <!-- ✅ Autocomplétion -->
  </div>
</form>

<script>
// ✅ Autocomplétion Commune ↔ Code postal
function cityToZip() {
  const v = cityInput.value.trim();
  if(communes[v]) zipInput.value = communes[v];
}
</script>
```

**Points forts:**

✅ **Autocomplétion** ville ↔ code postal (pour communes Guyane)
✅ **Labels clairs** en français
✅ **Responsive** grid CSS adaptatif

**Problèmes:**

⚠️ **1. Bug label (ligne 45)**

```html
<label for="{{ form.phone.id_for_label }}">Rue</label>
{{ form.street }}
<!-- ❌ Label pointe vers 'phone' mais affiche 'street' -->
```

**Impact:** Accessibilité cassée (lecteurs d'écran)

**Fix:**

```html
<label for="{{ form.street.id_for_label }}">Rue</label>
{{ form.street }}
```

⚠️ **2. Messages d'erreur non user-friendly**

```python
# contact/forms.py:16-78
class ContactForm(forms.ModelForm):
    class Meta:
        fields = ["topic", "full_name", ...]
        # ❌ Pas de error_messages personnalisés
```

**Résultat:** "Ce champ est obligatoire" (message Django par défaut)

**Solution:**

```python
class Meta:
    error_messages = {
        'full_name': {
            'required': 'Merci de renseigner votre nom complet',
        },
        'email': {
            'required': 'Votre email est nécessaire pour vous recontacter',
            'invalid': 'Format email invalide (ex: nom@exemple.fr)',
        },
        'phone': {
            'required': 'Votre numéro de téléphone est obligatoire',
        },
    }
```

⚠️ **3. Formulaire devis complexe**

```html
<!-- home.html:98-143 - Formulaire rapide -->
<select id="qq_urgency" name="urgency">
    <option value="standard">Standard (sous 1 semaine)</option>
    <option value="express">Express (48h)</option>
    <option value="immediat">Immédiat (24h)</option>
</select>
```

**Problème:** Utilisateur non technique ne comprend pas l'impact prix

**Solution:**

```html
<select id="qq_urgency" name="urgency" onchange="updateEstimate()">
    <option value="standard" data-markup="0">
        Standard (sous 1 semaine) - Tarif normal
    </option>
    <option value="express" data-markup="15">
        Express (48h) - Supplément +15%
    </option>
    <option value="immediat" data-markup="30">
        Immédiat (24h) - Supplément +30%
    </option>
</select>
<div class="estimate">
    Estimation: <span id="price-estimate">À calculer</span>
</div>
```

### 8.5 Design et UX

**CSS principal (static/css/style.css - 754 lignes):**

```css
:root {
    --primary-green: #104130;  /* Vert foncé premium */
    --accent-green: #2d8a5e;
    --bg-page: #f9fafb;
    --radius: 12px;
    --shadow-soft: 0 10px 30px -5px rgba(0, 0, 0, 0.08);
}
```

**Points forts:**

✅ **Variables CSS** - Cohérence design
✅ **Responsive** media queries
✅ **Animations** hover, transitions
✅ **Accessibilité** ARIA labels sur onglets

**Problèmes:**

⚠️ **1. Pas de focus visible**

```css
/* Manque: */
.btn:focus-visible,
.tab-btn:focus-visible {
    outline: 3px solid var(--accent-green);
    outline-offset: 2px;
}
```

**Impact:** Navigation clavier difficile

⚠️ **2. Contraste insuffisant potentiel**

```css
.muted { color: #6b7280; }
```

**À vérifier:** Ratio contraste WCAG AA (4.5:1 minimum)

---

## 9. SÉCURITÉ ET CONFIGURATION PRODUCTION

### 9.1 Audit de sécurité

#### 🔴 CRITIQUE 1: SECRET_KEY

```python
# settings/base.py:37
SECRET_KEY = env("DJANGO_SECRET_KEY")
```

✅ **Bon:** Variable d'environnement
⚠️ **Manque:** Validation complexité

**Solution:**

```python
SECRET_KEY = env("DJANGO_SECRET_KEY")

if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be at least 50 characters"
    )

if DEBUG and SECRET_KEY == "insecure-dev-key":
    warnings.warn("Using insecure dev key in DEBUG mode")
```

#### 🔴 CRITIQUE 2: ALLOWED_HOSTS

```python
# settings/base.py:50-54
raw_hosts = env("DJANGO_ALLOWED_HOSTS", default="")
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]
```

**Problème:** Si vide en production → Django autorise "*" si DEBUG=False

**Solution:**

```python
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]

if not ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set in production (DEBUG=False)"
    )
```

#### 🔴 CRITIQUE 3: Base SQLite en production

```python
# settings/base.py:130-135
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # ❌ INADAPTÉ PRODUCTION
    }
}
```

**Problèmes SQLite production:**
- Pas de concurrence (locks fichier)
- Corruption facile si crash
- Pas de backup automatique
- Perte de données possible

**Solution PostgreSQL:**

```python
# settings/prod.py
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}

# Exemple DATABASE_URL:
# postgresql://user:pass@host:5432/netexpress?sslmode=require
```

**Migration SQLite → PostgreSQL:**

```bash
# 1. Dump data
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.Permission \
    > data_backup.json

# 2. Configurer PostgreSQL
export DATABASE_URL="postgresql://..."

# 3. Migrate
python manage.py migrate

# 4. Load data
python manage.py loaddata data_backup.json
```

#### 🔴 CRITIQUE 4: Fichiers media non protégés

```python
# settings/base.py:163-164
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# urls.py:29-31
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Problème:** En production, fichiers servis directement par web server

**Impact:** PDFs factures/devis accessibles publiquement sans authentification

**Exemple:**
```
https://netexpress.fr/media/devis/DEV-2025-001.pdf  # ❌ Accessible à tous!
https://netexpress.fr/media/factures/FAC-2025-042.pdf  # ❌ Données sensibles
```

**Solution 1 (Django serve avec auth):**

```python
# urls.py
from django.urls import re_path
from core.views import protected_media

urlpatterns = [
    # ...
    re_path(r'^media/(?P<path>.*)$', protected_media, name='protected_media'),
]

# core/views.py
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
import os

@login_required
def protected_media(request, path):
    # Vérifier permissions selon le dossier
    if path.startswith('devis/') or path.startswith('factures/'):
        # Vérifier que l'utilisateur est staff
        if not request.user.is_staff:
            raise PermissionDenied

    file_path = settings.MEDIA_ROOT / path
    if not os.path.exists(file_path):
        raise Http404

    return FileResponse(open(file_path, 'rb'))
```

**Solution 2 (S3 avec signed URLs):**

```python
# settings/prod.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
AWS_QUERYSTRING_AUTH = True  # URLs signées
AWS_QUERYSTRING_EXPIRE = 3600  # Expiration 1h
```

### 9.2 Configuration production (settings/prod.py)

```python
from .base import *

DEBUG = False

# ✅ Headers sécurité
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Points forts:**

✅ **HSTS** 1 an (31536000 secondes)
✅ **SSL redirect** forcé
✅ **Cookies sécurisés** (HTTPS uniquement)

**Manquants:**

```python
# À AJOUTER:

# Content Security Policy
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# Session
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24h

# CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django_errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Admins
ADMINS = [
    ('Admin', env('ADMIN_EMAIL')),
]
MANAGERS = ADMINS
```

### 9.3 CSRF & XSS

**Protection CSRF:**

```python
# settings/base.py:95
MIDDLEWARE = [
    # ...
    "django.middleware.csrf.CsrfViewMiddleware",  # ✅ Présent
]
```

**Templates:**

```html
<!-- contact/contact.html:14 -->
<form method="post" novalidate class="contact-form">
  {% csrf_token %}  <!-- ✅ Token CSRF présent -->
```

✅ **Bon:** Protection CSRF active

**Protection XSS:**

```html
<!-- Tous les templates utilisent {{ }} -->
<td>{{ inv.number }}</td>  <!-- ✅ Auto-escaped -->
<td>{{ inv.total_ttc }} €</td>
```

✅ **Bon:** Auto-escaping Django actif par défaut

**⚠️ Attention:**

```html
<!-- Si utilisation de |safe: -->
{{ message.body|safe }}  <!-- ❌ DANGEREUX si body = user input -->

<!-- Devrait utiliser: -->
{{ message.body|linebreaks }}  <!-- ✅ Échappe + conserve sauts ligne -->
```

### 9.4 SQL Injection

**Django ORM utilisé partout:**

```python
# devis/views.py:159
quote = get_object_or_404(Quote, pk=pk)  # ✅ Paramétrisé
```

✅ **Bon:** Pas de requêtes SQL brutes détectées

**⚠️ Si requêtes raw futures:**

```python
# ❌ DANGER:
Quote.objects.raw(f"SELECT * FROM quote WHERE id = {request.GET['id']}")

# ✅ BON:
Quote.objects.raw("SELECT * FROM quote WHERE id = %s", [request.GET['id']])
```

### 9.5 Checklist sécurité production

| Check | Status | Action |
|-------|--------|--------|
| SECRET_KEY en variable env | ✅ | Valider longueur min 50 |
| DEBUG = False | ✅ | OK |
| ALLOWED_HOSTS configuré | ⚠️ | Ajouter validation non-vide |
| Base PostgreSQL | ❌ | Migrer depuis SQLite |
| HTTPS forcé | ✅ | OK |
| Cookies sécurisés | ✅ | OK |
| HSTS activé | ✅ | OK |
| CSP headers | ❌ | Ajouter middleware django-csp |
| Fichiers media protégés | ❌ | Implémenter auth view |
| Credentials git history | ❌ | Nettoyer avec filter-branch |
| Rate limiting | ❌ | Ajouter django-ratelimit |
| Monitoring erreurs | ❌ | Configurer Sentry |
| Logs structurés | ❌ | Configurer LOGGING |
| Backups DB automatiques | ❌ | Script cron + S3 |
| Celery sécurisé | ⚠️ | Configurer authentification Redis |

---

## 10. TESTS ET QUALITÉ DU CODE

### 10.1 Tests existants

**Fichier:** `tests/test_models.py` (100 lignes)

```python
import pytest
from django.urls import reverse
from services.models import Category, Service
from factures.models import Invoice
from tasks.models import Task

pytestmark = pytest.mark.django_db

def test_category_get_absolute_url():
    """get_absolute_url doit générer URL avec slug"""
    cat = Category.objects.create(slug="peinture", name="Peinture")
    url = cat.get_absolute_url()
    base = reverse("services:list")
    assert url.startswith(base)
    assert f"category={cat.slug}" in url

def test_invoice_number_unique():
    """Factures même année = numéros séquentiels"""
    inv1 = Invoice.objects.create(issue_date=date.today())
    inv2 = Invoice.objects.create(issue_date=date.today())
    assert inv1.number.endswith("001")
    assert inv2.number.endswith("002")

# ... 8 autres tests
```

**Analyse:**

✅ **Pytest** - Framework moderne
✅ **pytest-django** - Plugin Django
✅ **Tests fonctionnels** - get_absolute_url, numérotation, slugs

**Couverture:**

```
Total tests: 10
Modèles testés: Category, Service, Task, Invoice (4/12 = 33%)
Vues testées: 0
Forms testées: 0
Services testés: 0
```

**Problèmes:**

⚠️ **1. Couverture insuffisante (33% modèles seulement)**

Manquent:
- Quote, QuoteItem, Client
- Contact/Message
- EmailMessage
- Toutes les vues
- Services (PremiumEmailService, PdfService)
- Tâches Celery

⚠️ **2. Pas de tests d'intégration**

Scénarios à tester:
- Création devis → Conversion facture → Génération PDF → Envoi email
- Formulaire contact → Notification admin
- Upload photos devis

⚠️ **3. Pas de tests API**

Si API future (DRF), prévoir:
```python
def test_quote_api_create():
    response = client.post('/api/quotes/', data={...})
    assert response.status_code == 201
```

### 10.2 Recommandations tests

**Objectif:** Atteindre 80% de couverture critique

**Phase 1 (Sprint 1 semaine):**

```python
# tests/test_models_complete.py
def test_quote_generate_pdf():
    """Génération PDF devis fonctionne"""
    quote = QuoteFactory()
    pdf_bytes = quote.generate_pdf(attach=False)
    assert len(pdf_bytes) > 1000  # PDF non vide
    assert pdf_bytes.startswith(b'%PDF')

def test_invoice_compute_totals():
    """Calcul totaux avec remise"""
    invoice = InvoiceFactory()
    InvoiceItemFactory(invoice=invoice, quantity=2, unit_price=100, tax_rate=20)
    invoice.discount = Decimal('20.00')
    invoice.compute_totals()
    assert invoice.total_ht == Decimal('180.00')  # 200 - 20
    assert invoice.total_ttc == Decimal('216.00')  # 180 * 1.2

# tests/test_forms.py
def test_contact_form_valid():
    form_data = {
        'topic': 'bricolage',
        'full_name': 'Test User',
        'email': 'test@example.com',
        'phone': '0594301234',
        'street': '1 rue Test',
        'city': 'Cayenne',
        'zip_code': '97300',
        'body': 'Message test',
    }
    form = ContactForm(data=form_data)
    assert form.is_valid()

# tests/test_services.py
def test_premium_email_service_invoice():
    """Envoi email facture avec PDF"""
    invoice = InvoiceFactory()
    service = PremiumEmailService()

    with patch('django.core.mail.EmailMultiAlternatives.send') as mock_send:
        service.send_invoice_notification(invoice)
        mock_send.assert_called_once()

        # Vérifier PDF attaché
        call_args = mock_send.call_args
        # ... assertions attachments

# tests/test_views.py
def test_contact_view_post_success(client, mailoutbox):
    """Formulaire contact crée message et envoie email"""
    response = client.post('/contact/', data={...})
    assert response.status_code == 302  # Redirect
    assert Message.objects.count() == 1
    # Email admin envoyé
    assert len(mailoutbox) == 1
```

**Phase 2 (Sprint 2 semaines):**

```python
# tests/test_integration.py
@pytest.mark.django_db
def test_quote_to_invoice_workflow():
    """Workflow complet: devis → facture → PDF → email"""
    # 1. Créer devis
    quote = QuoteFactory()
    QuoteItemFactory.create_batch(3, quote=quote)

    # 2. Convertir en facture
    invoice = Invoice.create_from_quote(quote)
    assert invoice.invoice_items.count() == 3

    # 3. Générer PDF
    pdf_bytes = invoice.generate_pdf()
    assert pdf_bytes

    # 4. Envoyer email
    with patch('core.services.email_service.EmailMultiAlternatives') as mock:
        PremiumEmailService().send_invoice_notification(invoice)
        mock.assert_called()
```

**Configuration pytest (pytest.ini):**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = netexpress.settings.dev
python_files = tests.py test_*.py *_tests.py
addopts =
    --cov=src_netexpress
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

**CI/CD (.github/workflows/tests.yml):**

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements/dev.txt
      - run: pytest --cov
      - uses: codecov/codecov-action@v3
```

---

## 11. POINTS FORTS IDENTIFIÉS

### 11.1 Architecture

✅ **Structure Django propre** - Apps bien séparées (DRY)
✅ **Services layer** - Logique métier découplée
✅ **Settings modulaires** - base.py / dev.py / prod.py
✅ **Requirements structurés** - base / dev / prod
✅ **Templates réutilisables** - Héritage base.html

### 11.2 Fonctionnalités

✅ **Génération PDF professionnelle** (WeasyPrint + ReportLab)
✅ **Emails HTML brandés** avec templates
✅ **Tâches asynchrones** (Celery)
✅ **Numérotation automatique** devis/factures
✅ **Conversion devis → facture** atomique

### 11.3 Qualité code

✅ **Type hints** Python modernes
✅ **Docstrings complètes** (modèles, services)
✅ **Transactions atomiques** (factures)
✅ **Validations métier** (tâches)
✅ **Index DB optimisés** (performances)

### 11.4 Sécurité

✅ **Variables environnement** (.env)
✅ **HTTPS forcé** en production
✅ **CSRF protection** active
✅ **ORM Django** (anti-SQL injection)
✅ **WhiteNoise** (static files sécurisés)

### 11.5 UX/UI

✅ **Design moderne** (variables CSS, animations)
✅ **Responsive** (mobile-friendly)
✅ **Jazzmin admin** (interface intuitive)
✅ **Autocomplétion** (ville ↔ code postal)
✅ **Feedback visuel** (messages, KPIs)

---

## 12. PROBLÈMES CRITIQUES

### 12.1 Sécurité 🔴

| # | Problème | Impact | Localisation |
|---|----------|--------|--------------|
| 1 | **Credentials email hardcodés** | Fuite données, violation RGPD | `settings/base.py:226-232` |
| 2 | **SQLite en production** | Corruption DB, perte données | `settings/base.py:130-135` |
| 3 | **Fichiers media publics** | Factures/devis accessibles sans auth | `urls.py`, config media |
| 4 | **Pas de rate limiting** | Attaques brute-force formulaires | Toutes les vues publiques |
| 5 | **Historique Git compromis** | Credentials dans history | Repo Git |

### 12.2 Dépendances 🔴

| # | Problème | Impact | Action |
|---|----------|--------|--------|
| 1 | **WeasyPrint absent requirements** | ImportError runtime | Ajouter à base.txt |
| 2 | **Celery absent requirements** | ImportError runtime | Ajouter à base.txt |
| 3 | **Redis absent requirements** | Celery ne démarre pas | Ajouter à base.txt |
| 4 | **Pillow absent requirements** | Upload images échoue | Ajouter à base.txt |

### 12.3 Architecture 🔴

| # | Problème | Impact | Localisation |
|---|----------|--------|--------------|
| 1 | **PDF dans modèles (236 lignes)** | Violation SRP, maintenance difficile | `devis/models.py:225-461` |
| 2 | **Hexcore incomplet** | Confusion architecture | `hexcore/` non utilisé |
| 3 | **Pas de transactions** | Incohérence données | `devis/views.py:102-113` |
| 4 | **Race condition devis** | Numéros dupliqués possibles | `devis/models.py:171-186` |

### 12.4 Qualité code 🟠

| # | Problème | Impact | Localisation |
|---|----------|--------|--------------|
| 1 | **Couverture tests 10%** | Bugs non détectés | `/tests/` |
| 2 | **Exceptions trop larges** | Masque erreurs réelles | `contact/views.py:52-55` |
| 3 | **Pas de logging** | Debug production impossible | Tout le projet |
| 4 | **Champs redondants** | Dette technique | `factures/models.py:165` |

### 12.5 Ergonomie 🟠

| # | Problème | Impact | Localisation |
|---|----------|--------|--------------|
| 1 | **Messages erreur génériques** | UX confuse | Tous les formulaires |
| 2 | **Bug label HTML** | Accessibilité cassée | `contact.html:45` |
| 3 | **Pas de filtres dashboard** | Navigation difficile | `dashboard.html` |
| 4 | **Tarifs urgence cachés** | Client ne comprend pas prix | `home.html:132-136` |

---

## 13. RECOMMANDATIONS PRIORISÉES

### 13.1 URGENT (Avant mise en production - Semaine 1)

#### 1. Sécurité - Nettoyer credentials

```bash
# 1.1 Supprimer credentials du code
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch netexpress/settings/base.py" \
  --prune-empty -- --all

# 1.2 Créer .env.example
cat > .env.example <<EOF
DJANGO_SECRET_KEY=generer-avec-djecrety.ir
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DATABASE_URL=postgresql://user:pass@host:5432/netexpress
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=contact@votre-domaine.com
EMAIL_HOST_PASSWORD=mot-de-passe-securise
CELERY_BROKER_URL=redis://localhost:6379/0
SITE_URL=https://votre-domaine.com
EOF

# 1.3 Modifier settings/base.py
# Supprimer tous les default= avec credentials
```

**Charge:** 0.5 jour

#### 2. Dépendances - Compléter requirements

```txt
# requirements/base.txt - AJOUTER:
weasyprint>=60.1
celery>=5.3.4
redis>=5.0.1
pillow>=10.1.0
num2words>=0.5.14
```

**Charge:** 0.1 jour

#### 3. Base de données - Migrer PostgreSQL

```bash
# 3.1 Dump SQLite
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.Permission \
    > data_backup_$(date +%Y%m%d).json

# 3.2 Créer DB PostgreSQL
createdb netexpress

# 3.3 Configurer .env
DATABASE_URL=postgresql://user:pass@localhost:5432/netexpress

# 3.4 Migrate
python manage.py migrate

# 3.5 Load data
python manage.py loaddata data_backup_*.json

# 3.6 Vérifier
python manage.py shell
>>> from factures.models import Invoice
>>> Invoice.objects.count()
```

**Charge:** 0.5 jour (+ tests)

#### 4. Validation settings production

```python
# settings/prod.py - AJOUTER:
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set")

if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("SECRET_KEY too short")

if 'postgresql' not in DATABASES['default']['ENGINE']:
    raise ImproperlyConfigured("PostgreSQL required in production")
```

**Charge:** 0.2 jour

**Total semaine 1:** 1.3 jours

### 13.2 IMPORTANT (Post-production - Mois 1)

#### 5. Protection fichiers media

```python
# core/views.py
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.core.exceptions import PermissionDenied

@login_required
def protected_media(request, path):
    # Vérifier permissions
    if path.startswith(('devis/', 'factures/')):
        if not request.user.is_staff:
            raise PermissionDenied

    file_path = settings.MEDIA_ROOT / path
    if not file_path.exists():
        raise Http404

    return FileResponse(file_path.open('rb'), as_attachment=False)

# urls.py
urlpatterns = [
    # ...
    path('media/<path:path>', protected_media, name='protected_media'),
]
```

**Charge:** 1 jour (+ tests)

#### 6. Refactoring PDF dans services

```bash
# 6.1 Créer core/services/quote_pdf_generator.py
# Déplacer code depuis devis/models.py:225-461

# 6.2 Utiliser WeasyPrint au lieu de ReportLab
# Créer templates/pdf/quote_premium.html

# 6.3 Modifier devis/models.py:
def generate_pdf(self, attach: bool = True) -> bytes:
    from core.services.pdf_service import QuotePdfService
    service = QuotePdfService()
    pdf_file = service.generate(self)
    if attach:
        self.pdf.save(pdf_file.filename, ContentFile(pdf_file.content))
    return pdf_file.content
```

**Charge:** 2 jours

#### 7. Transactions atomiques vues

```python
# devis/views.py:admin_quote_edit
from django.db import transaction

if form.is_valid() and formset.is_valid():
    with transaction.atomic():
        form.save()
        formset.save()
        quote.compute_totals()
        # ... reste du code
```

**Charge:** 0.5 jour

#### 8. Amélioration ergonomie

```python
# 8.1 Messages erreur personnalisés
# contact/forms.py
class Meta:
    error_messages = {
        'full_name': {
            'required': 'Merci de renseigner votre nom complet',
        },
        # ... tous les champs
    }

# 8.2 Fix bug label
# templates/contact/contact.html:45
<label for="{{ form.street.id_for_label }}">Rue</label>

# 8.3 Tarifs urgence explicites
# templates/core/home.html
<option value="express" data-markup="15">
    Express (48h) - Supplément +15%
</option>
```

**Charge:** 1 jour

#### 9. Logging production

```python
# settings/prod.py
import os

LOG_DIR = BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

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
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django_errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_all': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file_all', 'file_errors', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file_errors', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file_all'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

**Charge:** 0.5 jour

#### 10. Monitoring (Sentry)

```bash
pip install sentry-sdk
```

```python
# settings/prod.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env("SENTRY_DSN"),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment=env("ENVIRONMENT", default="production"),
)
```

**Charge:** 0.5 jour

**Total mois 1:** 6 jours

### 13.3 AMÉLIORATION CONTINUE (Mois 2-3)

#### 11. Tests automatisés (couverture 80%)

```bash
# 11.1 Tests modèles
tests/test_models_complete.py       # 2 jours
tests/test_forms.py                  # 1 jour
tests/test_views.py                  # 2 jours
tests/test_services.py               # 1 jour
tests/test_integration.py            # 1 jour

# 11.2 CI/CD
.github/workflows/tests.yml          # 0.5 jour
pytest.ini, .coveragerc              # 0.5 jour
```

**Charge:** 8 jours

#### 12. Documentation

```markdown
# docs/
├── README.md                    # Vue d'ensemble
├── INSTALLATION.md              # Setup dev/prod
├── ARCHITECTURE.md              # Architecture technique
├── API.md                       # Si API future
├── DEPLOYMENT.md                # Guide déploiement
├── TROUBLESHOOTING.md           # FAQ
└── guide_utilisateur.md         # Pour admins non-tech
```

**Charge:** 3 jours

#### 13. Optimisations performances

```python
# 13.1 Select related / prefetch
# devis/views.py
quote = Quote.objects.select_related('client').prefetch_related('quote_items')

# 13.2 Pagination dashboard
from django.core.paginator import Paginator
paginator = Paginator(Task.objects.all(), 25)

# 13.3 Cache Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_CACHE_URL'),
    }
}

# 13.4 DB indexes optimisés
# Ajouter index sur colonnes filtrées/triées fréquemment
```

**Charge:** 2 jours

**Total mois 2-3:** 13 jours

---

## 14. PLAN D'ACTION DÉTAILLÉ

### Phase 0: Préparation (Avant démarrage)

```bash
# 1. Backup complet
tar -czf netexpress_backup_$(date +%Y%m%d).tar.gz src/

# 2. Créer branche develop
git checkout -b develop
git push -u origin develop

# 3. Setup environnement dev
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt

# 4. Tests baseline
pytest --cov
# Noter couverture actuelle pour comparaison
```

### Phase 1: URGENT (Semaine 1) - Prêt production

| Jour | Tâche | Responsable | Validation |
|------|-------|-------------|------------|
| J1 | Nettoyer credentials Git | Dev Senior | Code review |
| J1 | Créer .env.example | Dev Senior | - |
| J1 | Compléter requirements/*.txt | Dev Senior | pip install test |
| J2 | Dump SQLite | Dev | Vérifier JSON |
| J2 | Setup PostgreSQL local | Dev | Connexion OK |
| J2 | Migrer données | Dev | Count records |
| J3 | Valider settings/prod.py | Dev Senior | Checklist |
| J3 | Tests manuels complets | QA | Rapport bugs |
| J4 | Fix bugs critiques | Dev | Tests passent |
| J5 | Déploiement staging | DevOps | Smoke tests |

**Livrables:**
- ✅ Code sans credentials
- ✅ PostgreSQL en production
- ✅ Settings production validés
- ✅ Application déployable

### Phase 2: IMPORTANT (Mois 1) - Production stable

**Semaine 2:**
- Protection fichiers media (2j)
- Refactoring PDF (3j)

**Semaine 3:**
- Transactions atomiques (1j)
- Amélioration ergonomie (2j)
- Logging production (1j)
- Monitoring Sentry (1j)

**Semaine 4:**
- Tests manuels complets
- Fix bugs trouvés
- Documentation déploiement

**Livrables:**
- ✅ Fichiers media sécurisés
- ✅ Code PDF refactoré
- ✅ Logs structurés
- ✅ Monitoring actif

### Phase 3: AMÉLIORATION (Mois 2-3) - Production mature

**Mois 2:**
- Tests automatisés (couverture 80%)
- CI/CD GitHub Actions
- Documentation technique

**Mois 3:**
- Optimisations performances
- Documentation utilisateur
- Formation équipe
- Runbook incidents

**Livrables:**
- ✅ Tests automatisés
- ✅ CI/CD fonctionnel
- ✅ Documentation complète
- ✅ Équipe formée

### Timeline global

```
Semaine 1    : URGENT (sécurité + DB)          → Déploiement BETA
Semaines 2-4 : IMPORTANT (refactoring + logs)  → Production STABLE
Mois 2       : Tests + CI/CD                   → Production TESTÉE
Mois 3       : Docs + perf + formation         → Production MATURE
```

### Estimation charges totale

| Phase | Charge dev | Charge QA | Total |
|-------|------------|-----------|-------|
| **URGENT** | 1.5j | 0.5j | **2j** |
| **IMPORTANT** | 6j | 2j | **8j** |
| **AMÉLIORATION** | 13j | 3j | **16j** |
| **TOTAL** | **20.5j** | **5.5j** | **26j** |

**Budget recommandé:** 30 jours (avec marge sécurité)

---

## CONCLUSION

### État actuel

**⚠️ PROTOTYPE AVANCÉ - NON PRÊT PRODUCTION**

Le projet NetExpress présente une **base solide** avec une architecture Django propre, des fonctionnalités métier complètes et un design UI professionnel. Cependant, **plusieurs problèmes critiques** empêchent une mise en production immédiate:

1. 🔴 **Sécurité compromise** (credentials hardcodés)
2. 🔴 **Infrastructure inadaptée** (SQLite production)
3. 🔴 **Dépendances manquantes** (WeasyPrint, Celery, Redis)
4. 🟠 **Tests insuffisants** (10% couverture)
5. 🟠 **Ergonomie perfectible** (utilisateurs non techniques)

### Avec corrections URGENT (Semaine 1)

**✅ DÉPLOYABLE EN PRODUCTION LIMITÉE**

Après corrections de sécurité et migration PostgreSQL, l'application peut être déployée en production pour un usage limité (bêta privée, volume faible).

### Avec plan complet (2-3 mois)

**🌟 APPLICATION PROFESSIONNELLE ROBUSTE**

Avec le plan d'action complet, NetExpress deviendra une **application de production mature** avec:
- Sécurité renforcée
- Infrastructure scalable
- Code maintenable
- Tests automatisés
- Monitoring complet
- Documentation exhaustive

### Recommandation finale

```
┌─────────────────────────────────────────────────┐
│ PLAN RECOMMANDÉ:                                │
│                                                 │
│ 1. Semaine 1: URGENT (2j)                      │
│    → Corrections sécurité critiques            │
│    → Migration PostgreSQL                      │
│    → Déploiement BETA production               │
│                                                 │
│ 2. Mois 1: IMPORTANT (8j)                      │
│    → Refactoring code                          │
│    → Protection données                        │
│    → Logs & monitoring                         │
│    → Production STABLE                         │
│                                                 │
│ 3. Mois 2-3: AMÉLIORATION (16j)                │
│    → Tests automatisés (80%)                   │
│    → CI/CD                                     │
│    → Documentation                             │
│    → Production MATURE                         │
│                                                 │
│ Budget total: 26-30 jours                      │
└─────────────────────────────────────────────────┘
```

### Priorités immédiates

**Si mise en production urgente:**
1. Supprimer credentials du code (0.5j)
2. Migrer PostgreSQL (0.5j)
3. Valider settings production (0.2j)
4. Tests manuels complets (1j)
5. **Déployer en BETA limitée** (utilisateurs de confiance)

**Pour production robuste:**
Suivre le plan complet sur 2-3 mois.

---

**Fin du rapport**

*Pour questions ou clarifications, contacter l'équipe d'audit.*
