# 📐 NetExpress — Guide UX/UI Complet

> **Version:** 2.0  
> **Date:** Décembre 2025  
> **Responsable UX/UI:** Guide de conception  

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Analyse de l'existant](#analyse-de-lexistant)
3. [Design System — Charte Bleue NetExpress](#design-system)
4. [Parcours utilisateurs par profil](#parcours-utilisateurs)
5. [Maquettes fonctionnelles](#maquettes-fonctionnelles)
6. [Recommandations UI](#recommandations-ui)
7. [Accessibilité & Responsive](#accessibilite-responsive)
8. [Plan d'implémentation](#plan-dimplementation)

---

## 🎯 Vue d'ensemble

### Contexte

NetExpress est un ERP destiné à des **utilisateurs non techniques** dans le secteur du nettoyage et de l'entretien en Guyane. L'interface doit être :

- **Simple** : Pas de jargon technique
- **Efficace** : Actions en 2-3 clics maximum
- **Lisible** : Hiérarchie visuelle claire
- **Premium** : Cohérente avec l'image de marque

### Profils utilisateurs

| Profil | Description | Niveau technique | Besoins principaux |
|--------|-------------|------------------|-------------------|
| **Client** | Particuliers ou entreprises | Faible | Voir devis/factures, demander des prestations |
| **Worker** | Ouvriers sur le terrain | Moyen | Consulter tâches, planning, valider interventions |
| **Admin Business** | Gestionnaires métier | Moyen | Gérer devis/factures/tâches, suivre KPIs |
| **Admin Technique** | Administrateurs IT | Élevé | Configuration système, gestion utilisateurs |

---

## 🔍 Analyse de l'existant

### Architecture actuelle des portails

```
┌─────────────────────────────────────────────────────────────────┐
│                     NETEXPRESS - PORTAILS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🏠 Site Public (/)                                             │
│  ├── Accueil                                                    │
│  ├── Services                                                   │
│  ├── Excellence                                                 │
│  ├── Réalisations                                               │
│  ├── Contact                                                    │
│  └── Demande de devis                                           │
│                                                                 │
│  👤 Portail Client (/client/)                                   │
│  ├── Dashboard (vue d'ensemble)                                 │
│  ├── Mes Devis                                                  │
│  ├── Mes Factures                                               │
│  └── Messages                                                   │
│                                                                 │
│  👷 Portail Worker (/worker/)                                   │
│  ├── Tableau de bord                                            │
│  ├── Calendrier tâches                                          │
│  └── Liste des tâches                                           │
│                                                                 │
│  📊 Portail Admin Business (/admin-dashboard/)                  │
│  ├── Dashboard KPIs                                             │
│  ├── Planning global                                            │
│  ├── Gestion ouvriers/clients                                   │
│  ├── Devis & Factures                                           │
│  ├── Campagnes marketing                                        │
│  └── Messages                                                   │
│                                                                 │
│  ⚙️ Admin Technique (/gestion/)                                 │
│  └── Django Admin (interface native)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Points forts identifiés ✅

1. **Séparation claire des portails** par rôle
2. **Dashboard Admin riche** avec KPIs et graphiques
3. **Design system CSS** bien structuré (variables, composants)
4. **Responsive** : Support mobile avec menu burger
5. **Accessibilité** : Support `prefers-reduced-motion`, `prefers-contrast`

### Points d'amélioration 🔄

1. **Incohérence de palette** : Vert utilisé (style_v2.css) vs Bleu prévu (design-system.css)
2. **Portail Worker basique** : Manque de fonctionnalités par rapport aux autres
3. **Navigation hétérogène** : Différents patterns entre portails
4. **Deux templates de base** : `base.html` et `base_v2.html` créent de l'incohérence
5. **Actions rapides** : Manque de raccourcis contextuels pour le client

---

## 🎨 Design System

### 1. Palette de couleurs — Charte Bleue NetExpress

La palette bleue communique **professionnalisme**, **fiabilité** et **confiance**.

```css
:root {
  /* ═══════════════════════════════════════════
     BLEU NETEXPRESS — Couleur principale
     ═══════════════════════════════════════════ */
  --ne-blue-50:  #eff6ff;   /* Fond très léger */
  --ne-blue-100: #dbeafe;   /* Fond léger */
  --ne-blue-200: #bfdbfe;   /* Bordures légères */
  --ne-blue-300: #93c5fd;   /* Hover léger */
  --ne-blue-400: #60a5fa;   /* Éléments secondaires */
  --ne-blue-500: #3b82f6;   /* ⭐ COULEUR PRINCIPALE */
  --ne-blue-600: #2563eb;   /* Hover / Active */
  --ne-blue-700: #1d4ed8;   /* États pressed */
  --ne-blue-800: #1e40af;   /* Textes forts */
  --ne-blue-900: #1e3a8a;   /* Titres */
  --ne-blue-950: #172554;   /* Header / Sidebar */

  /* ═══════════════════════════════════════════
     COULEURS SÉMANTIQUES
     ═══════════════════════════════════════════ */
  
  /* Succès — Vert */
  --ne-success-50:  #f0fdf4;
  --ne-success-500: #22c55e;
  --ne-success-700: #15803d;
  
  /* Avertissement — Orange */
  --ne-warning-50:  #fffbeb;
  --ne-warning-500: #f59e0b;
  --ne-warning-700: #b45309;
  
  /* Erreur — Rouge */
  --ne-error-50:  #fef2f2;
  --ne-error-500: #ef4444;
  --ne-error-700: #b91c1c;
  
  /* Information — Cyan */
  --ne-info-50:  #f0f9ff;
  --ne-info-500: #0ea5e9;
  --ne-info-700: #0369a1;

  /* ═══════════════════════════════════════════
     NEUTRES
     ═══════════════════════════════════════════ */
  --ne-gray-50:  #f9fafb;   /* Fond de page */
  --ne-gray-100: #f3f4f6;   /* Cartes secondaires */
  --ne-gray-200: #e5e7eb;   /* Bordures */
  --ne-gray-300: #d1d5db;   /* Bordures focus */
  --ne-gray-400: #9ca3af;   /* Placeholder */
  --ne-gray-500: #6b7280;   /* Texte secondaire */
  --ne-gray-600: #4b5563;   /* Texte standard */
  --ne-gray-700: #374151;   /* Texte fort */
  --ne-gray-800: #1f2937;   /* Titres */
  --ne-gray-900: #111827;   /* Noir presque pur */
}
```

### 2. Typographie

```css
:root {
  /* Familles de police */
  --ne-font-display: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --ne-font-body: 'Inter', system-ui, -apple-system, sans-serif;
  --ne-font-mono: 'JetBrains Mono', monospace;

  /* Échelle typographique */
  --ne-text-xs:   0.75rem;   /* 12px — Labels, badges */
  --ne-text-sm:   0.875rem;  /* 14px — Corps secondaire */
  --ne-text-base: 1rem;      /* 16px — Corps principal */
  --ne-text-lg:   1.125rem;  /* 18px — Sous-titres */
  --ne-text-xl:   1.25rem;   /* 20px — Titres de section */
  --ne-text-2xl:  1.5rem;    /* 24px — Titres de page */
  --ne-text-3xl:  1.875rem;  /* 30px — Titres principaux */
  --ne-text-4xl:  2.25rem;   /* 36px — Grands titres */
}
```

### 3. Espacements

```css
:root {
  --ne-space-1:  0.25rem;  /* 4px  */
  --ne-space-2:  0.5rem;   /* 8px  */
  --ne-space-3:  0.75rem;  /* 12px */
  --ne-space-4:  1rem;     /* 16px */
  --ne-space-5:  1.25rem;  /* 20px */
  --ne-space-6:  1.5rem;   /* 24px */
  --ne-space-8:  2rem;     /* 32px */
  --ne-space-10: 2.5rem;   /* 40px */
  --ne-space-12: 3rem;     /* 48px */
  --ne-space-16: 4rem;     /* 64px */
}
```

### 4. Rayons & Ombres

```css
:root {
  /* Rayons de bordure */
  --ne-radius-sm:   6px;
  --ne-radius-md:   10px;
  --ne-radius-lg:   14px;
  --ne-radius-xl:   18px;
  --ne-radius-2xl:  24px;
  --ne-radius-full: 9999px;  /* Boutons pills */

  /* Ombres */
  --ne-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --ne-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07);
  --ne-shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
  --ne-shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.08);
  
  /* Ombres colorées pour CTAs */
  --ne-shadow-blue: 0 10px 30px -5px rgba(37, 99, 235, 0.25);
}
```

### 5. Composants UI

#### Boutons

| Variante | Usage | Exemple |
|----------|-------|---------|
| **Primary** | Actions principales | "Valider", "Envoyer" |
| **Secondary** | Actions secondaires | "Annuler", "Retour" |
| **Ghost** | Actions tertiaires | "En savoir plus" |
| **Danger** | Actions destructives | "Supprimer" |

```html
<!-- Primary Button -->
<button class="ne-btn ne-btn-primary">
  <i class="fas fa-check"></i> Valider le devis
</button>

<!-- Secondary Button -->
<button class="ne-btn ne-btn-secondary">
  Annuler
</button>
```

#### Badges de statut

| Statut | Couleur | Contexte |
|--------|---------|----------|
| `draft` | Gris | Brouillon |
| `pending` / `sent` | Jaune | En attente |
| `accepted` / `paid` | Vert | Validé/Payé |
| `rejected` / `overdue` | Rouge | Refusé/En retard |
| `in_progress` | Bleu | En cours |

#### Cartes KPI

```html
<div class="ne-card-kpi is-blue">
  <div class="ne-kpi-label">Chiffre d'Affaires</div>
  <div class="ne-kpi-value">24 580 €</div>
  <div class="ne-kpi-icon">
    <i class="fas fa-euro-sign"></i>
  </div>
</div>
```

---

## 🚶 Parcours utilisateurs

### Parcours Client

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARCOURS CLIENT                              │
└─────────────────────────────────────────────────────────────────┘

🌐 VISITEUR NON CONNECTÉ
│
├─► Découverte du site
│   └── Accueil → Services → Excellence → Réalisations
│
├─► Demande de devis express
│   └── Formulaire rapide → Confirmation
│
└─► Création de compte
    └── Inscription → Email confirmation → Connexion


👤 CLIENT CONNECTÉ
│
├─► Dashboard (/client/)
│   │
│   ├── Vue résumée
│   │   ├── Nombre de devis (total / en attente)
│   │   ├── Nombre de factures (total / impayées)
│   │   └── Documents récents
│   │
│   └── Actions rapides
│       ├── [Nouveau devis] → Formulaire → Confirmation
│       ├── [Messages] → Liste conversations
│       └── [Mon profil] → Édition informations
│
├─► Mes Devis (/client/quotes/)
│   │
│   ├── Liste avec filtres (statut, date)
│   │
│   └── Détail devis (/client/quotes/<id>/)
│       ├── Visualisation PDF
│       ├── [Accepter] → Code validation → Signature → Confirmation
│       └── [Refuser] → Motif (optionnel) → Confirmation
│
├─► Mes Factures (/client/invoices/)
│   │
│   ├── Liste avec filtres (statut, date)
│   │
│   └── Détail facture (/client/invoices/<id>/)
│       ├── Visualisation PDF
│       ├── [Télécharger PDF]
│       └── Historique paiements
│
└─► Messages (/messaging/)
    ├── Liste des conversations
    └── Nouvelle conversation → Envoi → Notification admin
```

#### Wireframe Dashboard Client

```
┌─────────────────────────────────────────────────────────────────┐
│  🏠 Nettoyage Express          Dashboard ▾  👤 Jean Dupont ▾    │
├─────────────────────────────────────────────────────────────────┤
│  Dashboard │ Mes Devis │ Mes Factures │ Messages               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bienvenue, Jean                          Dernière connexion:   │
│  ─────────────────────                    12/12/2025 à 14:32   │
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │    📄     │ │    ⏳     │ │    📃     │ │    ⚠️     │       │
│  │    5      │ │    2      │ │    8      │ │    1      │       │
│  │  Devis    │ │ En attente│ │ Factures  │ │ Impayées  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│                                                                 │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐│
│  │ 📄 Devis Récents           │ │ 📃 Factures Récentes        ││
│  │ ─────────────────────────  │ │ ─────────────────────────   ││
│  │                            │ │                             ││
│  │ DEV-2025-0042  1 250,00 €  │ │ FAC-2025-0089  890,00 €     ││
│  │ ⏳ En attente   [Voir]     │ │ ✅ Payée        [Voir]       ││
│  │                            │ │                             ││
│  │ DEV-2025-0038    680,00 €  │ │ FAC-2025-0085  450,00 €     ││
│  │ ✅ Accepté      [Voir]     │ │ ⚠️ En attente   [Voir]       ││
│  │                            │ │                             ││
│  │        [Voir tous →]       │ │        [Voir toutes →]      ││
│  └─────────────────────────────┘ └─────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ⚡ Actions Rapides                                          ││
│  │ ─────────────────────────────────────────────────────────── ││
│  │                                                             ││
│  │  [➕ Nouveau Devis]  [💬 Messages]  [📄 Mes Devis]  [👤 Profil]││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Parcours Worker

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARCOURS WORKER                              │
└─────────────────────────────────────────────────────────────────┘

👷 OUVRIER CONNECTÉ
│
├─► Dashboard (/worker/)
│   │
│   ├── Vue du jour
│   │   ├── Tâches du jour (priorité haute en premier)
│   │   ├── Tâches en retard (alerte visuelle)
│   │   └── Prochaines tâches (J+1, J+2)
│   │
│   └── KPIs personnels
│       ├── Tâches terminées ce mois
│       ├── Taux de complétion
│       └── Heures travaillées
│
├─► Calendrier (/worker/calendar/)
│   │
│   ├── Vue mensuelle/semaine/jour
│   ├── Code couleur par type de tâche
│   └── Clic sur événement → Détail tâche
│
├─► Liste des tâches (/tasks/list/)
│   │
│   ├── Filtres : Statut, Date, Client
│   ├── Tri : Priorité, Date échéance
│   │
│   └── Détail tâche (/tasks/<id>/)
│       ├── Informations : Titre, Description, Lieu
│       ├── Client associé (contact, adresse)
│       ├── Documents liés (devis, facture)
│       │
│       └── Actions
│           ├── [Commencer] → Statut "En cours"
│           ├── [Terminer] → Statut "Terminé" + Note optionnelle
│           ├── [Signaler problème] → Message vers admin
│           └── [Ajouter photo] → Upload preuve intervention
│
└─► Messages (/messaging/)
    └── Communication avec l'administration
```

#### Wireframe Dashboard Worker (Amélioré)

```
┌─────────────────────────────────────────────────────────────────┐
│  🏠 Nettoyage Express                          👷 Marc Dubois ▾ │
├─────────────────────────────────────────────────────────────────┤
│  Mon Dashboard │ Calendrier │ Mes Tâches                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bonjour Marc ! Voici vos tâches du jour               📅 Lun 28│
│  ───────────────────────────────────────────────────────────────│
│                                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │   12    │ │   85%   │ │   42h   │                           │
│  │ Tâches  │ │ Taux    │ │ Ce mois │                           │
│  │ terminées│ │ complet.│ │         │                           │
│  └─────────┘ └─────────┘ └─────────┘                           │
│                                                                 │
│  ⚠️ EN RETARD (1)                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🔴 Nettoyage bureaux - SCI Amazonie                         ││
│  │    📍 753 Chemin de la Désirée, Matoury                     ││
│  │    ⏰ Échéance: 27/12 (hier)     [Commencer]  [Signaler]    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  📋 AUJOURD'HUI (3)                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🟡 Entretien jardin - M. Dupont                             ││
│  │    📍 12 Rue des Palmiers, Cayenne                          ││
│  │    ⏰ 09:00 - 12:00              [Commencer]                ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 🟢 Peinture façade - Mme Martin (EN COURS)                  ││
│  │    📍 45 Avenue du Général, Rémire                          ││
│  │    ⏰ 14:00 - 17:00              [Terminer]   [Ajouter photo]││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  📆 DEMAIN (2)                                                  │
│  └── [Voir toutes →]                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Parcours Admin Business

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARCOURS ADMIN BUSINESS                      │
└─────────────────────────────────────────────────────────────────┘

📊 ADMINISTRATEUR MÉTIER
│
├─► Dashboard (/admin-dashboard/)
│   │
│   ├── KPIs temps réel
│   │   ├── Chiffre d'Affaires (total, mensuel, en attente)
│   │   ├── Taux de conversion devis
│   │   ├── Tâches (terminées, en retard)
│   │   └── Performance ouvriers
│   │
│   ├── Graphiques
│   │   ├── Évolution CA (6 mois)
│   │   └── Répartition statuts
│   │
│   ├── Activité récente
│   │   ├── Derniers devis
│   │   ├── Dernières factures
│   │   └── Dernières tâches
│   │
│   └── Actions rapides
│       ├── [+ Devis]
│       ├── [+ Facture]
│       ├── [+ Tâche]
│       └── [+ Ouvrier]
│
├─► Planning Global (/admin-dashboard/planning/)
│   │
│   ├── Vue calendrier tous ouvriers
│   ├── Affectation par drag & drop
│   └── Filtres par ouvrier, client, statut
│
├─► Gestion Équipe
│   ├── Liste ouvriers (/admin-dashboard/workers/)
│   └── Création ouvrier (/admin-dashboard/workers/create/)
│
├─► Gestion Clients
│   ├── Liste clients (/admin-dashboard/clients/)
│   └── Création client (/admin-dashboard/clients/create/)
│
├─► Devis
│   ├── Liste (/admin-dashboard/quotes/)
│   │   ├── Filtres (statut, client, date)
│   │   ├── Export PDF/Excel
│   │   └── Actions en masse
│   │
│   └── Création (/admin-dashboard/quotes/create/)
│       ├── Sélection client (existant ou nouveau)
│       ├── Ajout lignes (produits/services)
│       ├── Calcul automatique TVA
│       ├── Aperçu PDF
│       └── [Enregistrer] ou [Enregistrer & Envoyer]
│
├─► Factures
│   ├── Liste (/admin-dashboard/invoices/)
│   └── Création (/admin-dashboard/invoices/create/)
│
├─► Campagnes Marketing (/admin-dashboard/campaigns/)
│   ├── Liste des campagnes
│   ├── Création campagne email
│   └── Statistiques d'envoi
│
└─► Messages (/messaging/)
    └── Conversations avec clients/ouvriers
```

---

### Parcours Admin Technique

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARCOURS ADMIN TECHNIQUE                     │
└─────────────────────────────────────────────────────────────────┘

⚙️ ADMINISTRATEUR TECHNIQUE
│
└─► Django Admin (/gestion/)
    │
    ├── Gestion des utilisateurs
    │   ├── Créer/Modifier/Supprimer
    │   ├── Attribution des rôles
    │   └── Réinitialisation mot de passe
    │
    ├── Configuration système
    │   ├── Services disponibles
    │   ├── Templates email
    │   └── Paramètres Brevo (emailing)
    │
    ├── Données métier
    │   ├── Devis (accès complet)
    │   ├── Factures (accès complet)
    │   ├── Tâches (accès complet)
    │   └── Messages
    │
    └── Monitoring
        ├── Logs d'activité
        ├── Sessions actives
        └── Notifications UI
```

---

## 🖼️ Maquettes fonctionnelles

### Navigation unifiée

La navigation doit être **consistante** entre tous les portails :

```
┌─────────────────────────────────────────────────────────────────┐
│                     STRUCTURE NAVIGATION                        │
└─────────────────────────────────────────────────────────────────┘

HEADER (toujours visible)
├── Logo + Nom (lien vers Dashboard du profil)
├── Navigation contextuelle (liens du portail)
├── 🔔 Notifications (badge compteur)
├── 👤 Menu utilisateur
│   ├── Mon Profil
│   ├── Aide (optionnel)
│   └── Déconnexion
└── 🍔 Menu burger (mobile)

NAVIGATION LATÉRALE (Admin Business uniquement)
├── Dashboard
├── Planning Global
├── ─────────────
├── Ouvriers
├── Clients
├── ─────────────
├── Devis
├── Factures
├── ─────────────
├── Campagnes
├── Messages
└── ─────────────
    ⚙️ Gestion (lien vers Django Admin)
```

### Composants récurrents

#### Card Document (Devis/Facture)

```
┌─────────────────────────────────────────────────────────────────┐
│  📄 DEV-2025-0042                                    ⏳ Envoyé   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client: Jean Dupont                                            │
│  Date: 15/12/2025                                               │
│  Échéance: 30/12/2025                                           │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Montant HT:     1 041,67 €                                     │
│  TVA (20%):        208,33 €                                     │
│  Total TTC:      1 250,00 €                                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [👁️ Voir]  [📥 Télécharger]  [✉️ Envoyer]  [✏️ Modifier]        │
└─────────────────────────────────────────────────────────────────┘
```

#### Card Tâche

```
┌─────────────────────────────────────────────────────────────────┐
│  🟡 En cours                                        ⏰ 14:00    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Nettoyage bureaux SCI Amazonie                                 │
│  ─────────────────────────────────────────────────────────────  │
│  📍 753 Chemin de la Désirée, Matoury                           │
│  👤 Client: SCI Amazonie                                        │
│  👷 Assigné: Marc Dubois, Sophie Martin                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Voir détails]                              Dernière màj: 14:32│
└─────────────────────────────────────────────────────────────────┘
```

---

## 💡 Recommandations UI

### 1. Unification de la palette

**Action immédiate** : Migrer de la palette verte vers la palette bleue définie dans `netexpress-design-system.css`.

```css
/* Remplacer */
.portal-nav { background-color: #16a34a; }

/* Par */
.portal-nav { 
  background: linear-gradient(135deg, var(--ne-blue-600), var(--ne-blue-800)); 
}
```

### 2. Amélioration du portail Worker

Le portail Worker actuel est trop basique. Ajouter :

- **Vue du jour** avec tâches priorisées
- **KPIs personnels** (motivation)
- **Actions rapides** sur les tâches
- **Upload photo** pour preuves d'intervention
- **Géolocalisation** pour les trajets

### 3. Enrichissement du portail Client

Ajouter :

- **Historique des interventions** passées
- **Évaluation** post-intervention (5 étoiles)
- **Rappel de paiement** visuel pour factures en attente
- **Chat en temps réel** avec l'administration

### 4. Micro-interactions

Ajouter des animations subtiles pour améliorer l'expérience :

```css
/* Animation d'apparition des cartes */
.ne-card {
  animation: ne-fade-in 0.3s ease-out;
}

/* Effet hover sur les lignes de tableau */
.ne-table tr:hover td {
  background: var(--ne-blue-50);
  transition: background 0.15s ease;
}

/* Bouton avec effet de pression */
.ne-btn:active {
  transform: translateY(1px);
}
```

### 5. États vides (Empty States)

Ajouter des illustrations et messages contextuels :

```html
<div class="ne-empty-state">
  <img src="/static/img/empty-quotes.svg" alt="" aria-hidden="true">
  <h3>Aucun devis pour le moment</h3>
  <p>Vos devis apparaîtront ici une fois créés.</p>
  <a href="{% url 'devis:request_quote' %}" class="ne-btn ne-btn-primary">
    Demander un devis
  </a>
</div>
```

### 6. Feedback utilisateur

Améliorer les notifications avec des toasts animés :

```html
<div class="ne-toast ne-toast-success" role="alert">
  <i class="fas fa-check-circle"></i>
  <span>Devis envoyé avec succès !</span>
  <button class="ne-toast-close" aria-label="Fermer">×</button>
</div>
```

---

## ♿ Accessibilité & Responsive

### Accessibilité (WCAG 2.1 AA)

1. **Contrastes** : Ratio minimum 4.5:1 pour le texte
2. **Focus visible** : Outline bleu de 3px sur tous les éléments interactifs
3. **Labels** : Tous les champs de formulaire ont des labels associés
4. **Navigation clavier** : Tous les éléments accessibles via Tab
5. **Lecteurs d'écran** : Attributs `aria-*` sur les éléments dynamiques

```css
/* Focus visible */
.ne-btn:focus-visible,
.ne-input:focus-visible,
.ne-nav-link:focus-visible {
  outline: 3px solid var(--ne-blue-300);
  outline-offset: 2px;
}

/* Mode contraste élevé */
@media (prefers-contrast: high) {
  .ne-card { border: 2px solid #000; }
  .ne-btn { border: 2px solid currentColor; }
}

/* Mouvement réduit */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Responsive Design

| Breakpoint | Taille | Adaptation |
|------------|--------|------------|
| Mobile | < 640px | Navigation burger, 1 colonne, boutons pleine largeur |
| Tablette | 640px - 1024px | 2 colonnes, sidebar repliable |
| Desktop | > 1024px | Sidebar fixe, 3-4 colonnes |

```css
/* Mobile first */
.ne-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--ne-space-4);
}

@media (min-width: 768px) {
  .ne-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (min-width: 1024px) {
  .ne-grid { grid-template-columns: repeat(4, 1fr); }
}
```

---

## 📅 Plan d'implémentation

### Phase 1 : Uniformisation (2 semaines)

1. ✅ Migrer tous les templates vers `base_v2.html`
2. ✅ Appliquer la palette bleue NetExpress
3. ✅ Unifier les composants (boutons, cartes, badges)
4. ✅ Corriger les incohérences de navigation

### Phase 2 : Amélioration Worker (1 semaine)

1. Refonte du dashboard Worker
2. Ajout des KPIs personnels
3. Actions rapides sur les tâches
4. Upload photo d'intervention

### Phase 3 : Enrichissement Client (1 semaine)

1. Historique des interventions
2. Système d'évaluation
3. Rappels visuels de paiement
4. États vides illustrés

### Phase 4 : Polish (1 semaine)

1. Micro-interactions et animations
2. Toasts de notification améliorés
3. Audit accessibilité
4. Tests responsive sur appareils réels

---

## 📎 Annexes

### Fichiers de référence

| Fichier | Description |
|---------|-------------|
| `static/css/netexpress-design-system.css` | Design system complet (à utiliser) |
| `static/css/style_v2.css` | Styles portails (à migrer vers bleu) |
| `static/css/backoffice.css` | Styles backoffice Worker |
| `templates/base_v2.html` | Template de base moderne |

### Icônes recommandées

Utiliser **Font Awesome 6** pour la cohérence :

- 📊 `fa-tachometer-alt` — Dashboard
- 📄 `fa-file-alt` — Devis
- 📃 `fa-receipt` — Factures
- 📋 `fa-tasks` — Tâches
- 👥 `fa-users` — Équipe
- 📆 `fa-calendar-alt` — Planning
- 💬 `fa-envelope` — Messages
- ⚙️ `fa-cogs` — Paramètres

---

*Document généré pour le projet NetExpress — Décembre 2025*

