# Synthèse Inter-Agents - NetExpress

**Version:** 1.0  
**Date:** 2025-01-27  
**Pour:** Tous les agents IA travaillant sur NetExpress

---

## Rôle de l'Architecte Principal

L'architecte principal (ce document) :
- ✅ **Définit** l'architecture globale
- ✅ **Valide** les choix structurants
- ✅ **Arbitre** les conflits entre propositions
- ✅ **Coordonne** les autres agents
- ❌ **Ne produit PAS** de code applicatif

---

## Principes fondamentaux

### 1. Pragmatisme avant tout

**Règle** : Solutions simples et efficaces, pas de sur-ingénierie.

**Exemples** :
- ✅ Utiliser Django ORM directement plutôt qu'un repository pattern complexe
- ✅ Éviter les abstractions inutiles
- ✅ Préférer la lisibilité à la "pureté" architecturale

**À éviter** :
- ❌ Patterns complexes sans bénéfice clair
- ❌ Over-engineering pour des cas d'usage hypothétiques
- ❌ Refactoring "pour le plaisir"

---

### 2. Séparation stricte des responsabilités

**Règle** : Chaque application Django gère un domaine métier distinct.

**Applications et responsabilités** :

| Application | Responsabilité | Ne doit PAS |
|-------------|----------------|-------------|
| `accounts` | Utilisateurs, profils, authentification | Logique métier business |
| `core` | Portails, notifications, routing | Logique métier spécifique |
| `devis` | Devis uniquement | Factures (utiliser la conversion) |
| `factures` | Factures uniquement | Devis (utiliser la conversion) |
| `tasks` | Tâches et planning | Gestion des utilisateurs |
| `messaging` | Messagerie interne | Notifications UI (utiliser core) |
| `services` | Catalogue de services | Logique de devis/factures |

**Règle d'or** : Si une fonctionnalité touche plusieurs apps, elle doit être dans `core/`.

---

### 3. Orientation métier

**Règle** : L'architecture suit les processus métier, pas l'inverse.

**Exemples** :
- ✅ Workflow devis → facture suit le processus réel
- ✅ Portails séparés selon les rôles métier
- ✅ Notifications selon les événements métier

---

## Standards de code

### Structure des fichiers

```
<app>/
├── models.py          # Modèles Django
├── views.py           # Vues (ou views/ pour plusieurs fichiers)
├── urls.py            # URLs
├── admin.py           # Configuration admin
├── forms.py           # Formulaires (si nécessaire)
├── services.py        # Services simples (1 fichier)
├── services/          # Services complexes (multi-fichiers)
│   ├── __init__.py
│   └── service_name.py
├── signals.py         # Signaux Django (si nécessaire)
└── templates/<app>/    # Templates
```

### Nommage

- **Modèles** : PascalCase (`Quote`, `InvoiceItem`)
- **Vues** : snake_case (`client_dashboard`, `admin_create_quote`)
- **Services** : snake_case (`create_quote`, `send_invoice_email`)
- **URLs** : kebab-case dans les URLs (`/admin-dashboard/`), snake_case dans les noms (`admin_dashboard`)

### Imports

```python
# Ordre recommandé :
# 1. Standard library
# 2. Third-party
# 3. Django
# 4. Local apps

from datetime import date
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User

from core.models import UINotification
from devis.models import Quote
```

---

## Contrôle d'accès

### Rôles utilisateur

| Rôle | Code | Portail | Accès |
|------|------|---------|-------|
| Client | `client` | `/client/` | Dashboard client, devis, factures |
| Ouvrier | `worker` | `/worker/` | Tâches assignées, planning |
| Admin Business | `admin_business` | `/admin-dashboard/` | Gestion complète + lecture `/gestion/` |
| Admin Technique | `admin_technical` | `/gestion/` | Django Admin complet |

### Vérification des permissions

**Dans les vues** :
```python
from accounts.models import Profile

def ma_vue(request):
    if request.user.profile.role != Profile.ROLE_ADMIN_BUSINESS:
        raise PermissionDenied
    # ...
```

**Décorateurs disponibles** :
- `@require_role('admin_business')` (dans `core/decorators_v2.py`)
- `@require_portal_access` (dans `core/decorators_v2.py`)

**Middleware** :
- `RoleBasedAccessMiddleware` redirige automatiquement selon le rôle
- Ne pas contourner le middleware dans les vues

---

## Gestion des erreurs

### Principes

1. **Erreurs utilisateur** : Messages clairs et actionnables
2. **Erreurs système** : Logs détaillés, message générique à l'utilisateur
3. **Erreurs critiques** : Notification immédiate aux admins

### Pattern recommandé

