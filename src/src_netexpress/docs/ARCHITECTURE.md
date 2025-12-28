# Architecture NetExpress

**Version:** 1.0  
**Date:** 2025-01-27  
**Auteur:** Chef de Projet / Architecte Principal

---

## 1. Vision d'ensemble

NetExpress est un mini-ERP professionnel développé avec Django pour une entreprise de services (nettoyage, espaces verts, peinture, bricolage). Le système est conçu pour être **léger, pragmatique et orienté métier**, sans sur-ingénierie.

### Principes architecturaux

1. **Séparation stricte des responsabilités** : Chaque application Django gère un domaine métier distinct
2. **Pragmatisme avant tout** : Solutions simples et efficaces, pas de complexité inutile
3. **Orientation métier** : L'architecture suit les processus métier, pas l'inverse
4. **Évolutivité contrôlée** : Structure modulaire permettant l'ajout de fonctionnalités sans refactoring majeur

---

## 2. Architecture applicative

### 2.1 Structure modulaire

Le projet suit une architecture modulaire Django avec 8 applications principales :

```
netexpress/
├── accounts/          # Gestion des utilisateurs et profils
├── core/              # Fonctionnalités centrales (portails, notifications, routing)
├── devis/             # Gestion des devis
├── factures/          # Gestion des factures
├── tasks/             # Gestion des tâches/planning
├── messaging/         # Système de messagerie interne
├── services/          # Catalogue de services
├── contact/           # Formulaire de contact public
└── hexcore/           # Architecture hexagonale (facturation) - expérimental
```

### 2.2 Applications et responsabilités

#### **accounts** - Gestion des utilisateurs
- **Modèles** : `Profile` (rôles utilisateur)
- **Responsabilités** :
  - Gestion des profils utilisateur avec rôles
  - Middleware de contrôle d'accès basé sur les rôles
  - Création automatique de profils
- **Dépendances** : Aucune (app de base)

#### **core** - Fonctionnalités centrales
- **Modèles** : `ClientDocument`, `UINotification`, `PortalSession`
- **Responsabilités** :
  - Routing des portails (`portal_routing.py`)
  - Système de notifications UI
  - Tracking des sessions utilisateur
  - Vues communes aux portails
- **Dépendances** : `accounts`

#### **devis** - Gestion des devis
- **Modèles** : `Client`, `Quote`, `QuoteItem`, `QuoteRequest`
- **Responsabilités** :
  - Création et gestion des devis
  - Conversion devis → facture
  - Génération PDF des devis
  - Workflow de validation par signature électronique
- **Dépendances** : `services`, `accounts`

#### **factures** - Gestion des factures
- **Modèles** : `Invoice`, `InvoiceItem`
- **Responsabilités** :
  - Création et gestion des factures
  - Génération PDF professionnelle (ReportLab)
  - Workflow de paiement
- **Dépendances** : `devis`

#### **tasks** - Gestion des tâches
- **Modèles** : `Task`
- **Responsabilités** :
  - Création et suivi des tâches
  - Planning et calendrier
  - Attribution aux ouvriers
- **Dépendances** : `accounts`

#### **messaging** - Messagerie interne
- **Modèles** : `EmailMessage`, `MessageThread`
- **Responsabilités** :
  - Communication entre clients, ouvriers et administrateurs
  - Notifications par email
- **Dépendances** : `accounts`, `core`

#### **services** - Catalogue de services
- **Modèles** : `Service`, `Category`
- **Responsabilités** :
  - Catalogue des services proposés
  - Tarification
- **Dépendances** : Aucune

#### **contact** - Contact public
- **Modèles** : `Message`
- **Responsabilités** :
  - Formulaire de contact public
  - Traitement des demandes
- **Dépendances** : Aucune

---

## 3. Architecture des portails

### 3.1 Système multi-portails

NetExpress implémente un système de **4 portails distincts** selon les rôles utilisateur :

| Portail | URL | Rôle | Accès |
|---------|-----|------|-------|
| **Client** | `/client/` | `client` | Dashboard client, devis, factures |
| **Ouvrier** | `/worker/` | `worker` | Tâches assignées, planning |
| **Admin Business** | `/admin-dashboard/` | `admin_business` | Gestion complète + lecture `/gestion/` |
| **Admin Technique** | `/gestion/` | `admin_technical` | Interface Django Admin (Jazzmin) |

### 3.2 Contrôle d'accès

Le middleware `RoleBasedAccessMiddleware` (`accounts/middleware.py`) implémente la logique d'accès :

- **Superuser** : Accès UNIQUEMENT à `/gestion/`
- **Admin Technique** : Accès UNIQUEMENT à `/gestion/`
- **Admin Business** : Accès à `/admin-dashboard/` + lecture seule `/gestion/`
- **Worker** : Accès UNIQUEMENT à `/worker/`
- **Client** : Accès UNIQUEMENT à `/client/`

### 3.3 Routing des portails

Le module `core/portal_routing.py` fournit :
- Détection automatique du portail approprié
- Redirection après connexion
- Validation d'accès aux URLs
- Utilitaires de navigation

---

## 4. Modèle de données

### 4.1 Entités principales

```
User (Django)
  └── Profile (accounts)
      ├── role (client|worker|admin_business|admin_technical)
      └── notification_preferences

Client (devis)
  ├── Quote (devis)
  │   ├── QuoteItem[]
  │   └── QuoteRequest
  └── Invoice (factures)
      └── InvoiceItem[]

Task (tasks)
  ├── assigned_to → User
  └── completed_by → User

EmailMessage (messaging)
  └── MessageThread

Service (services)
  └── Category
```

### 4.2 Relations clés

