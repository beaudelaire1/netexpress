# 📘 NetExpress — Parcours UX par Profil

> Document de référence UX/UI — Version 1.0  
> Dernière mise à jour : Décembre 2025

---

## Table des matières

1. [Vision Produit](#vision-produit)
2. [Principes UX](#principes-ux)
3. [Parcours Client](#parcours-client)
4. [Parcours Worker (Ouvrier)](#parcours-worker)
5. [Parcours Administrateur Business](#parcours-admin-business)
6. [Parcours Administrateur Technique](#parcours-admin-technique)
7. [Recommandations UI](#recommandations-ui)
8. [Composants Réutilisables](#composants-réutilisables)

---

## 1. Vision Produit {#vision-produit}

### Objectif
NetExpress est un ERP de services (nettoyage, entretien, espaces verts) destiné à des **utilisateurs non-techniques**. L'interface doit être :

- **Intuitive** : Navigation évidente sans formation
- **Efficace** : Tâches complètes en minimum de clics
- **Rassurante** : Feedback clair à chaque action

### Personas

| Persona | Description | Objectif Principal |
|---------|-------------|-------------------|
| **Marie, 45 ans** | Cliente particulière, peu à l'aise avec le numérique | Suivre mes devis et factures simplement |
| **Jean, 32 ans** | Ouvrier terrain, utilise son smartphone | Voir mes tâches du jour rapidement |
| **Sophie, 38 ans** | Responsable admin, gère 5-10 ouvriers | Avoir une vue globale et agir vite |
| **Marc, 42 ans** | Gérant, besoin de KPIs et rapports | Prendre des décisions business |

---

## 2. Principes UX {#principes-ux}

### 2.1 Hiérarchie de l'Information

```
┌─────────────────────────────────────────────────────┐
│  NIVEAU 1 — Ce qui compte MAINTENANT               │
│  → KPIs critiques, alertes, actions urgentes       │
├─────────────────────────────────────────────────────┤
│  NIVEAU 2 — Ce qui compte AUJOURD'HUI              │
│  → Tâches du jour, documents en attente            │
├─────────────────────────────────────────────────────┤
│  NIVEAU 3 — Ce qui compte CETTE SEMAINE            │
│  → Planning, tendances, suivi projets              │
├─────────────────────────────────────────────────────┤
│  NIVEAU 4 — Historique & Paramètres                │
│  → Archives, configuration, profil                 │
└─────────────────────────────────────────────────────┘
```

### 2.2 Règles d'Or

| Règle | Application |
|-------|-------------|
| **3 clics max** | Toute action principale accessible en 3 clics |
| **Feedback immédiat** | Toast/notification après chaque action |
| **Confirmation visuelle** | Changement d'état visible (badges, couleurs) |
| **Zéro jargon technique** | Vocabulaire métier uniquement |
| **Mobile-first pour Workers** | Interface optimisée tactile |

### 2.3 Codes Couleur Sémantiques

```css
/* États */
Brouillon    → Gris     (#6B7280)
En attente   → Orange   (#F59E0B)
Accepté/Payé → Vert     (#22C55E)
Refusé/Retard → Rouge   (#EF4444)
En cours     → Bleu     (#3B82F6)
```

---

## 3. Parcours Client {#parcours-client}

### 3.1 Objectifs Utilisateur

- ✅ Consulter mes devis en attente
- ✅ Valider un devis (signature électronique)
- ✅ Voir mes factures et leur statut de paiement
- ✅ Contacter l'entreprise facilement
- ✅ Demander un nouveau devis

### 3.2 Arborescence

```
📁 ESPACE CLIENT (/client/)
│
├── 📊 Dashboard
│   ├── Résumé (devis en attente, factures impayées)
│   ├── Actions rapides
│   └── Dernière activité
│
├── 📄 Mes Devis (/client/quotes/)
│   ├── Liste avec filtres (statut)
│   └── Détail devis → Action: Accepter/Refuser
│
├── 🧾 Mes Factures (/client/invoices/)
│   ├── Liste avec filtres (payé, impayé, retard)
│   └── Détail facture → Télécharger PDF
│
├── 💬 Messages (/messaging/)
│   ├── Conversations avec l'équipe
│   └── Nouveau message
│
└── 👤 Mon Profil (/accounts/profile/)
    ├── Informations personnelles
    └── Préférences notifications
```

### 3.3 Écrans Clés

#### Dashboard Client

```
┌────────────────────────────────────────────────────────────┐
│  🏠 Mon Espace Client                                      │
│  Bonjour Marie ! Dernière connexion : 27/12/2025           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 📄 3     │  │ ⏳ 1     │  │ 🧾 5     │  │ ⚠️ 0     │   │
│  │ Devis    │  │ En       │  │ Factures │  │ Impayées │   │
│  │ totaux   │  │ attente  │  │ totales  │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                            │
│  ┌─────────────────────────────┬──────────────────────────┐│
│  │ 📋 DEVIS EN ATTENTE         │ 🧾 FACTURES RÉCENTES     ││
│  │                             │                          ││
│  │ • DEV-2025-042  850€        │ • FAC-2025-038  320€ ✅  ││
│  │   → [Voir] [Accepter]       │   → [Télécharger]        ││
│  │                             │                          ││
│  │ Aucun autre devis           │ • FAC-2025-035  480€ ⏳  ││
│  │                             │   → [Télécharger]        ││
│  └─────────────────────────────┴──────────────────────────┘│
│                                                            │
│  ┌─────────────────────────────────────────────────────────┐
│  │ ⚡ ACTIONS RAPIDES                                      │
│  │                                                         │
│  │  [➕ Nouveau Devis]  [💬 Contacter]  [👤 Mon Profil]    │
│  └─────────────────────────────────────────────────────────┘
└────────────────────────────────────────────────────────────┘
```

#### Flux : Validation de Devis

```
ÉTAPE 1               ÉTAPE 2               ÉTAPE 3
┌───────────┐        ┌───────────┐        ┌───────────┐
│ Liste     │   →    │ Détail    │   →    │ Code de   │
│ devis     │        │ du devis  │        │ validation│
└───────────┘        └───────────┘        └───────────┘
                          ↓                     ↓
                     [Accepter]           SMS → 4 chiffres
                          ↓                     ↓
                                          ┌───────────┐
                                          │ ✅ Devis  │
                                          │ accepté ! │
                                          └───────────┘
```

### 3.4 Points d'Attention UX

| Zone | Recommandation |
|------|----------------|
| **Dashboard** | Mettre en évidence les éléments nécessitant une action |
| **Liste devis** | Badge coloré visible pour le statut |
| **Validation** | Processus en 2 étapes max (code SMS) |
| **Factures** | Bouton "Télécharger PDF" très visible |
| **Messages** | Indicateur de non-lus |

---

## 4. Parcours Worker (Ouvrier) {#parcours-worker}

### 4.1 Objectifs Utilisateur

- ✅ Voir mes tâches du jour en un coup d'œil
- ✅ Consulter les détails d'une intervention (lieu, client)
- ✅ Marquer une tâche comme terminée
- ✅ Voir mon planning de la semaine
- ✅ Signaler un problème (photos)

### 4.2 Arborescence

```
📁 ESPACE OUVRIER (/worker/)
│
├── 📊 Tableau de Bord
│   ├── Tâches du jour (prioritaires)
│   ├── Prochaines interventions
│   └── Statut global (X terminées / Y total)
│
├── 📅 Planning (/worker/schedule/)
│   ├── Vue semaine
│   ├── Vue mois
│   └── Filtrer par équipe
│
├── ✅ Mes Tâches (/tasks/)
│   ├── Liste avec tri (date, priorité)
│   ├── Détail tâche
│   │   ├── Infos client & lieu (+ lien Maps)
│   │   ├── Description intervention
│   │   ├── [Marquer terminée]
│   │   └── [Ajouter photos]
│   └── Historique
│
└── 👤 Mon Profil
```

### 4.3 Écran Mobile — Vue Jour

```
┌────────────────────────────────────┐
│ ☰  MES TÂCHES DU JOUR    27 Déc   │
├────────────────────────────────────┤
│                                    │
│  📍 3 interventions aujourd'hui    │
│  ▓▓▓▓▓▓▓░░░░░  2/3 terminées       │
│                                    │
├────────────────────────────────────┤
│                                    │
│  ┌────────────────────────────────┐│
│  │ ✅ 08:00 - Nettoyage bureaux   ││
│  │    📍 12 Rue du Commerce       ││
│  │    👤 Entreprise ABC           ││
│  │    [Terminé à 09:45]           ││
│  └────────────────────────────────┘│
│                                    │
│  ┌────────────────────────────────┐│
│  │ ✅ 10:30 - Entretien jardin    ││
│  │    📍 8 Avenue des Fleurs      ││
│  │    👤 M. Dupont                ││
│  │    [Terminé à 12:15]           ││
│  └────────────────────────────────┘│
│                                    │
│  ┌────────────────────────────────┐│
│  │ 🔵 14:00 - Peinture intérieur  ││
│  │    📍 25 Bd de la Liberté      ││
│  │    👤 Mme Martin               ││
│  │                                ││
│  │  [📍 Itinéraire]  [▶️ Démarrer]││
│  └────────────────────────────────┘│
│                                    │
└────────────────────────────────────┘
│  [📅 Planning]  [📋 Toutes]  [👤]  │
└────────────────────────────────────┘
```

### 4.4 Flux : Terminer une Tâche

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Carte tâche   │ →   │ [▶️ Démarrer] │ →   │ [✅ Terminer] │
│ (liste jour)  │     │ En cours...   │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
                                                   ↓
                                            ┌───────────────┐
                                            │ 📷 Ajouter    │
                                            │ photos ?      │
                                            │ [Oui] [Non]   │
                                            └───────────────┘
                                                   ↓
                                            ┌───────────────┐
                                            │ ✅ Tâche      │
                                            │ terminée !    │
                                            │ [Suivante →]  │
                                            └───────────────┘
```

### 4.5 Points d'Attention UX

| Zone | Recommandation |
|------|----------------|
| **Vue jour** | Tâches triées par heure, très lisible |
| **Carte tâche** | Informations essentielles seulement |
| **Bouton Maps** | Ouvrir l'app native de navigation |
| **Terminer** | Confirmation visuelle forte (animation) |
| **Mode hors-ligne** | Synchroniser quand connexion |

---

## 5. Parcours Administrateur Business {#parcours-admin-business}

### 5.1 Objectifs Utilisateur

- ✅ Vue d'ensemble des KPIs business
- ✅ Créer et envoyer des devis
- ✅ Gérer les factures
- ✅ Assigner des tâches aux ouvriers
- ✅ Suivre la performance des équipes
- ✅ Gérer les campagnes marketing

### 5.2 Arborescence

```
📁 ADMIN DASHBOARD (/admin-dashboard/)
│
├── 📊 Vue d'Ensemble
│   ├── KPIs (CA total, mensuel, en attente)
│   ├── Graphiques (tendances, répartition)
│   ├── Alertes (retards, urgences)
│   └── Activité récente
│
├── 📄 Devis (/admin-dashboard/quotes/)
│   ├── Liste avec filtres avancés
│   ├── Créer un devis
│   ├── Éditer / Envoyer par email
│   └── Convertir en facture
│
├── 🧾 Factures (/admin-dashboard/invoices/)
│   ├── Liste avec statuts
│   ├── Créer une facture
│   ├── Marquer comme payée
│   └── Relance client
│
├── 👷 Ouvriers (/admin-dashboard/workers/)
│   ├── Liste des ouvriers
│   ├── Performance individuelle
│   └── Ajouter un ouvrier
│
├── ✅ Tâches & Planning
│   ├── Planning global (calendrier)
│   ├── Créer une tâche
│   └── Assigner / Réassigner
│
├── 👥 Clients (/admin-dashboard/clients/)
│   ├── Liste des clients
│   ├── Historique par client
│   └── Ajouter un client
│
├── 📢 Campagnes (/admin-dashboard/campaigns/)
│   ├── Liste des campagnes
│   └── Créer une campagne
│
└── 💬 Messages
    └── Conversations avec clients
```

### 5.3 Dashboard Admin — Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NETEXPRESS                           🔔 3  👤 Sophie Martin  [Déconnexion] │
├──────────────┬──────────────────────────────────────────────────────────────┤
│              │                                                              │
│  📊 Dashboard│  ┌──────────────────────────────────────────────────────────┐│
│  📄 Devis    │  │  📊 TABLEAU DE BORD ADMINISTRATEUR                       ││
│  🧾 Factures │  │                                                          ││
│  👷 Ouvriers │  │  Vue d'ensemble • Dernière maj: il y a 2 min             ││
│  📅 Planning │  └──────────────────────────────────────────────────────────┘│
│  👥 Clients  │                                                              │
│  📢 Campagnes│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│  💬 Messages │  │ 💶 45 230€  │ │ 💶 8 420€   │ │ 📈 12 450€  │ │ 📊 72%   ││
│              │  │ CA Total    │ │ CA Mensuel  │ │ En attente  │ │ Convert. ││
│              │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘│
│              │                                                              │
│              │  ┌────────────────────────────────────────┬──────────────────┐
│              │  │  📈 ÉVOLUTION CA                       │ 📊 RÉPARTITION   │
│              │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓          │                  │
│              │  │  ████████████████████████████████      │    🔵 Devis      │
│              │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                    │    🟢 Factures   │
│              │  │  Jan  Fév  Mar  Avr  Mai  Jun          │    🟣 Tâches     │
│              │  └────────────────────────────────────────┴──────────────────┘
│              │                                                              │
│              │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│              │  │ DEVIS RÉCENTS   │ │ FACTURES        │ │ TÂCHES          │ │
│              │  │ DEV-042  850€ ⏳│ │ FAC-038 320€ ✅ │ │ Nettoyage... ✅ │ │
│              │  │ DEV-041  420€ ✅│ │ FAC-037 480€ ⏳ │ │ Peinture... 🔵  │ │
│              │  │ [Voir tout →]   │ │ [Voir tout →]   │ │ [Voir tout →]   │ │
│              │  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│              │                                                              │
│              │  ┌───────────────────────────────────────────────────────────┐
│              │  │ ⚡ ACTIONS RAPIDES                                        │
│              │  │ [➕ Devis] [➕ Facture] [➕ Tâche] [➕ Ouvrier] [⚙️ Gestion]│
│              │  └───────────────────────────────────────────────────────────┘
│              │                                                              │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

### 5.4 Flux Clés

#### Création de Devis

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ [➕ Nouveau   │ →   │ Sélection     │ →   │ Détail        │ →   │ Récapitulatif │
│    Devis]     │     │ client        │     │ prestations   │     │ & validation  │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
                                                                         ↓
                      ┌───────────────────────────────────────────────────┘
                      ↓
               ┌───────────────┐     ┌───────────────┐
               │ Aperçu PDF    │ →   │ [Envoyer par  │
               │               │     │  email]       │
               └───────────────┘     └───────────────┘
```

#### Assignation de Tâche

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Planning      │ →   │ Créer tâche   │ →   │ Assigner      │
│ (calendrier)  │     │ (formulaire)  │     │ ouvrier(s)    │
└───────────────┘     └───────────────┘     └───────────────┘
                                                   ↓
                                            ┌───────────────┐
                                            │ ✅ Tâche      │
                                            │ assignée !    │
                                            │ [Notifier]    │
                                            └───────────────┘
```

### 5.5 Points d'Attention UX

| Zone | Recommandation |
|------|----------------|
| **KPIs** | Couleurs cohérentes avec le contexte (vert=positif, rouge=alerte) |
| **Tableaux** | Pagination, tri par colonne, recherche |
| **Formulaires** | Validation en temps réel, preview |
| **Actions** | Confirmation pour actions destructives |
| **Filtres** | Mémoriser les préférences utilisateur |

---

## 6. Parcours Administrateur Technique {#parcours-admin-technique}

### 6.1 Accès

L'admin technique a accès à l'interface Django Admin complète (`/gestion/`), en plus du dashboard business.

### 6.2 Fonctionnalités Exclusives

- Configuration système (paramètres email, API)
- Gestion des utilisateurs et permissions
- Logs et audit trail
- Import/Export de données
- Maintenance technique

### 6.3 Recommandation

> ⚠️ L'interface Django Admin est technique par nature. Pour cet utilisateur avancé, les personnalisations Jazzmin actuelles sont suffisantes. Prioriser l'UX des autres profils.

---

## 7. Recommandations UI {#recommandations-ui}

### 7.1 Migration vers Charte Bleue

**Situation actuelle** : Palette verte (#104130)  
**Cible** : Palette bleue NetExpress

| Élément | Avant (Vert) | Après (Bleu) |
|---------|--------------|--------------|
| Header | `#104130` | `#2563eb` gradient vers `#1e40af` |
| Sidebar | `#0b2f23` | `#1e3a8a` gradient vers `#172554` |
| Boutons primaires | `#2d8a5e` | `#3b82f6` |
| Liens | `#15803d` | `#2563eb` |
| Focus ring | `rgba(45,138,94,0.25)` | `rgba(59,130,246,0.25)` |

### 7.2 Typographie

```css
/* Titres & Headlines */
font-family: 'Plus Jakarta Sans', sans-serif;
font-weight: 700-800;

/* Corps de texte */
font-family: 'Inter', system-ui, sans-serif;
font-weight: 400-500;

/* Monospace (codes, numéros) */
font-family: 'JetBrains Mono', monospace;
```

### 7.3 Iconographie

Utiliser **Font Awesome 6** (déjà inclus) avec cohérence :

| Action | Icône |
|--------|-------|
| Créer / Ajouter | `fa-plus` |
| Voir / Détail | `fa-eye` |
| Modifier | `fa-pen` |
| Supprimer | `fa-trash` |
| Télécharger | `fa-download` |
| Envoyer | `fa-paper-plane` |
| Valider | `fa-check` |
| Annuler | `fa-times` |
| Alerter | `fa-exclamation-triangle` |
| Rechercher | `fa-search` |

### 7.4 Composants Clés

#### Boutons

```html
<!-- Primaire — Action principale -->
<button class="ne-btn ne-btn-primary">
  <i class="fas fa-plus"></i> Nouveau Devis
</button>

<!-- Secondaire — Action secondaire -->
<button class="ne-btn ne-btn-secondary">
  Annuler
</button>

<!-- Ghost — Navigation / Options -->
<button class="ne-btn ne-btn-ghost">
  <i class="fas fa-filter"></i> Filtres
</button>
```

#### Cards KPI

```html
<div class="ne-card-kpi is-blue">
  <span class="ne-kpi-label">Chiffre d'Affaires</span>
  <span class="ne-kpi-value">45 230 €</span>
  <div class="ne-kpi-icon"><i class="fas fa-euro-sign"></i></div>
</div>
```

#### Badges de Statut

```html
<span class="ne-badge ne-badge-pending">En attente</span>
<span class="ne-badge ne-badge-accepted">Accepté</span>
<span class="ne-badge ne-badge-overdue">En retard</span>
```

---

## 8. Composants Réutilisables {#composants-réutilisables}

### 8.1 Template de Base

Tous les portails doivent hériter du nouveau template unifié :

```django
{% extends "base_netexpress.html" %}

{% block sidebar %}
  <!-- Navigation spécifique au profil -->
{% endblock %}

{% block content %}
  <!-- Contenu de la page -->
{% endblock %}
```

### 8.2 Partials Recommandés

| Composant | Fichier | Usage |
|-----------|---------|-------|
| KPI Card | `partials/kpi_card.html` | Dashboard admin |
| Document Card | `partials/document_card.html` | Listes devis/factures |
| Task Card | `partials/task_card.html` | Planning worker |
| Status Badge | `partials/status_badge.html` | Partout |
| Empty State | `partials/empty_state.html` | Listes vides |
| Pagination | `partials/pagination.html` | Tableaux |

### 8.3 Animations

Utiliser les classes d'animation du design system :

```html
<!-- Fade in au chargement -->
<div class="ne-animate-fade-in">...</div>

<!-- Stagger pour les listes -->
<div class="ne-stagger">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

---

## 📋 Checklist de Mise en Œuvre

### Phase 1 — Design System (1 semaine)
- [ ] Migrer les variables CSS vers la charte bleue
- [ ] Créer les composants de base (boutons, cards, badges)
- [ ] Mettre à jour le header/navigation

### Phase 2 — Portail Client (2 semaines)
- [ ] Refonte du dashboard client
- [ ] Améliorer le flux de validation de devis
- [ ] Optimiser l'affichage des factures

### Phase 3 — Portail Worker (2 semaines)
- [ ] Vue mobile-first pour les tâches du jour
- [ ] Intégration bouton Maps/Navigation
- [ ] Flux "Terminer une tâche" simplifié

### Phase 4 — Dashboard Admin (3 semaines)
- [ ] Nouveaux composants KPI
- [ ] Graphiques interactifs
- [ ] Optimisation des formulaires de création

### Phase 5 — Tests & Ajustements (1 semaine)
- [ ] Tests utilisateurs par profil
- [ ] Corrections accessibilité
- [ ] Optimisation performance

---

*Document créé par l'équipe UX/UI NetExpress*  
*Pour toute question : [contact@netexpress.fr]*