```python
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def ma_vue(request):
    try:
        # Code métier
        result = service.doSomething()
        messages.success(request, "Opération réussie")
    except ValidationError as e:
        # Erreur utilisateur
        messages.error(request, f"Erreur de validation : {e}")
    except Exception as e:
        # Erreur système
        logger.error(f"Erreur dans ma_vue : {e}", exc_info=True)
        messages.error(request, "Une erreur est survenue. Veuillez réessayer.")
```

---

## Tests

### Priorités

1. **Tests d'intégration** : Workflows critiques (devis → facture, création compte)
2. **Tests unitaires** : Services et logique métier complexe
3. **Tests de régression** : Bugs corrigés

### Structure

```
tests/
├── test_<feature>_units.py      # Tests unitaires
├── test_<feature>_properties.py # Tests de propriétés/comportement
└── test_<feature>_integration.py # Tests d'intégration
```

### Exemples

**Test unitaire** :
```python
def test_create_quote():
    quote = Quote.objects.create(...)
    assert quote.status == Quote.STATUS_DRAFT
```

**Test d'intégration** :
```python
def test_quote_to_invoice_workflow():
    # Créer devis → Valider → Convertir en facture
    quote = create_quote(...)
    quote.validate()
    invoice = convert_to_invoice(quote)
    assert invoice.quote == quote
```

---

## Documentation

### Documentation du code

**Docstrings** : Obligatoires pour :
- Toutes les fonctions publiques
- Toutes les classes
- Méthodes complexes

**Format** :
```python
def create_quote(client, items):
    """
    Crée un nouveau devis pour un client.
    
    Args:
        client: Instance Client
        items: Liste de QuoteItem
        
    Returns:
        Quote: Devis créé
        
    Raises:
        ValidationError: Si les données sont invalides
    """
```

### Documentation des décisions

**Quand documenter** :
- Nouvelle fonctionnalité majeure
- Choix technique non évident
- Workaround ou solution temporaire

**Où documenter** :
- `docs/DECISIONS.md` pour les décisions architecturales
- Commentaires dans le code pour les détails d'implémentation

---

## Processus de développement

### Avant de commencer

1. ✅ Lire `docs/ARCHITECTURE.md`
2. ✅ Vérifier `docs/FEUILLE_DE_ROUTE.md` pour les priorités
3. ✅ Consulter `docs/DECISIONS.md` pour les décisions existantes

### Pendant le développement

1. ✅ Respecter les principes architecturaux
2. ✅ Suivre les standards de code
3. ✅ Tester localement avant commit
4. ✅ Documenter les décisions importantes

### Avant de proposer une modification

1. ✅ Vérifier la cohérence avec l'architecture existante
2. ✅ Évaluer l'impact sur les autres modules
3. ✅ Consulter l'architecte pour les changements structurants

---

## Résolution de conflits

### Conflit entre propositions

**Processus** :
1. Documenter les deux propositions
2. Évaluer selon les principes (pragmatisme, séparation responsabilités)
3. Arbitrage par l'architecte si nécessaire

**Critères d'arbitrage** :
- Simplicité > Complexité
- Cohérence avec l'existant > Innovation
- Besoin métier > Élégance technique

### Conflit avec l'architecture existante

**Si une fonctionnalité ne rentre pas dans l'architecture** :
1. ✅ Discuter avec l'architecte AVANT d'implémenter
2. ✅ Proposer une évolution de l'architecture si nécessaire
3. ❌ Ne pas contourner l'architecture sans validation

---

## Checklist avant soumission

Avant de proposer du code ou une modification :

- [ ] Code respecte les standards de nommage
- [ ] Imports organisés correctement
- [ ] Contrôle d'accès implémenté si nécessaire
- [ ] Gestion d'erreurs appropriée
- [ ] Tests ajoutés (si fonctionnalité nouvelle)
- [ ] Documentation à jour
- [ ] Pas de dépendances circulaires
- [ ] Cohérent avec l'architecture existante

---

## Contacts et ressources

### Documents de référence

- `docs/ARCHITECTURE.md` : Architecture détaillée
- `docs/FEUILLE_DE_ROUTE.md` : Priorités et planning
- `docs/DECISIONS.md` : Décisions architecturales

### Points d'attention

⚠️ **À éviter** :
- Modifications non documentées de l'architecture
- Dépendances circulaires entre apps
- Code dupliqué sans justification
- Sur-ingénierie

✅ **À favoriser** :
- Solutions simples et pragmatiques
- Code lisible et maintenable
- Documentation claire
- Tests pertinents

---

**Ce document est vivant** : Il sera mis à jour selon l'évolution du projet.  
**Dernière mise à jour** : 2025-01-27

