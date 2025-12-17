# Analyse Rigoureuse du Projet NetExpress

**Date :** 17 décembre 2025
**Projet :** NetExpress - Application Django pour services de nettoyage
**Contexte :** Revue de code pour développeur intermédiaire

---

## RESUME EXECUTIF

| Domaine | Note | Priorité |
|---------|------|----------|
| **Sécurité** | CRITIQUE | Urgente |
| **Architecture** | Bon | - |
| **Back-end** | Satisfaisant | Moyenne |
| **Front-end** | Satisfaisant | Moyenne |
| **SEO** | Insuffisant | Haute |
| **Performance** | Moyen | Moyenne |
| **Tests** | Insuffisant | Haute |
| **Documentation** | Bon | - |

---

## 1. SECURITE - PROBLEMES CRITIQUES

### 1.1 Secrets exposés dans le dépôt (CRITIQUE)

**Fichier:** `src/src_netexpress/.env` (ligne 19)

```
EMAIL_HOST_PASSWORD=ymgxtrrstpqwkkwk
SECRET_KEY=change-me_testing-in-production
```

**Problèmes identifiés :**
- Le fichier `.env` est versionné dans git avec des secrets en clair
- Mot de passe d'application Gmail exposé publiquement
- `SECRET_KEY` par défaut non sécurisée ("change-me_testing-in-production")

**Impact :** Un attaquant peut usurper l'identité email de l'entreprise, envoyer des emails frauduleux, et potentiellement compromettre les sessions Django.

**Actions immédiates requises :**
1. Révoquer immédiatement le mot de passe d'application Gmail
2. Générer une nouvelle `SECRET_KEY` cryptographiquement sécurisée
3. Ajouter `.env` au `.gitignore`
4. Supprimer le fichier `.env` de l'historique git (avec `git filter-branch` ou `bfg`)

### 1.2 Configuration de sécurité Django incomplète

**Fichier:** `src/src_netexpress/netexpress/settings/base.py`

**Manquants :**
```python
# Ces paramètres de sécurité essentiels ne sont pas configurés :
SECURE_SSL_REDIRECT = True  # Manquant
SECURE_HSTS_SECONDS = 31536000  # Manquant
SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Manquant
SECURE_HSTS_PRELOAD = True  # Manquant
SESSION_COOKIE_SECURE = True  # Manquant
CSRF_COOKIE_SECURE = True  # Manquant
SECURE_CONTENT_TYPE_NOSNIFF = True  # Manquant
SECURE_BROWSER_XSS_FILTER = True  # Manquant (déprécié mais utile)
X_FRAME_OPTIONS = 'DENY'  # Présent via middleware mais pas explicite
```

### 1.3 Validation des entrées utilisateur

**Fichier:** `src/src_netexpress/devis/forms.py` (lignes 42-52)

```python
phone = forms.CharField(
    label="Téléphone",
    max_length=50,
    widget=forms.TextInput(...)
)
```

**Problème :** Aucune validation du format de téléphone - un utilisateur peut entrer n'importe quoi.

**Solution recommandée :**
```python
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r'^(?:(?:\+|00)594|0)[1-9](?:[0-9]{8})$',
    message="Entrez un numéro de téléphone valide (Guyane)"
)

phone = forms.CharField(
    validators=[phone_validator],
    ...
)
```

### 1.4 Protection CSRF insuffisante dans JavaScript

**Fichier:** `src/src_netexpress/static/js/main.js`

Le code ne gère pas l'envoi du token CSRF pour les requêtes AJAX futures. Si des appels fetch/XMLHttpRequest sont ajoutés, ils seront vulnérables.

### 1.5 Upload de fichiers sans validation stricte

**Fichier:** `src/src_netexpress/devis/views.py` (lignes 29-33)

```python
files = request.FILES.getlist("photos")
for f in files:
    photo = QuoteRequestPhoto.objects.create(image=f)
```

