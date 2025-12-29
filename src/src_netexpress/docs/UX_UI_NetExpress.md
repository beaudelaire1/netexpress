# NetExpress — Guide UX/UI Complet

**Version 1.0 — Décembre 2025**  
**Responsable UX/UI**

---

## Table des matières

1. [Vision Produit](#1-vision-produit)
2. [Profils Utilisateurs](#2-profils-utilisateurs)
3. [Parcours UX Détaillés](#3-parcours-ux-détaillés)
4. [Design System](#4-design-system)
5. [Composants UI](#5-composants-ui)
6. [Maquettes Fonctionnelles](#6-maquettes-fonctionnelles)
7. [Responsive & Mobile](#7-responsive--mobile)
8. [Accessibilité](#8-accessibilité)
9. [Recommandations](#9-recommandations)

---

## 1. Vision Produit

### 1.1 Objectif

NetExpress est un **ERP métier** conçu pour les entreprises de services (nettoyage, entretien, espaces verts). L'interface doit être :

- **Accessible** : utilisateurs non techniques
- **Efficace** : tâches accomplies en minimum de clics
- **Premium** : image professionnelle cohérente
- **Sobre** : pas de surcharge visuelle

### 1.2 Principes Directeurs

| Principe | Description |
|----------|-------------|
| **Clarté** | Chaque écran a un objectif unique et évident |
| **Cohérence** | Mêmes patterns dans tous les portails |
| **Feedback** | L'utilisateur sait toujours ce qui se passe |
| **Efficacité** | Actions principales en ≤3 clics |
| **Sobriété** | Espace blanc généreux, hiérarchie claire |

---

## 2. Profils Utilisateurs

### 2.1 Client

| Attribut | Description |
|----------|-------------|
| **Profil type** | Particulier ou entreprise, utilisateur occasionnel |
| **Objectifs** | Demander devis, suivre factures, communiquer |
| **Compétences** | Faibles à moyennes en informatique |
| **Fréquence** | 1-5 fois/mois |
| **Priorité UX** | Simplicité maximale, assistance guidée |

### 2.2 Ouvrier (Worker)

| Attribut | Description |
|----------|-------------|
| **Profil type** | Technicien terrain, utilise principalement mobile |
| **Objectifs** | Voir planning, marquer tâches terminées |
| **Compétences** | Variables, souvent faibles |
| **Fréquence** | Quotidienne |
| **Priorité UX** | Rapidité, gros boutons tactiles, mode hors-ligne |

### 2.3 Administrateur Business

| Attribut | Description |
|----------|-------------|
| **Profil type** | Gestionnaire, responsable commercial |
| **Objectifs** | Créer devis/factures, gérer planning, suivre KPIs |
| **Compétences** | Moyennes |
| **Fréquence** | Plusieurs fois/jour |
| **Priorité UX** | Efficacité, vue d'ensemble, actions rapides |

### 2.4 Administrateur Technique

| Attribut | Description |
|----------|-------------|
| **Profil type** | IT, développeur, technicien |
| **Objectifs** | Configuration système, gestion utilisateurs |
| **Compétences** | Élevées |
| **Fréquence** | Hebdomadaire à mensuelle |
| **Priorité UX** | Puissance, accès à toutes les données |

---

## 3. Parcours UX Détaillés

### 3.1 Parcours Client

#### 3.1.1 Demande de Devis (Nouveau Client)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PAGE D'ACCUEIL                                              │
│     └── CTA "Devis Express" (visible immédiatement)             │
│                                                                 │
│  2. FORMULAIRE DEVIS                                            │
│     ├── Sélection service (icônes cliquables)                   │
│     ├── Surface estimée (slider intuitif)                       │
│     ├── Fréquence souhaitée                                     │
│     └── Coordonnées                                             │
│                                                                 │
│  3. CONFIRMATION                                                │
│     ├── Résumé de la demande                                    │
│     ├── Email de confirmation envoyé                            │
│     └── Proposition de créer un compte                          │
│                                                                 │
│  4. SUIVI (après inscription)                                   │
│     └── Dashboard client → Devis reçu → Validation              │
└─────────────────────────────────────────────────────────────────┘
```

**Points clés UX :**
- Formulaire en une seule page, pas d'étapes multiples
- Validation en temps réel
- Estimation indicative affichée dynamiquement
- Possibilité de joindre des photos

#### 3.1.2 Espace Client Connecté

```
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD CLIENT                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Mes Devis   │  │ Mes Factures│  │ Messages    │              │
│  │ (3 en cours)│  │ (1 impayée) │  │ (2 non lus) │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  ACTIONS RAPIDES                                                │
│  [+ Nouveau Devis] [📬 Contacter] [👤 Mon Profil]               │
│                                                                 │
│  DOCUMENTS RÉCENTS (vue liste épurée)                           │
│  ├── Devis #D-2025-0042 — En attente — 1 250,00 €               │
│  ├── Facture #F-2025-0018 — Payée — 890,00 €                    │
│  └── Devis #D-2025-0039 — Accepté — 2 100,00 €                  │
└─────────────────────────────────────────────────────────────────┘
```

**Flux de validation d'un devis :**
1. Client reçoit email avec lien sécurisé
2. Vue détaillée du devis (PDF consultable)
3. Bouton "Accepter" + saisie code de validation (SMS/email)
4. Confirmation + génération facture automatique

---

### 3.2 Parcours Ouvrier

#### 3.2.1 Consultation Planning Quotidien

```
┌─────────────────────────────────────────────────────────────────┐
│  ÉCRAN PRINCIPAL OUVRIER (optimisé mobile)                      │
│                                                                 │
│  ╭────────────────────────────────────────╮                     │
│  │  📅 AUJOURD'HUI — Lundi 28 Déc.        │                     │
│  │                                        │                     │
│  │  🕐 08:00-10:00                        │                     │
│  │  Nettoyage bureaux — SCI Matoury       │                     │
│  │  📍 12 rue des Palmiers                │                     │
│  │  [🗺️ Itinéraire] [✅ Commencer]         │                     │
│  ╰────────────────────────────────────────╯                     │
│                                                                 │
│  ╭────────────────────────────────────────╮                     │
│  │  🕐 10:30-12:00                        │                     │
│  │  Entretien jardin — M. Dupont          │                     │
│  │  📍 45 allée des Orchidées             │                     │
│  │  [🗺️ Itinéraire]                        │                     │
│  ╰────────────────────────────────────────╯                     │
│                                                                 │
│  [📋 Semaine] [📊 Mes Stats]                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Workflow tâche :**
1. **À faire** → Clic "Commencer" → **En cours**
2. **En cours** → Clic "Terminer" → **Terminée**
   - Option : Ajouter photo avant/après
   - Option : Signaler un problème
3. Notification automatique à l'admin

---

### 3.3 Parcours Administrateur Business

#### 3.3.1 Vue Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────┬─────────┬─────────┬─────────┐                      │
│  │ CA MOIS │ EN      │ IMPAYÉS │ TAUX    │  ← KPIs en haut      │
│  │ 12 450€ │ ATTENTE │ 890€    │ CONV.   │                      │
│  │         │ 3 200€  │         │ 72%     │                      │
│  └─────────┴─────────┴─────────┴─────────┘                      │
│                                                                 │
│  ┌──────────────────────┐ ┌──────────────────────┐              │
│  │ DEVIS RÉCENTS        │ │ TÂCHES DU JOUR       │              │
│  │ ▸ #D-042 En attente  │ │ ▸ 3 en cours         │              │
│  │ ▸ #D-041 Accepté     │ │ ▸ 2 à venir          │              │
│  │ [Voir tous]          │ │ [Voir planning]      │              │
│  └──────────────────────┘ └──────────────────────┘              │
│                                                                 │
│  ACTIONS RAPIDES                                                │
│  [+ Devis] [+ Facture] [+ Tâche] [+ Ouvrier]                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 Création de Devis

```
┌─────────────────────────────────────────────────────────────────┐
│  NOUVEAU DEVIS                                                  │
│                                                                 │
│  CLIENT ────────────────────────────────────────────────        │
│  [🔍 Rechercher client existant...        ]                     │
│  [+ Créer nouveau client]                                       │
│                                                                 │
│  LIGNES DE DEVIS ───────────────────────────────────────        │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Service           │ Qté │ Prix U. │ Total           │       │
│  ├──────────────────────────────────────────────────────┤       │
│  │ Nettoyage bureaux │  1  │ 150,00  │ 150,00 €        │       │
│  │ [✏️] [🗑️]                                            │       │
│  ├──────────────────────────────────────────────────────┤       │
│  │ [+ Ajouter une ligne]                                │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
│                           Sous-total : 150,00 €                 │
│                           TVA (20%)  :  30,00 €                 │
│                           ─────────────────────                 │
│                           TOTAL TTC  : 180,00 €                 │
│                                                                 │
│  [💾 Brouillon] [📧 Envoyer au client] [📄 Voir PDF]            │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Parcours Administrateur Technique

Accès à l'interface Django Admin (`/gestion/`) avec :
- Gestion complète des utilisateurs et rôles
- Configuration système
- Logs et audit
- Import/Export de données

---

## 4. Design System

### 4.1 Palette de Couleurs — Charte Verte NetExpress

#### Couleurs Principales

| Token | Valeur | Usage |
|-------|--------|-------|
| `--ne-green-500` | `#0e6b4c` | Couleur principale, CTAs |
| `--ne-green-600` | `#0c5a40` | Hover, liens actifs |
| `--ne-green-700` | `#0a4934` | Headers, accents forts |
| `--ne-green-800` | `#083828` | Textes importants |
| `--ne-green-900` | `#06271c` | Sidebar, footer |

#### Couleurs Sémantiques

| Token | Valeur | Usage |
|-------|--------|-------|
| `--ne-success-500` | `#22c55e` | Succès, validé, payé |
| `--ne-warning-500` | `#f59e0b` | Attention, en attente |
| `--ne-error-500` | `#ef4444` | Erreur, rejeté, impayé |
| `--ne-info-500` | `#0ea5e9` | Information |

#### Neutres

| Token | Valeur | Usage |
|-------|--------|-------|
| `--ne-gray-50` | `#f9fafb` | Fond de page |
| `--ne-gray-100` | `#f3f4f6` | Fond de tableaux |
| `--ne-gray-500` | `#6b7280` | Texte secondaire |
| `--ne-gray-800` | `#1f2937` | Texte principal |

### 4.2 Typographie

#### Familles

```css
--ne-font-display: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
--ne-font-body: 'Inter', system-ui, sans-serif;
--ne-font-mono: 'JetBrains Mono', monospace;
```

#### Échelle

| Niveau | Taille | Usage |
|--------|--------|-------|
| `text-xs` | 12px | Badges, labels |
| `text-sm` | 14px | Texte secondaire, nav |
| `text-base` | 16px | Texte courant |
| `text-lg` | 18px | Sous-titres |
| `text-xl` | 20px | Titres de section |
| `text-2xl` | 24px | Titres de page |
| `text-3xl` | 30px | KPIs |
| `text-4xl` | 36px | Hero, dashboard |

### 4.3 Espacements

```css
--ne-space-1: 4px;    /* Marges internes serrées */
--ne-space-2: 8px;    /* Gaps entre éléments proches */
--ne-space-3: 12px;   /* Padding boutons */
--ne-space-4: 16px;   /* Padding cartes */
--ne-space-6: 24px;   /* Marges sections */
--ne-space-8: 32px;   /* Espacement entre sections */
--ne-space-12: 48px;  /* Grandes marges */
```

### 4.4 Rayons et Ombres

```css
/* Rayons */
--ne-radius-sm: 6px;      /* Badges, inputs */
--ne-radius-md: 10px;     /* Boutons */
--ne-radius-lg: 14px;     /* Cartes */
--ne-radius-xl: 18px;     /* Modals */
--ne-radius-full: 9999px; /* Pills */

/* Ombres */
--ne-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--ne-shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
--ne-shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.08);
--ne-shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.08);
--ne-shadow-green: 0 10px 30px rgba(22, 163, 74, 0.25);
```

---

## 5. Composants UI

### 5.1 Boutons

#### Primaire (Actions principales)
```html
<button class="ne-btn ne-btn-primary">
  Envoyer le devis
</button>
```
- Fond : gradient vert
- Texte : blanc, semi-bold
- Ombre colorée
- Hover : légère élévation

#### Secondaire (Actions alternatives)
```html
<button class="ne-btn ne-btn-secondary">
  Annuler
</button>
```
- Fond : transparent
- Bordure : verte
- Texte : vert

#### Ghost (Actions tertiaires)
```html
<button class="ne-btn ne-btn-ghost">
  <i class="fas fa-eye"></i> Voir détails
</button>
```
- Fond : transparent
- Texte : gris
- Hover : fond gris léger

### 5.2 Cartes

#### Carte Standard
```html
<div class="ne-card">
  <div class="ne-card-header">
    <h3 class="ne-card-title">Titre</h3>
    <a href="#">Voir tout</a>
  </div>
  <div class="ne-card-body">
    Contenu...
  </div>
</div>
```

#### Carte KPI
```html
<div class="ne-card-kpi is-green">
  <span class="ne-kpi-label">Chiffre d'Affaires</span>
  <span class="ne-kpi-value">12 450 €</span>
  <div class="ne-kpi-icon">
    <i class="fas fa-euro-sign"></i>
  </div>
</div>
```

### 5.3 Badges de Statut

| Statut | Classe | Couleur |
|--------|--------|---------|
| Brouillon | `ne-badge-draft` | Gris |
| Envoyé | `ne-badge-sent` | Jaune |
| Accepté | `ne-badge-accepted` | Vert |
| Rejeté | `ne-badge-rejected` | Rouge |
| Payé | `ne-badge-paid` | Vert |
| Impayé | `ne-badge-overdue` | Rouge |
| En cours | `ne-badge-in-progress` | Vert |

### 5.4 Formulaires

```html
<div class="ne-form-group">
  <label class="ne-label">Email *</label>
  <input type="email" class="ne-input" placeholder="client@exemple.fr">
</div>
```

**États :**
- Normal : bordure grise
- Focus : bordure verte + ombre verte légère
- Erreur : bordure rouge + message d'erreur
- Désactivé : fond gris, curseur interdit

### 5.5 Tables

```html
<div class="ne-table-wrapper">
  <table class="ne-table">
    <thead>
      <tr>
        <th>Numéro</th>
        <th>Client</th>
        <th>Montant</th>
        <th>Statut</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>#D-2025-0042</td>
        <td>SCI Matoury</td>
        <td>1 250,00 €</td>
        <td><span class="ne-badge ne-badge-sent">Envoyé</span></td>
        <td>
          <button class="ne-btn ne-btn-ghost ne-btn-sm">
            <i class="fas fa-eye"></i>
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 6. Maquettes Fonctionnelles

### 6.1 Page d'Accueil Public

```
┌────────────────────────────────────────────────────────────────────┐
│ HEADER                                                             │
│ [Logo] Nettoyage Express        [Services] [Contact] [DEVIS ✨]    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  █████████████████████████████████████████████████████████████████ │
│  █                                                               █ │
│  █   Propreté Premium                                           █ │
│  █   en Guyane                                                  █ │
│  █                                                               █ │
│  █   Services d'entretien professionnels                        █ │
│  █   pour particuliers et entreprises                           █ │
│  █                                                               █ │
│  █   [Demander un devis gratuit]   [Nos services →]             █ │
│  █                                                               █ │
│  █████████████████████████████████████████████████████████████████ │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 🧹 Nettoyage │  │ 🌿 Espaces   │  │ 🔨 Bricolage │              │
│  │   bureaux    │  │    verts     │  │   peinture   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│ FOOTER — Contact — Mentions légales — © 2025                       │
└────────────────────────────────────────────────────────────────────┘
```

### 6.2 Dashboard Client

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER VERT                                                         │
│ [Logo]               [Dashboard] [Devis] [Factures] [Messages] [👤] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Bonjour, Jean Dupont                                               │
│  Dernière connexion : 27/12/2025 à 14:32                            │
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ Devis   │  │ En      │  │ Factures│  │ Impayées│                 │
│  │   5     │  │ attente │  │   12    │  │    1    │                 │
│  │         │  │   2     │  │         │  │         │                 │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘                 │
│                                                                     │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐ │
│  │ 📄 DEVIS RÉCENTS             │  │ 🧾 FACTURES RÉCENTES         │ │
│  ├──────────────────────────────┤  ├──────────────────────────────┤ │
│  │ #D-042  En attente  1250€    │  │ #F-018  Payée      890€      │ │
│  │ #D-041  Accepté     2100€    │  │ #F-017  À payer   1250€ ⚠️   │ │
│  │ [Voir tous →]                │  │ [Voir toutes →]              │ │
│  └──────────────────────────────┘  └──────────────────────────────┘ │
│                                                                     │
│  ACTIONS RAPIDES                                                    │
│  [➕ Nouveau Devis] [✉️ Contacter] [👤 Mon Profil]                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Dashboard Admin

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER VERT FONCÉ                                                   │
│ [Logo]        [Dashboard] [Planning] [Devis] [Factures] [Équipe]    │
├───────┬─────────────────────────────────────────────────────────────┤
│       │                                                             │
│  S    │  Dashboard Administrateur                                   │
│  I    │  Vue d'ensemble des performances                            │
│  D    │                                                             │
│  E    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                │
│  B    │  │ CA     │ │ MOIS   │ │IMPAYÉS │ │ TAUX   │                │
│  A    │  │145 800€│ │ 12 450€│ │ 3 200€ │ │  72%   │                │
│  R    │  └────────┘ └────────┘ └────────┘ └────────┘                │
│       │                                                             │
│  📊   │  ┌─────────────────────┐ ┌────────────────────┐             │
│  Dash │  │ 📈 ÉVOLUTION CA     │ │ 🥧 STATUTS DEVIS   │             │
│       │  │     (Graphique)     │ │    (Camembert)     │             │
│  📅   │  └─────────────────────┘ └────────────────────┘             │
│ Plan. │                                                             │
│       │  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  👥   │  │ Devis    │ │ Factures │ │ Tâches   │                     │
│ Équipe│  │ récents  │ │ récentes │ │ récentes │                     │
│       │  └──────────┘ └──────────┘ └──────────┘                     │
│  📄   │                                                             │
│ Devis │  ACTIONS RAPIDES                                            │
│       │  [+ Devis] [+ Facture] [+ Tâche] [+ Ouvrier] [⚙️ Gestion]   │
│  🧾   │                                                             │
│ Fact. │                                                             │
│       │                                                             │
└───────┴─────────────────────────────────────────────────────────────┘
```

### 6.4 Dashboard Ouvrier (Mobile First)

```
┌─────────────────────────────────┐
│ HEADER VERT                     │
│ [☰]  Mes Tâches  [🔔]           │
├─────────────────────────────────┤
│                                 │
│  📅 Lundi 28 Décembre           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                 │
│  ╭─────────────────────────╮    │
│  │ 🕗 08:00 - 10:00        │    │
│  │                         │    │
│  │ Nettoyage bureaux       │    │
│  │ SCI Matoury             │    │
│  │                         │    │
│  │ 📍 12 rue des Palmiers  │    │
│  │                         │    │
│  │ ┌─────────┐ ┌─────────┐ │    │
│  │ │ 🗺️ GPS  │ │ ✅ START│ │    │
│  │ └─────────┘ └─────────┘ │    │
│  ╰─────────────────────────╯    │
│                                 │
│  ╭─────────────────────────╮    │
│  │ 🕥 10:30 - 12:00        │    │
│  │                         │    │
│  │ Entretien jardin        │    │
│  │ M. Dupont               │    │
│  │                         │    │
│  │ 📍 45 allée Orchidées   │    │
│  │                         │    │
│  │ [🗺️ GPS]                │    │
│  ╰─────────────────────────╯    │
│                                 │
├─────────────────────────────────┤
│  [📋 Liste] [📅 Semaine] [📊]   │
└─────────────────────────────────┘
```

---

## 7. Responsive & Mobile

### 7.1 Breakpoints

| Nom | Largeur | Usage |
|-----|---------|-------|
| `sm` | 640px | Mobiles larges |
| `md` | 768px | Tablettes portrait |
| `lg` | 1024px | Tablettes paysage |
| `xl` | 1280px | Desktop |
| `2xl` | 1536px | Grands écrans |

### 7.2 Stratégie Mobile

#### Client
- Dashboard simplifié
- Liste de documents scrollable
- Actions principales en bas d'écran
- Formulaire de devis optimisé tactile

#### Ouvrier
- **Mobile First obligatoire**
- Cartes de tâches grandes et espacées
- Boutons d'action minimum 48x48px
- Accès GPS en un clic
- Mode hors-ligne pour consultation

#### Admin
- Sidebar rétractable en drawer
- Tableaux scrollables horizontalement
- KPIs empilés sur mobile
- Graphiques adaptatifs

---

## 8. Accessibilité

### 8.1 Standards

- **WCAG 2.1 niveau AA**
- Contraste minimum 4.5:1 (texte) / 3:1 (éléments)
- Navigation clavier complète
- Labels ARIA sur éléments interactifs
- Skip links pour navigation rapide

### 8.2 Implémentation

```css
/* Focus visible */
*:focus-visible {
  outline: 3px solid rgba(59, 130, 246, 0.5);
  outline-offset: 2px;
}

/* Mouvement réduit */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* Contraste élevé */
@media (prefers-contrast: high) {
  .ne-card { border: 2px solid #000; }
  .ne-btn { border: 2px solid currentColor; }
}
```

---

## 9. Recommandations

### 9.1 Actions Prioritaires

| Priorité | Action | Impact |
|----------|--------|--------|
| 🔴 P1 | Valider la charte verte | Cohérence visuelle |
| 🔴 P1 | Optimiser dashboard ouvrier mobile | UX terrain |
| 🟡 P2 | Ajouter mode hors-ligne ouvrier | Fiabilité |
| 🟡 P2 | Implémenter validation devis en 1 clic | Conversion |
| 🟢 P3 | Ajouter dark mode (optionnel) | Confort |
| 🟢 P3 | Animations de chargement squelette | Perception perf. |

### 9.2 À Éviter

❌ Surcharge d'informations sur un même écran  
❌ Menus à plus de 2 niveaux de profondeur  
❌ Tableaux avec trop de colonnes sur mobile  
❌ Pop-ups modaux intrusifs  
❌ Couleurs non sémantiques (ex: rouge pour succès)  
❌ Textes trop petits (< 14px)  
❌ Contrastes insuffisants  

### 9.3 Bonnes Pratiques

✅ 1 objectif principal par écran  
✅ Feedback immédiat sur chaque action  
✅ Confirmation avant actions destructives  
✅ États de chargement visuels  
✅ Messages d'erreur explicites et actionnables  
✅ Raccourcis clavier pour utilisateurs experts  
✅ Historique/Undo quand possible  

---

## Annexe : Fichiers de Référence

| Fichier | Description |
|---------|-------------|
| `static/css/style_v2.css` | Styles principaux (charte verte) |
| `templates/base_v2.html` | Template de base portails |
| `tailwind.config.js` | Configuration Tailwind |

---

**Document maintenu par l'équipe UX/UI NetExpress**  
*Dernière mise à jour : 28 Décembre 2025*