- **User ↔ Profile** : OneToOne (création automatique)
- **Client ↔ Quote** : OneToMany
- **Quote ↔ Invoice** : OneToOne (conversion)
- **User ↔ Task** : ManyToMany (assigned_to, completed_by)
- **User ↔ EmailMessage** : ManyToMany (expéditeur, destinataires)

---

## 5. Services et logique métier

### 5.1 Services applicatifs

Les services sont organisés par domaine :

```
core/services/
├── email_service.py          # Envoi d'emails
├── notification_service.py   # Notifications UI
├── document_service.py       # Gestion documents
└── brevo_campaign_service.py # Campagnes email (Brevo)

devis/services.py            # Logique métier devis
factures/services/           # Logique métier factures
tasks/services.py            # Logique métier tâches
```

### 5.2 Architecture hexagonale (expérimental)

Le module `hexcore/` implémente une architecture hexagonale pour la facturation :

```
hexcore/
├── domain/          # Entités métier pures (Invoice, InvoiceItem)
├── ports/           # Interfaces (InvoiceRepository, PdfGenerator)
└── services/        # Services applicatifs (InvoiceService)
```

**État actuel** : Expérimental, non complètement intégré.  
**Recommandation** : Évaluer l'utilité avant généralisation.

---

## 6. Tâches asynchrones (Celery)

### 6.1 Configuration

- **Broker** : Redis
- **Queues** : `messaging`, `documents`, `notifications`
- **Time limits** : 60s (soft), 120s (hard)

### 6.2 Tâches définies

- `messaging.tasks.*` : Envoi d'emails de messagerie
- `devis.tasks.*` : Génération PDF devis
- `factures.tasks.*` : Génération PDF factures
- `contact.tasks.*` : Notifications de contact

---

## 7. Sécurité

### 7.1 Authentification

- Django Auth standard
- Middleware de contrôle d'accès par rôle
- Redirection automatique selon le rôle

### 7.2 Autorisations

- **Décorateurs** : `@require_role`, `@require_portal_access`
- **Middleware** : `RoleBasedAccessMiddleware`
- **Vues** : Validation dans chaque vue de portail

### 7.3 Protection CSRF

- CSRF activé par défaut
- `CSRF_TRUSTED_ORIGINS` configuré pour production

---

## 8. Génération de documents

### 8.1 PDF - Devis

- **Bibliothèque** : WeasyPrint
- **Template** : HTML → PDF
- **Localisation** : `devis/templates/pdf/`

### 8.2 PDF - Factures

- **Bibliothèque** : ReportLab
- **Génération** : Programmatique (code Python)
- **Fonctionnalités** : Logo, QR code paiement, pagination

---

## 9. Notifications

### 9.1 Notifications UI

- **Modèle** : `UINotification` (core)
- **Types** : task_completed, quote_validated, invoice_created, etc.
- **Affichage** : HTMX pour mise à jour dynamique

### 9.2 Notifications Email

- **Backend** : Brevo (SMTP)
- **Templates** : `templates/emails/`
- **Tâches** : Celery pour envoi asynchrone

---

## 10. Configuration et déploiement

### 10.1 Settings modulaires

```
netexpress/settings/
├── base.py      # Configuration de base
├── dev.py       # Développement
├── prod.py      # Production
├── test.py      # Tests
└── local.py     # Overrides locaux
```

### 10.2 Variables d'environnement

- `DJANGO_SECRET_KEY`
- `EMAIL_BACKEND`
- `REDIS_URL`
- `DATABASE_URL` (production)

### 10.3 Déploiement

- **Static files** : WhiteNoise
- **Database** : SQLite (dev) / PostgreSQL (prod)
- **Hosting** : Render.com (configuré)

---

## 11. Points d'attention architecturaux

### 11.1 Architecture hexagonale partielle

**Problème** : Le module `hexcore/` n'est pas complètement intégré.  
**Recommandation** : 
- Soit compléter l'intégration
- Soit supprimer si non utilisé
- Ne pas créer de nouvelles fonctionnalités avec cette approche sans validation

### 11.2 Duplication de code

**Problème** : Certaines fonctionnalités sont dupliquées (ex: `middleware.py` vs `middleware_v2.py`).  
**Recommandation** : Nettoyer les fichiers obsolètes après migration complète.

### 11.3 Services dispersés

**Problème** : Les services sont dans différents emplacements (`services.py`, `services/`, `core/services/`).  
**Recommandation** : Standardiser l'emplacement selon le domaine métier.

---

## 12. Évolutions prévues

### 12.1 Court terme

- Finalisation de la migration vers `middleware_v2.py`
- Nettoyage des fichiers obsolètes
- Documentation des APIs internes

### 12.2 Moyen terme

- Amélioration de la gestion des erreurs
- Tests d'intégration complets
- Optimisation des performances (requêtes DB)

### 12.3 Long terme

- API REST pour intégrations externes
- Application mobile (optionnel)
- Analytics avancés

---

## 13. Décisions architecturales majeures

| Décision | Justification | Impact |
|----------|---------------|--------|
| **Multi-portails séparés** | Séparation claire des responsabilités par rôle | Maintenance facilitée, sécurité renforcée |
| **Middleware d'accès** | Contrôle centralisé des permissions | Cohérence garantie |
| **Celery pour emails** | Performance et fiabilité | Expérience utilisateur améliorée |
| **WeasyPrint + ReportLab** | Besoins différents (devis HTML vs factures programmatiques) | Flexibilité maximale |
| **Architecture modulaire Django** | Simplicité et maintenabilité | Évolutivité contrôlée |

---

**Document maintenu par** : Chef de Projet / Architecte Principal  
**Dernière mise à jour** : 2025-01-27