**Problèmes :**
- Pas de validation de la taille maximale des fichiers
- Pas de validation du type MIME réel (pas seulement l'extension)
- Pas de limite sur le nombre de fichiers uploadés

---

## 2. ARCHITECTURE ET BACK-END

### 2.1 Points positifs

- **Architecture hexagonale partielle** (`hexcore/`) : Bonne initiative de séparation des préoccupations
- **Utilisation de signals** pour découpler la logique métier
- **Services dédiés** (`email_service.py`, `pdf_service.py`)
- **Gestion des transactions** dans `Invoice.save()` avec `select_for_update()`
- **Génération automatique de slugs** avec gestion des collisions
- **Celery intégré** pour les tâches asynchrones

### 2.2 Points à améliorer

#### 2.2.1 Code dupliqué dans les modèles

**Fichiers:** `devis/models.py` et `factures/models.py`

La logique de génération de numéros est dupliquée :
```python
# Dans Quote.save() (devis/models.py:171-186)
prefix = f"DEV-{year}-"
last_number = Quote.objects.filter(number__startswith=prefix)...

# Dans Invoice.save() (factures/models.py:205-230)
prefix = f"FAC-{year}-"
last = Invoice.objects.select_for_update().filter(number__startswith=prefix)...
```

**Recommandation :** Créer un mixin ou une fonction utilitaire partagée.

#### 2.2.2 Méthode `generate_pdf` trop volumineuse

**Fichier:** `src/src_netexpress/devis/models.py` (lignes 225-461)

La méthode `Quote.generate_pdf()` fait **237 lignes**. Elle viole le principe de responsabilité unique.

**Recommandation :** Extraire vers un service dédié `QuotePdfGenerator` (comme c'est fait pour les factures).

#### 2.2.3 Gestion d'erreurs silencieuse

**Fichier:** `src/src_netexpress/devis/views.py` (lignes 109-124)

```python
try:
    quote.compute_totals()
except Exception:
    pass  # Erreur avalée silencieusement

try:
    if quote.status == Quote.QuoteStatus.SENT:
        ...
except Exception:
    pass  # Erreur avalée silencieusement
```

**Problème :** Les erreurs sont masquées, rendant le débogage impossible.

**Recommandation :**
```python
import logging
logger = logging.getLogger(__name__)

try:
    quote.compute_totals()
except Exception as e:
    logger.exception("Échec du calcul des totaux pour le devis %s", quote.pk)
```

#### 2.2.4 Queries N+1 potentielles

**Fichier:** `src/src_netexpress/devis/models.py` (ligne 211)

```python
for item in self.quote_items.all():  # Query pour chaque item
    qty = Decimal(str(getattr(item, "quantity", 0) or 0))
```

**Recommandation :** Utiliser `select_related` ou `prefetch_related` dans les vues.

#### 2.2.5 Absence de type hints cohérents

Certaines fonctions ont des type hints, d'autres non. L'adoption devrait être systématique.

---

## 3. FRONT-END

### 3.1 Points positifs

- **CSS Variables** bien utilisées pour la thématisation
- **Mobile-first approach** avec media queries appropriées
- **Animations CSS subtiles** (`.animated-border`)
- **Vanilla JS** léger sans dépendance framework lourde

### 3.2 Points à améliorer

#### 3.2.1 Accessibilité (A11Y) insuffisante

**Fichier:** `src/src_netexpress/templates/base.html`

```html
<nav id="primary-navigation" class="nav" hidden>
```

**Problèmes :**
- Manque de `role="navigation"` explicite
- Pas de skip-link pour la navigation au clavier
- Contrastes de couleurs non vérifiés (WCAG 2.1 AA)

**Fichier:** `src/src_netexpress/templates/core/home.html` (lignes 101-113)

```html
<button class="option active" type="button" data-service-value="nettoyage">
```

Les boutons de sélection de service n'ont pas d'attributs ARIA pour indiquer l'état sélectionné.

**Recommandation :**
```html
<button class="option active" type="button"
        role="radio"
        aria-checked="true"
        data-service-value="nettoyage">
```

#### 3.2.2 CSS non minifié et dupliqué

**Fichiers:** `base.css` et `style.css`

Ces deux fichiers définissent des variables CSS similaires mais différentes :
- `base.css`: `--brand: #0f6d4e`
- `style.css`: `--primary-green: #104130`

**Impact :** Incohérence visuelle et maintenance difficile.

#### 3.2.3 JavaScript chargé en bloquant

**Fichier:** `src/src_netexpress/templates/base.html` (lignes 20-21)

```html
<script src="{% static 'js/main.js' %}"></script>
<script src="{% static 'js/forms.js' %}"></script>
```

**Problème :** Les scripts sont dans le `<head>` sans attribut `defer` ou `async`.

**Recommandation :**
```html
<script src="{% static 'js/main.js' %}" defer></script>
<script src="{% static 'js/forms.js' %}" defer></script>
```

#### 3.2.4 Images sans dimensions explicites

**Fichier:** `src/src_netexpress/templates/core/home.html`

```html
<img src="{% static 'img/default_service.jpg' %}" alt="Nettoyage de prestige">
```

**Problème :** Pas d'attributs `width` et `height`, causant du CLS (Cumulative Layout Shift).

#### 3.2.5 Pas de lazy loading pour les images

Les images sous la ligne de flottaison devraient utiliser `loading="lazy"`.

---

## 4. SEO

### 4.1 Points positifs

- Meta description présente dans `base.html`
- URLs sémantiques (`/services/`, `/devis/`, `/contact/`)
- Balises `<title>` personnalisables par page

### 4.2 Points à améliorer

#### 4.2.1 Absence de données structurées

Aucun JSON-LD pour Schema.org n'est présent. Pour une entreprise de services, c'est crucial.

**Recommandation :** Ajouter dans `base.html` :
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Nettoyage Express",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "753, Chemin de la Désirée",
    "addressLocality": "Matoury",
    "postalCode": "97351",
    "addressCountry": "GF"
  },
  "telephone": "+594 594 30 23 68",
  "priceRange": "€€"
}
</script>
```

#### 4.2.2 Absence de sitemap.xml

Aucun sitemap n'est généré. Django offre `django.contrib.sitemaps`.

#### 4.2.3 Absence de robots.txt

Fichier non présent pour guider les crawlers.

#### 4.2.4 Images sans attribut alt descriptif

```html
<img src="{% static 'img/hero_bg.png' %}" alt="Jardin Villa">
```

L'alt "Jardin Villa" n'est pas suffisamment descriptif pour le SEO et l'accessibilité.

#### 4.2.5 Canonical URLs manquantes

Aucune balise `<link rel="canonical">` pour éviter le contenu dupliqué.

---

## 5. PERFORMANCE

### 5.1 Points positifs

- **WhiteNoise** configuré pour servir les fichiers statiques avec compression
- **Celery** pour les tâches asynchrones (emails)
- **Indexes de base de données** définis sur les modèles clés

### 5.2 Points à améliorer

#### 5.2.1 Pas de cache configuré

**Fichier:** `src/src_netexpress/netexpress/settings/base.py`

Aucune configuration de cache Django. Pour un site de services, même un cache en mémoire simple améliorerait les performances.

**Recommandation :**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

#### 5.2.2 Ressources externes bloquantes

**Fichier:** `src/src_netexpress/templates/base.html` (lignes 10-13)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

**Problèmes :**
- Google Fonts et Font Awesome sont des SPOF (Single Point of Failure)
- Chargement bloquant du rendu

**Recommandations :**
1. Self-host les polices critiques
2. Utiliser `font-display: swap` ou `optional`
3. Charger Font Awesome de manière asynchrone ou utiliser un sous-ensemble SVG

#### 5.2.3 Base de données SQLite en production

**Fichier:** `src/src_netexpress/.env` (ligne 8)

```
# DATABASE_URL laissé vide = SQLite en dev
```

SQLite n'est pas adapté à la production pour une application web avec des écritures concurrentes.

#### 5.2.4 Pas de compression des images

Les images dans `/static/img/` ne semblent pas optimisées (format WebP non utilisé).

---

## 6. TESTS

### 6.1 Couverture actuelle

**Fichier:** `src/src_netexpress/tests/test_models.py`

Seuls **6 tests** existent, couvrant :
- `Category.get_absolute_url()`
- `Task.get_absolute_url()`
- `Task.is_due_soon()`
- Unicité des slugs Service/Category
- Séquence des numéros de facture

### 6.2 Couverture manquante (CRITIQUE)

- **Aucun test de vue** (0% de couverture)
- **Aucun test de formulaire**
- **Aucun test d'intégration email**
- **Aucun test de génération PDF**
- **Aucun test de sécurité** (CSRF, permissions)

**Estimation de couverture globale :** ~5%

---

## 7. BONNES PRATIQUES MANQUANTES

### 7.1 Logging

Aucune configuration de logging structuré. Essentiel pour le debugging en production.

### 7.2 Monitoring

Aucune intégration avec des outils de monitoring (Sentry, etc.).

### 7.3 CI/CD

Aucun fichier de configuration CI visible (`.github/workflows/`, `gitlab-ci.yml`, etc.).

### 7.4 Pre-commit hooks

Pas de configuration pour linting automatique (`black`, `isort`, `flake8`).

---

## DIRECTIVES ET PLAN D'ACTION

### PRIORITE 1 - CRITIQUE (À faire immédiatement)

1. **Révoquer et changer tous les secrets exposés**
   - Nouveau mot de passe Gmail (régénérer un "App Password")
   - Nouvelle `SECRET_KEY` Django
   - Invalider toutes les sessions existantes

2. **Sécuriser le dépôt git**
   ```bash
   echo ".env" >> .gitignore
   # Puis purger l'historique avec bfg ou git filter-branch
   ```

3. **Ajouter les headers de sécurité** dans `settings/prod.py`

### PRIORITE 2 - HAUTE (Cette semaine)

4. **Valider les entrées utilisateur**
   - Ajouter des validators pour téléphone, email
   - Limiter la taille et le nombre des uploads

5. **Ajouter des tests critiques**
   - Tests des vues principales
   - Tests de formulaires
   - Au minimum atteindre 40% de couverture

6. **Configurer un sitemap.xml et robots.txt**

### PRIORITE 3 - MOYENNE (Ce mois)

7. **Refactoring du code dupliqué**
   - Extraire la logique de numérotation
   - Simplifier `Quote.generate_pdf()` en service

8. **Optimiser le front-end**
   - Ajouter `defer` aux scripts
   - Lazy loading des images
   - Self-host les polices critiques

9. **Configurer le cache Django**

10. **Migrer vers PostgreSQL** pour la production

### PRIORITE 4 - BASSE (Long terme)

11. **Ajouter Schema.org / JSON-LD**

12. **Configurer CI/CD**
    - Linting automatique
    - Tests automatiques
    - Déploiement automatisé

13. **Améliorer l'accessibilité**
    - Audit WCAG 2.1 AA
    - Skip links
    - ARIA states

14. **Monitoring et alerting**
    - Intégrer Sentry
    - Configurer des logs structurés

---

## CONCLUSION

Ce projet présente une **architecture globalement saine** avec des choix techniques pertinents (Django, Celery, architecture hexagonale partielle). La qualité du code est celle attendue d'un développeur intermédiaire, avec des points forts notables (documentation en français, séparation des préoccupations) mais des **lacunes critiques en sécurité** qui doivent être adressées immédiatement.

Les **secrets exposés dans git constituent un incident de sécurité** nécessitant une action corrective urgente. Une fois cette urgence traitée, le projet peut évoluer sereinement en suivant les recommandations de ce rapport.

**Score global estimé : 55/100**
- Sécurité : 20/100 (critique)
- Architecture : 70/100
- Code quality : 60/100
- Tests : 15/100
- SEO : 40/100
- Performance : 55/100
- Documentation : 75/100

---

*Rapport généré par Claude Code - Revue technique approfondie*
