# Résumé Exécutif - Interface de Gestion Métier

**Document complet :** `docs/INTERFACE_GESTION_METIER.md`

---

## 🎯 Vision Globale

L'interface de gestion métier (`/admin-dashboard/`) est le **cœur opérationnel** de NetExpress. Elle permet aux équipes de gestion (administrateurs métier, gestionnaires, responsables d'exploitation) de piloter l'activité quotidienne **sans dépendre de l'interface technique Django Admin**.

---

## 📋 Modules Principaux

### 1. Dashboard
- **KPIs** : CA mois, CA attente, Montant impayé, Taux conversion
- **Graphiques** : Évolution CA, Répartition statuts
- **Listes récentes** : Devis, Factures, Tâches du jour
- **Actions rapides** : Création directe

### 2. Gestion Clients
- Liste avec recherche/filtres
- Détail avec historique complet
- Création manuelle ou depuis inscription publique
- Vue complète : devis, factures, timeline

### 3. Gestion Workers ⚠️
- Liste avec statistiques performance
- **Création worker** : Génération compte automatique + envoi identifiants
- **RÈGLE CRITIQUE** : Workers ne peuvent JAMAIS créer leur compte eux-mêmes
- Détail : Tâches assignées, planning, statistiques

### 4. Gestion Devis
- Liste avec filtres (statut, client, période)
- Détail complet avec lignes, totaux, historique
- Création en 3 étapes : Client → Lignes → Validation
- Envoi email avec PDF
- Conversion en facture (si accepté)

### 5. Gestion Factures
- Liste avec filtres (statut, impayées, en retard)
- Détail complet
- Création manuelle ou conversion devis
- Suivi paiements (payée, partielle, impayée)

### 6. Planning et Tâches
- Vue calendrier (mois, semaine, jour)
- Liste complète avec filtres
- Création et modification tâches
- Affectation/réassignation workers

### 7. Tableaux de Bord Avancés
- KPIs globaux
- Reporting personnalisé
- Exports (CSV, PDF)

---

## 🔐 Règles Fondamentales

### Règle 1 : Workers ne s'inscrivent jamais
- ⚠️ Les workers sont créés **UNIQUEMENT** par un utilisateur de gestion
- Création depuis `/admin-dashboard/workers/create/`
- Génération automatique compte + mot de passe temporaire
- Envoi email identifiants automatique

### Règle 2 : Inscription publique = Client
- Toute inscription depuis l'interface publique crée automatiquement un **CLIENT**
- Rôle `client` attribué automatiquement
- Pas de possibilité de s'inscrire en tant que worker

### Règle 3 : Permissions côté serveur
- Toutes les vérifications de permissions sont effectuées **côté serveur**
- Aucune élévation de privilège possible côté client
- Rôles contrôlés uniquement par le backend

---

## 🔄 Flux Métiers Principaux

### Flux 1 : Devis → Facture
```
Création Devis → Envoi → Validation Client → Conversion Facture → Paiement
```

### Flux 2 : Création Worker
```
Admin Crée Worker → Génération Compte → Envoi Identifiants → Activation Worker
```

### Flux 3 : Planning
```
Création Tâche → Assignation Worker → Accomplissement → Suivi Performance
```

---

## 🛠️ Architecture Technique

### Structure Recommandée

```
core/
├── views.py                    # Vues principales admin-dashboard
├── services/
│   ├── client_service.py       # Logique métier clients
│   ├── worker_service.py       # Logique métier workers
│   └── dashboard_service.py    # Calculs KPIs
```

### Principes
- **Vues Django classiques** (FBV ou CBV)
- **Logique métier dans services** (jamais dans templates)
- **Permissions vérifiées** dans chaque vue
- **Validation côté serveur** (Django Forms)

---

## ✅ Checklist Implémentation

### Priorité 1 (Semaines 1-2)
- [ ] Dashboard avec KPIs
- [ ] Gestion clients (CRUD)
- [ ] Création client

### Priorité 2 (Semaines 2-3)
- [ ] Gestion workers (CRUD)
- [ ] Création worker avec service backend
- [ ] Envoi identifiants

### Priorité 3 (Semaines 3-4)
- [ ] Gestion devis (amélioration si nécessaire)
- [ ] Envoi email devis

### Priorité 4 (Semaines 4-5)
- [ ] Gestion factures (CRUD)
- [ ] Conversion devis → facture

### Priorité 5 (Semaines 5-6)
- [ ] Gestion tâches (CRUD)
- [ ] Vue calendrier
- [ ] Affectation workers

---

## 📚 Documentation Complète

Pour les détails complets de chaque module, flux métier, règles d'accès et recommandations techniques, consulter :

**`docs/INTERFACE_GESTION_METIER.md`**

Ce document contient :
- ✅ Description détaillée de chaque page
- ✅ Flux métiers complets
- ✅ Règles d'accès et permissions
- ✅ Structure technique recommandée
- ✅ Bonnes pratiques d'implémentation

---

**Créé le :** 28 Décembre 2025  
**Version :** 1.0

